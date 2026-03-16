#!/usr/bin/env python3
"""
Face Finder - Reverse image search tool for finding a person across the internet.

Given a photo of someone's face, this tool:
1. Detects and extracts the face from the image
2. Searches multiple reverse image search engines (Google, Yandex, Bing, TinEye)
3. Optionally uses SerpAPI for automated result scraping
4. Downloads and compares found images using face embeddings to verify matches
5. Outputs a report of all confirmed matches with source URLs

Usage:
    python face_finder.py photo.jpg
    python face_finder.py photo.jpg --serpapi-key YOUR_KEY
    python face_finder.py photo.jpg --output results/
"""

import argparse
import base64
import hashlib
import json
import os
import shutil
import struct
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from PIL import Image

# DeepFace is imported lazily to speed up startup for URL-generation-only mode
_deepface = None


def _get_deepface():
    global _deepface
    if _deepface is None:
        os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
        from deepface import DeepFace
        _deepface = DeepFace
    return _deepface


# ─── Data classes ────────────────────────────────────────────────────────────

@dataclass
class FaceRegion:
    x: int
    y: int
    w: int
    h: int
    confidence: float = 0.0
    image: Optional[np.ndarray] = None


@dataclass
class SearchResult:
    engine: str
    url: str
    page_url: str = ""
    title: str = ""
    thumbnail_url: str = ""


@dataclass
class VerifiedMatch:
    source_engine: str
    image_url: str
    page_url: str
    title: str
    distance: float
    local_path: str = ""


@dataclass
class SearchReport:
    input_image: str
    faces_detected: int
    search_urls: dict = field(default_factory=dict)
    raw_results: list = field(default_factory=list)
    verified_matches: list = field(default_factory=list)


# ─── Face Detection & Embedding ─────────────────────────────────────────────

def detect_faces(image_path: str) -> list[FaceRegion]:
    """Detect faces in an image and return their regions."""
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Could not read image: {image_path}")

    DeepFace = _get_deepface()
    try:
        faces = DeepFace.extract_faces(
            img_path=image_path,
            detector_backend="opencv",
            enforce_detection=False,
        )
    except Exception as e:
        print(f"[!] DeepFace detection failed, falling back to OpenCV Haar: {e}")
        return _detect_faces_opencv(img)

    regions = []
    for face in faces:
        area = face.get("facial_area", {})
        x, y, w, h = area.get("x", 0), area.get("y", 0), area.get("w", 0), area.get("h", 0)
        conf = face.get("confidence", 0)
        if w > 20 and h > 20:  # filter tiny false positives
            face_img = img[y:y + h, x:x + w]
            regions.append(FaceRegion(x=x, y=y, w=w, h=h, confidence=conf, image=face_img))

    return regions


def _detect_faces_opencv(img: np.ndarray) -> list[FaceRegion]:
    """Fallback face detection using OpenCV Haar cascades."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    cascade = cv2.CascadeClassifier(cascade_path)
    rects = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
    regions = []
    for (x, y, w, h) in rects:
        face_img = img[y:y + h, x:x + w]
        regions.append(FaceRegion(x=x, y=y, w=w, h=h, confidence=1.0, image=face_img))
    return regions


def get_face_embedding(image_path: str) -> Optional[list[float]]:
    """Get a 128-d face embedding vector using DeepFace."""
    DeepFace = _get_deepface()
    try:
        embeddings = DeepFace.represent(
            img_path=image_path,
            model_name="Facenet512",
            detector_backend="opencv",
            enforce_detection=False,
        )
        if embeddings:
            return embeddings[0]["embedding"]
    except Exception as e:
        print(f"[!] Could not compute embedding: {e}")
    return None


def compare_faces(img1_path: str, img2_path: str, threshold: float = 0.60) -> tuple[bool, float]:
    """Compare two face images. Returns (is_match, distance)."""
    DeepFace = _get_deepface()
    try:
        result = DeepFace.verify(
            img1_path=img1_path,
            img2_path=img2_path,
            model_name="Facenet512",
            detector_backend="opencv",
            enforce_detection=False,
        )
        distance = result.get("distance", 1.0)
        return distance <= threshold, distance
    except Exception as e:
        print(f"[!] Face comparison failed: {e}")
        return False, 1.0


# ─── Prepare image for upload ───────────────────────────────────────────────

def prepare_face_image(image_path: str, output_dir: str) -> str:
    """Extract the largest face from an image and save it for searching."""
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Cannot read image: {image_path}")

    faces = detect_faces(image_path)
    if not faces:
        print("[*] No faces detected - using full image for search")
        out_path = os.path.join(output_dir, "search_face.jpg")
        # Resize to reasonable dimensions for upload
        h, w = img.shape[:2]
        if max(h, w) > 1000:
            scale = 1000 / max(h, w)
            img = cv2.resize(img, (int(w * scale), int(h * scale)))
        cv2.imwrite(out_path, img, [cv2.IMWRITE_JPEG_QUALITY, 95])
        return out_path

    # Use the largest face
    largest = max(faces, key=lambda f: f.w * f.h)
    print(f"[*] Found {len(faces)} face(s), using largest ({largest.w}x{largest.h})")

    # Add padding around the face for better search results
    h, w = img.shape[:2]
    pad = int(max(largest.w, largest.h) * 0.4)
    x1 = max(0, largest.x - pad)
    y1 = max(0, largest.y - pad)
    x2 = min(w, largest.x + largest.w + pad)
    y2 = min(h, largest.y + largest.h + pad)
    face_crop = img[y1:y2, x1:x2]

    out_path = os.path.join(output_dir, "search_face.jpg")
    cv2.imwrite(out_path, face_crop, [cv2.IMWRITE_JPEG_QUALITY, 95])
    return out_path


# ─── Search Engine URL Generators ───────────────────────────────────────────

def _image_to_base64(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _image_to_data_uri(image_path: str) -> str:
    b64 = _image_to_base64(image_path)
    return f"data:image/jpeg;base64,{b64}"


def get_search_urls(image_path: str) -> dict[str, str]:
    """
    Generate reverse image search URLs for manual use.
    These URLs can be opened in a browser to perform the search.
    """
    urls = {}

    # Google Images (Google Lens) - upload via the search page
    urls["google_lens"] = "https://lens.google.com/"
    urls["google_images"] = "https://images.google.com/"

    # Yandex - best for face recognition
    urls["yandex"] = "https://yandex.com/images/search?rpt=imageview&url="

    # Bing Visual Search
    urls["bing"] = "https://www.bing.com/images/search?view=detailv2&iss=sbi"

    # TinEye
    urls["tineye"] = "https://tineye.com/search"

    # FaceCheck.ID - specifically for face search
    urls["facecheck"] = "https://facecheck.id/"

    # PimEyes - face search engine
    urls["pimeyes"] = "https://pimeyes.com/en"

    # Social Catfish - people search
    urls["socialcatfish"] = "https://socialcatfish.com/reverse-image-search/"

    return urls


# ─── SerpAPI Integration (Automated Search) ─────────────────────────────────

def _upload_image_to_tmphost(image_path: str) -> Optional[str]:
    """
    Upload image to a free temporary image hosting service to get a public URL.
    This URL is needed for search engine APIs that require a URL rather than upload.
    """
    try:
        import requests
        # Use imgbb free API (no key needed for basic uploads)
        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")

        # Try freeimage.host (no API key required)
        resp = requests.post(
            "https://freeimage.host/api/1/upload",
            data={
                "key": "6d207e02198a847aa98d0a2a901485a5",  # public API key
                "action": "upload",
                "source": b64,
                "format": "json",
            },
            timeout=30,
        )
        if resp.status_code == 200:
            data = resp.json()
            url = data.get("image", {}).get("url")
            if url:
                print(f"[*] Image uploaded to: {url}")
                return url
    except Exception as e:
        print(f"[!] Image upload failed: {e}")

    return None


def search_serpapi(image_path: str, api_key: str) -> list[SearchResult]:
    """
    Use SerpAPI to search Google Lens and Yandex with the image.
    SerpAPI handles image upload and returns structured results.
    """
    import requests

    results = []
    image_url = _upload_image_to_tmphost(image_path)

    # --- Google Lens via SerpAPI ---
    print("[*] Searching Google Lens via SerpAPI...")
    try:
        params = {
            "engine": "google_lens",
            "api_key": api_key,
        }
        if image_url:
            params["url"] = image_url
        else:
            # Upload directly to SerpAPI
            with open(image_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
            params["image_base64"] = b64

        resp = requests.get("https://serpapi.com/search", params=params, timeout=60)
        if resp.status_code == 200:
            data = resp.json()
            # Visual matches
            for match in data.get("visual_matches", []):
                results.append(SearchResult(
                    engine="google_lens",
                    url=match.get("thumbnail", ""),
                    page_url=match.get("link", ""),
                    title=match.get("title", ""),
                    thumbnail_url=match.get("thumbnail", ""),
                ))
            # Knowledge graph
            for kg in data.get("knowledge_graph", []):
                results.append(SearchResult(
                    engine="google_lens_kg",
                    url=kg.get("images", [{}])[0].get("link", "") if kg.get("images") else "",
                    page_url=kg.get("link", ""),
                    title=kg.get("title", ""),
                ))
            print(f"    Found {len([r for r in results if 'google' in r.engine])} Google Lens results")
        else:
            print(f"    Google Lens search failed: {resp.status_code}")
    except Exception as e:
        print(f"    Google Lens search error: {e}")

    # --- Yandex via SerpAPI ---
    if image_url:
        print("[*] Searching Yandex via SerpAPI...")
        try:
            params = {
                "engine": "yandex_images",
                "url": image_url,
                "api_key": api_key,
            }
            resp = requests.get("https://serpapi.com/search", params=params, timeout=60)
            if resp.status_code == 200:
                data = resp.json()
                for img_result in data.get("image_results", []):
                    results.append(SearchResult(
                        engine="yandex",
                        url=img_result.get("original_image", {}).get("link", ""),
                        page_url=img_result.get("source", {}).get("link", ""),
                        title=img_result.get("source", {}).get("title", ""),
                        thumbnail_url=img_result.get("thumbnail", {}).get("link", ""),
                    ))
                print(f"    Found {len([r for r in results if r.engine == 'yandex'])} Yandex results")
            else:
                print(f"    Yandex search failed: {resp.status_code}")
        except Exception as e:
            print(f"    Yandex search error: {e}")

    # --- Google Reverse Image Search via SerpAPI ---
    if image_url:
        print("[*] Searching Google Reverse Image via SerpAPI...")
        try:
            params = {
                "engine": "google_reverse_image",
                "image_url": image_url,
                "api_key": api_key,
            }
            resp = requests.get("https://serpapi.com/search", params=params, timeout=60)
            if resp.status_code == 200:
                data = resp.json()
                for result_item in data.get("image_results", []):
                    results.append(SearchResult(
                        engine="google_reverse",
                        url=result_item.get("original_image", {}).get("link", ""),
                        page_url=result_item.get("link", ""),
                        title=result_item.get("title", ""),
                        thumbnail_url=result_item.get("thumbnail", ""),
                    ))
                # Inline images
                for inline in data.get("inline_images", []):
                    results.append(SearchResult(
                        engine="google_reverse",
                        url=inline.get("original", ""),
                        page_url=inline.get("source", ""),
                        title=inline.get("title", ""),
                        thumbnail_url=inline.get("thumbnail", ""),
                    ))
                cnt = len([r for r in results if r.engine == "google_reverse"])
                print(f"    Found {cnt} Google Reverse Image results")
            else:
                print(f"    Google Reverse Image failed: {resp.status_code}")
        except Exception as e:
            print(f"    Google Reverse Image error: {e}")

    return results


def search_bing_visual(image_path: str, api_key: str) -> list[SearchResult]:
    """Search using Bing Visual Search API (requires Azure Cognitive Services key)."""
    import requests

    results = []
    print("[*] Searching Bing Visual Search...")
    try:
        with open(image_path, "rb") as f:
            image_data = f.read()

        resp = requests.post(
            "https://api.bing.microsoft.com/v7.0/images/visualsearch",
            headers={"Ocp-Apim-Subscription-Key": api_key},
            files={"image": ("search.jpg", image_data, "image/jpeg")},
            timeout=60,
        )
        if resp.status_code == 200:
            data = resp.json()
            for tag in data.get("tags", []):
                for action in tag.get("actions", []):
                    if action.get("actionType") in ("VisualSearch", "PagesIncluding", "SimilarImages"):
                        for item in action.get("data", {}).get("value", []):
                            results.append(SearchResult(
                                engine="bing",
                                url=item.get("contentUrl", ""),
                                page_url=item.get("hostPageUrl", ""),
                                title=item.get("name", ""),
                                thumbnail_url=item.get("thumbnailUrl", ""),
                            ))
            print(f"    Found {len(results)} Bing results")
    except Exception as e:
        print(f"    Bing Visual Search error: {e}")

    return results


# ─── Direct Search (No API key needed) ──────────────────────────────────────

def search_tineye_direct(image_path: str) -> list[SearchResult]:
    """Search TinEye directly by uploading the image."""
    import requests

    results = []
    print("[*] Searching TinEye (direct upload)...")
    try:
        with open(image_path, "rb") as f:
            resp = requests.post(
                "https://tineye.com/result_json/",
                files={"image": ("search.jpg", f, "image/jpeg")},
                data={"sort": "score", "order": "desc"},
                headers={
                    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
                    "Accept": "application/json",
                },
                timeout=30,
            )
        if resp.status_code == 200:
            data = resp.json()
            for match in data.get("matches", []):
                for backlink in match.get("backlinks", []):
                    results.append(SearchResult(
                        engine="tineye",
                        url=match.get("image_url", ""),
                        page_url=backlink.get("url", ""),
                        title=backlink.get("url", ""),
                    ))
            print(f"    Found {len(results)} TinEye results")
        else:
            print(f"    TinEye returned status {resp.status_code}")
    except Exception as e:
        print(f"    TinEye search error: {e}")
    return results


def search_yandex_direct(image_path: str) -> list[SearchResult]:
    """
    Upload image directly to Yandex reverse image search.
    Yandex is particularly strong for face matching.
    """
    import requests

    results = []
    print("[*] Searching Yandex (direct upload)...")
    try:
        # Step 1: Upload image to get a CBIR ID
        with open(image_path, "rb") as f:
            resp = requests.post(
                "https://yandex.com/images-apphost/image-download",
                files={"upfile": ("face.jpg", f, "image/jpeg")},
                headers={
                    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
                },
                timeout=30,
            )
        if resp.status_code == 200:
            data = resp.json()
            image_url = data.get("url", "")
            image_shard = data.get("image_shard", "")
            image_id = data.get("image_id", "")

            if image_url:
                print(f"    Image uploaded, searching...")
                # Step 2: Search with the uploaded image
                search_url = (
                    f"https://yandex.com/images/search"
                    f"?rpt=imageview&url={urllib.parse.quote(image_url)}"
                    f"&cbir_id={image_shard}/{image_id}"
                )
                resp2 = requests.get(
                    search_url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
                    },
                    timeout=30,
                )
                # Parse basic results from the HTML
                if resp2.status_code == 200:
                    # Extract image URLs from response
                    import re
                    img_urls = re.findall(r'"img_href":"(https?://[^"]+)"', resp2.text)
                    page_urls = re.findall(r'"source_url":"(https?://[^"]+)"', resp2.text)
                    titles = re.findall(r'"snippet":\{"title":"([^"]*)"', resp2.text)

                    for i, img_url in enumerate(img_urls[:50]):
                        results.append(SearchResult(
                            engine="yandex_direct",
                            url=img_url,
                            page_url=page_urls[i] if i < len(page_urls) else "",
                            title=titles[i] if i < len(titles) else "",
                        ))
                    print(f"    Found {len(results)} Yandex direct results")
        else:
            print(f"    Yandex upload returned status {resp.status_code}")
    except Exception as e:
        print(f"    Yandex direct search error: {e}")
    return results


# ─── Image Downloading ──────────────────────────────────────────────────────

def download_image(url: str, output_dir: str, timeout: int = 15) -> Optional[str]:
    """Download an image from URL and return the local path."""
    import requests

    if not url or not url.startswith("http"):
        return None

    try:
        url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
        ext = ".jpg"
        if ".png" in url.lower():
            ext = ".png"
        elif ".webp" in url.lower():
            ext = ".webp"
        local_path = os.path.join(output_dir, f"dl_{url_hash}{ext}")

        if os.path.exists(local_path):
            return local_path

        resp = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"},
            timeout=timeout,
            stream=True,
        )
        if resp.status_code == 200:
            content_type = resp.headers.get("content-type", "")
            if "image" not in content_type and "octet" not in content_type:
                return None

            with open(local_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)

            # Verify it's actually an image
            try:
                img = Image.open(local_path)
                img.verify()
                return local_path
            except Exception:
                os.remove(local_path)
                return None
    except Exception:
        pass
    return None


# ─── Verification Pipeline ──────────────────────────────────────────────────

def verify_results(
    reference_face: str,
    search_results: list[SearchResult],
    output_dir: str,
    threshold: float = 0.60,
    max_downloads: int = 100,
) -> list[VerifiedMatch]:
    """
    Download candidate images and verify face matches against reference.
    Uses Facenet512 embeddings for comparison.
    """
    verified = []
    download_dir = os.path.join(output_dir, "downloads")
    os.makedirs(download_dir, exist_ok=True)

    # Deduplicate URLs
    seen_urls = set()
    unique_results = []
    for r in search_results:
        if r.url and r.url not in seen_urls:
            seen_urls.add(r.url)
            unique_results.append(r)

    print(f"\n[*] Downloading and verifying {min(len(unique_results), max_downloads)} candidate images...")

    # Download images in parallel
    downloaded = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {}
        for r in unique_results[:max_downloads]:
            future = executor.submit(download_image, r.url, download_dir)
            futures[future] = r

        for future in as_completed(futures):
            r = futures[future]
            local_path = future.result()
            if local_path:
                downloaded.append((r, local_path))

    print(f"[*] Successfully downloaded {len(downloaded)} images, verifying faces...")

    # Compare faces
    for i, (result, local_path) in enumerate(downloaded):
        if (i + 1) % 10 == 0:
            print(f"    Verified {i + 1}/{len(downloaded)}...")
        try:
            is_match, distance = compare_faces(reference_face, local_path, threshold)
            if is_match:
                verified.append(VerifiedMatch(
                    source_engine=result.engine,
                    image_url=result.url,
                    page_url=result.page_url,
                    title=result.title,
                    distance=distance,
                    local_path=local_path,
                ))
        except Exception:
            continue

    # Sort by best match (lowest distance)
    verified.sort(key=lambda m: m.distance)
    return verified


# ─── Report Generation ──────────────────────────────────────────────────────

def generate_report(report: SearchReport, output_dir: str) -> str:
    """Generate an HTML report of all matches."""
    html_path = os.path.join(output_dir, "report.html")

    html = """<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>Face Finder Results</title>
<style>
body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; background: #1a1a2e; color: #eee; }
h1 { color: #e94560; }
h2 { color: #0f3460; background: #16213e; padding: 10px; border-radius: 6px; }
.search-urls { background: #16213e; padding: 15px; border-radius: 8px; margin: 20px 0; }
.search-urls a { color: #e94560; display: block; margin: 5px 0; text-decoration: none; }
.search-urls a:hover { text-decoration: underline; }
.match { display: flex; gap: 15px; background: #16213e; padding: 15px; border-radius: 8px; margin: 10px 0; border-left: 4px solid #e94560; }
.match img { width: 150px; height: 150px; object-fit: cover; border-radius: 6px; }
.match-info { flex: 1; }
.match-info .distance { color: #0f0; font-weight: bold; }
.match-info a { color: #e94560; }
.stats { display: flex; gap: 20px; margin: 20px 0; }
.stat { background: #16213e; padding: 15px 25px; border-radius: 8px; text-align: center; }
.stat .num { font-size: 2em; color: #e94560; }
.instructions { background: #0f3460; padding: 20px; border-radius: 8px; margin: 20px 0; line-height: 1.8; }
.instructions ol { padding-left: 20px; }
</style></head><body>
"""
    html += f"<h1>Face Finder Results</h1>\n"
    html += f"<p>Input: <code>{report.input_image}</code></p>\n"

    html += '<div class="stats">\n'
    html += f'<div class="stat"><div class="num">{report.faces_detected}</div>Faces Detected</div>\n'
    html += f'<div class="stat"><div class="num">{len(report.raw_results)}</div>Search Results</div>\n'
    html += f'<div class="stat"><div class="num">{len(report.verified_matches)}</div>Verified Matches</div>\n'
    html += '</div>\n'

    # Manual search URLs
    html += '<h2>Manual Search Links (Open in Browser)</h2>\n'
    html += '<div class="instructions">\n'
    html += "<p><strong>For best results, manually search on these sites:</strong></p>\n"
    html += "<ol>\n"
    html += "<li><strong>Yandex Images</strong> - Best for face matching. Upload your photo at the link below.</li>\n"
    html += "<li><strong>Google Lens</strong> - Good general reverse search.</li>\n"
    html += "<li><strong>FaceCheck.ID</strong> - Dedicated face search engine (free tier available).</li>\n"
    html += "<li><strong>PimEyes</strong> - Powerful face search (limited free searches).</li>\n"
    html += "<li><strong>TinEye</strong> - Finds exact/near-exact copies of the image.</li>\n"
    html += "</ol>\n"
    html += "</div>\n"
    html += '<div class="search-urls">\n'
    for engine, url in report.search_urls.items():
        html += f'<a href="{url}" target="_blank">{engine}: {url}</a>\n'
    html += '</div>\n'

    # Verified matches
    if report.verified_matches:
        html += '<h2>Verified Face Matches</h2>\n'
        for match in report.verified_matches:
            confidence = max(0, (1 - match.distance) * 100)
            html += '<div class="match">\n'
            if match.local_path and os.path.exists(match.local_path):
                rel_path = os.path.relpath(match.local_path, output_dir)
                html += f'<img src="{rel_path}" alt="match">\n'
            html += '<div class="match-info">\n'
            html += f'<p class="distance">Match Confidence: {confidence:.1f}%</p>\n'
            html += f'<p>Engine: {match.source_engine}</p>\n'
            if match.title:
                html += f'<p>Title: {match.title}</p>\n'
            if match.page_url:
                html += f'<p>Page: <a href="{match.page_url}" target="_blank">{match.page_url[:80]}...</a></p>\n'
            if match.image_url:
                html += f'<p>Image: <a href="{match.image_url}" target="_blank">{match.image_url[:80]}...</a></p>\n'
            html += '</div></div>\n'
    elif report.raw_results:
        html += '<h2>Unverified Results (Face verification not run or no matches)</h2>\n'
        for r in report.raw_results[:50]:
            html += '<div class="match">\n'
            html += '<div class="match-info">\n'
            html += f'<p>Engine: {r.engine}</p>\n'
            if r.title:
                html += f'<p>Title: {r.title}</p>\n'
            if r.page_url:
                html += f'<p>Page: <a href="{r.page_url}" target="_blank">{r.page_url[:80]}...</a></p>\n'
            if r.url:
                html += f'<p>Image: <a href="{r.url}" target="_blank">{r.url[:80]}...</a></p>\n'
            html += '</div></div>\n'

    html += "</body></html>"

    with open(html_path, "w") as f:
        f.write(html)

    # Also save JSON report
    json_path = os.path.join(output_dir, "report.json")
    json_data = {
        "input_image": report.input_image,
        "faces_detected": report.faces_detected,
        "search_urls": report.search_urls,
        "raw_results_count": len(report.raw_results),
        "verified_matches": [
            {
                "source_engine": m.source_engine,
                "image_url": m.image_url,
                "page_url": m.page_url,
                "title": m.title,
                "confidence": round(max(0, (1 - m.distance) * 100), 1),
                "distance": round(m.distance, 4),
            }
            for m in report.verified_matches
        ],
    }
    with open(json_path, "w") as f:
        json.dump(json_data, f, indent=2)

    return html_path


# ─── Main Pipeline ──────────────────────────────────────────────────────────

def run_search(
    image_path: str,
    output_dir: str = "face_finder_results",
    serpapi_key: Optional[str] = None,
    bing_key: Optional[str] = None,
    verify: bool = True,
    threshold: float = 0.60,
    max_downloads: int = 100,
) -> SearchReport:
    """
    Run the full face finder pipeline.

    Args:
        image_path: Path to the input photo
        output_dir: Directory to save results
        serpapi_key: Optional SerpAPI key for automated search
        bing_key: Optional Bing Visual Search API key
        verify: Whether to download and verify faces
        threshold: Face match threshold (lower = stricter, default 0.60)
        max_downloads: Maximum images to download for verification
    """
    os.makedirs(output_dir, exist_ok=True)

    report = SearchReport(input_image=image_path)

    # Step 1: Detect and prepare face
    print("=" * 60)
    print("FACE FINDER - Reverse Face Search Tool")
    print("=" * 60)
    print(f"\n[*] Processing: {image_path}")

    face_path = prepare_face_image(image_path, output_dir)
    faces = detect_faces(image_path)
    report.faces_detected = len(faces)
    print(f"[*] Face image saved to: {face_path}")

    # Step 2: Generate manual search URLs
    report.search_urls = get_search_urls(face_path)

    # Step 3: Automated searches
    all_results = []

    # Direct searches (no API key needed)
    try:
        all_results.extend(search_tineye_direct(face_path))
    except Exception as e:
        print(f"[!] TinEye error: {e}")

    try:
        all_results.extend(search_yandex_direct(face_path))
    except Exception as e:
        print(f"[!] Yandex error: {e}")

    # SerpAPI searches
    if serpapi_key:
        try:
            all_results.extend(search_serpapi(face_path, serpapi_key))
        except Exception as e:
            print(f"[!] SerpAPI error: {e}")

    # Bing Visual Search
    if bing_key:
        try:
            all_results.extend(search_bing_visual(face_path, bing_key))
        except Exception as e:
            print(f"[!] Bing error: {e}")

    report.raw_results = all_results
    print(f"\n[*] Total search results: {len(all_results)}")

    # Step 4: Verify face matches
    if verify and all_results:
        verified = verify_results(face_path, all_results, output_dir, threshold, max_downloads)
        report.verified_matches = verified
        print(f"[*] Verified face matches: {len(verified)}")
    elif not all_results:
        print("\n[*] No automated results found.")
        print("[*] Use the manual search URLs in the report for best results!")

    # Step 5: Generate report
    html_path = generate_report(report, output_dir)
    print(f"\n{'=' * 60}")
    print(f"RESULTS SAVED")
    print(f"{'=' * 60}")
    print(f"  HTML Report: {html_path}")
    print(f"  JSON Report: {os.path.join(output_dir, 'report.json')}")
    print(f"  Face Image:  {face_path}")
    if report.verified_matches:
        print(f"  Matches:     {len(report.verified_matches)} verified face matches")
    print(f"\n[*] For best results, also manually search on:")
    print(f"    - https://yandex.com/images/ (best face matching)")
    print(f"    - https://facecheck.id/ (dedicated face search)")
    print(f"    - https://pimeyes.com/ (face search engine)")
    print(f"    - https://lens.google.com/ (Google Lens)")
    print()

    return report


def main():
    parser = argparse.ArgumentParser(
        description="Face Finder - Find all photos of a person online using reverse face search",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage - generates search URLs and runs direct searches
  python face_finder.py photo.jpg

  # With SerpAPI key for automated Google Lens + Yandex searching
  python face_finder.py photo.jpg --serpapi-key sk-xxxx

  # With Bing Visual Search API key
  python face_finder.py photo.jpg --bing-key xxxx

  # Custom output directory and stricter matching
  python face_finder.py photo.jpg --output my_results --threshold 0.45

  # Skip face verification (just collect URLs)
  python face_finder.py photo.jpg --no-verify

  # Use all available APIs
  python face_finder.py photo.jpg --serpapi-key sk-xxx --bing-key yyy

Tips:
  - For best results, use a clear, well-lit frontal face photo
  - Yandex is the #1 search engine for face matching
  - FaceCheck.ID and PimEyes are dedicated face search engines
  - Lower threshold = stricter matching (fewer false positives)
  - Use --serpapi-key for the most comprehensive automated results
        """,
    )

    parser.add_argument("image", help="Path to the face photo to search for")
    parser.add_argument("--output", "-o", default="face_finder_results",
                        help="Output directory (default: face_finder_results)")
    parser.add_argument("--serpapi-key", help="SerpAPI key for Google Lens + Yandex search")
    parser.add_argument("--bing-key", help="Bing Visual Search API key")
    parser.add_argument("--threshold", "-t", type=float, default=0.60,
                        help="Face match threshold, lower=stricter (default: 0.60)")
    parser.add_argument("--max-downloads", type=int, default=100,
                        help="Max images to download for verification (default: 100)")
    parser.add_argument("--no-verify", action="store_true",
                        help="Skip face verification (just collect search results)")

    args = parser.parse_args()

    if not os.path.exists(args.image):
        print(f"Error: Image not found: {args.image}")
        sys.exit(1)

    # Check for API keys in environment
    serpapi_key = args.serpapi_key or os.environ.get("SERPAPI_KEY")
    bing_key = args.bing_key or os.environ.get("BING_VISUAL_SEARCH_KEY")

    run_search(
        image_path=args.image,
        output_dir=args.output,
        serpapi_key=serpapi_key,
        bing_key=bing_key,
        verify=not args.no_verify,
        threshold=args.threshold,
        max_downloads=args.max_downloads,
    )


if __name__ == "__main__":
    main()
