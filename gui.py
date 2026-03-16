#!/usr/bin/env python3
"""
Face Finder GUI - Interactive web interface for reverse face search.

Launch with:
    python gui.py
    python gui.py --port 8080
    python gui.py --serpapi-key YOUR_KEY --bing-key YOUR_KEY

Then open http://localhost:5000 in your browser.
"""

import argparse
import base64
import io
import json
import os
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path

from flask import Flask, render_template_string, request, jsonify, send_from_directory

import face_finder

app = Flask(__name__)

# Global config set from CLI args
CONFIG = {
    "serpapi_key": None,
    "bing_key": None,
}

# In-memory job tracking: job_id -> job state
JOBS = {}

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Face Finder</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #0d1117; color: #c9d1d9; min-height: 100vh;
}
.header {
    background: linear-gradient(135deg, #161b22 0%, #0d1117 100%);
    border-bottom: 1px solid #30363d;
    padding: 20px 40px; display: flex; align-items: center; gap: 16px;
}
.header h1 { font-size: 24px; color: #f0f6fc; }
.header h1 span { color: #e85d75; }
.container { max-width: 1400px; margin: 0 auto; padding: 30px 40px; }

/* Upload area */
.upload-area {
    border: 2px dashed #30363d; border-radius: 16px;
    padding: 60px 40px; text-align: center;
    transition: all 0.3s ease; cursor: pointer;
    background: #161b22; position: relative;
}
.upload-area:hover, .upload-area.dragover {
    border-color: #e85d75; background: #1c2333;
}
.upload-area h2 { font-size: 22px; margin-bottom: 10px; color: #f0f6fc; }
.upload-area p { color: #8b949e; margin-bottom: 20px; }
.upload-area input[type="file"] {
    position: absolute; inset: 0; opacity: 0; cursor: pointer;
}
.upload-btn {
    display: inline-block; background: #e85d75; color: #fff;
    padding: 12px 32px; border-radius: 8px; font-size: 16px; font-weight: 600;
    border: none; cursor: pointer; transition: background 0.2s;
}
.upload-btn:hover { background: #d44a64; }

/* Preview */
.preview-section {
    display: none; margin-top: 30px;
    background: #161b22; border-radius: 16px; padding: 24px;
    border: 1px solid #30363d;
}
.preview-section.show { display: block; }
.preview-row { display: flex; align-items: center; gap: 24px; flex-wrap: wrap; }
.preview-img {
    width: 180px; height: 180px; object-fit: cover; border-radius: 12px;
    border: 3px solid #e85d75;
}
.preview-info { flex: 1; min-width: 200px; }
.preview-info h3 { color: #f0f6fc; margin-bottom: 8px; }

/* Settings */
.settings-row {
    display: flex; gap: 16px; margin-top: 16px; flex-wrap: wrap;
}
.setting-group { display: flex; flex-direction: column; gap: 4px; }
.setting-group label { font-size: 13px; color: #8b949e; }
.setting-group input, .setting-group select {
    background: #0d1117; border: 1px solid #30363d; color: #c9d1d9;
    padding: 8px 12px; border-radius: 6px; font-size: 14px;
}
.search-btn {
    background: #e85d75; color: #fff; padding: 12px 40px;
    border-radius: 8px; font-size: 16px; font-weight: 600;
    border: none; cursor: pointer; margin-top: 20px;
    transition: background 0.2s;
}
.search-btn:hover { background: #d44a64; }
.search-btn:disabled { background: #484f58; cursor: not-allowed; }

/* Progress */
.progress-section {
    display: none; margin-top: 30px;
    background: #161b22; border-radius: 16px; padding: 24px;
    border: 1px solid #30363d;
}
.progress-section.show { display: block; }
.progress-bar-bg {
    width: 100%; height: 8px; background: #21262d; border-radius: 4px;
    overflow: hidden; margin: 16px 0;
}
.progress-bar {
    height: 100%; background: linear-gradient(90deg, #e85d75, #f78166);
    border-radius: 4px; transition: width 0.4s ease; width: 0%;
}
.progress-log {
    background: #0d1117; border-radius: 8px; padding: 12px 16px;
    font-family: 'SF Mono', Consolas, monospace; font-size: 13px;
    max-height: 200px; overflow-y: auto; color: #8b949e;
    margin-top: 12px;
}
.progress-log .log-line { margin: 3px 0; }
.progress-log .log-line.highlight { color: #58a6ff; }

/* Results grid */
.results-section {
    display: none; margin-top: 30px;
}
.results-section.show { display: block; }
.results-header {
    display: flex; justify-content: space-between; align-items: center;
    margin-bottom: 20px;
}
.results-header h2 { color: #f0f6fc; font-size: 22px; }
.results-count {
    background: #e85d75; color: #fff; padding: 4px 14px;
    border-radius: 20px; font-weight: 600; font-size: 14px;
}
.results-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 16px;
}
.result-card {
    background: #161b22; border-radius: 12px; overflow: hidden;
    border: 1px solid #30363d; transition: all 0.25s ease;
    cursor: pointer; position: relative;
}
.result-card:hover {
    border-color: #e85d75; transform: translateY(-4px);
    box-shadow: 0 8px 24px rgba(232,93,117,0.2);
}
.result-card img {
    width: 100%; height: 200px; object-fit: cover;
    display: block;
}
.result-card .card-info {
    padding: 12px; min-height: 80px;
}
.result-card .confidence {
    display: inline-block; background: #1f6f2b; color: #3fb950;
    padding: 2px 10px; border-radius: 12px; font-size: 12px;
    font-weight: 600; margin-bottom: 6px;
}
.result-card .confidence.high { background: #1f6f2b; color: #3fb950; }
.result-card .confidence.medium { background: #5a4a00; color: #d29922; }
.result-card .confidence.low { background: #6e3630; color: #f85149; }
.result-card .engine {
    font-size: 11px; color: #8b949e; text-transform: uppercase;
    letter-spacing: 0.5px;
}
.result-card .title {
    font-size: 13px; color: #c9d1d9; margin-top: 4px;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.result-card .open-link {
    position: absolute; top: 8px; right: 8px;
    background: rgba(0,0,0,0.7); color: #fff; border-radius: 50%;
    width: 32px; height: 32px; display: flex; align-items: center;
    justify-content: center; opacity: 0; transition: opacity 0.2s;
    font-size: 16px; text-decoration: none;
}
.result-card:hover .open-link { opacity: 1; }

/* No results */
.no-results {
    text-align: center; padding: 60px 20px;
    background: #161b22; border-radius: 16px;
    border: 1px solid #30363d;
}
.no-results h3 { color: #f0f6fc; margin-bottom: 10px; }
.no-results p { color: #8b949e; }
.manual-links { margin-top: 20px; }
.manual-links a {
    display: inline-block; margin: 6px; padding: 8px 16px;
    background: #21262d; border-radius: 8px; color: #58a6ff;
    text-decoration: none; font-size: 14px; border: 1px solid #30363d;
    transition: all 0.2s;
}
.manual-links a:hover { background: #30363d; border-color: #58a6ff; }

.spinner {
    display: inline-block; width: 20px; height: 20px;
    border: 3px solid #30363d; border-top-color: #e85d75;
    border-radius: 50%; animation: spin 0.8s linear infinite;
    vertical-align: middle; margin-right: 8px;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
</head>
<body>
<div class="header">
    <h1><span>Face</span> Finder</h1>
</div>
<div class="container">
    <!-- Upload -->
    <div class="upload-area" id="uploadArea">
        <h2>Drop a face photo here</h2>
        <p>or click to browse &mdash; JPG, PNG, WEBP supported</p>
        <button class="upload-btn">Choose Photo</button>
        <input type="file" id="fileInput" accept="image/*">
    </div>

    <!-- Preview + Settings -->
    <div class="preview-section" id="previewSection">
        <div class="preview-row">
            <img id="previewImg" class="preview-img" src="" alt="preview">
            <div class="preview-info">
                <h3 id="fileName">photo.jpg</h3>
                <div class="settings-row">
                    <div class="setting-group">
                        <label>Match Threshold</label>
                        <select id="threshold">
                            <option value="0.45">Strict (0.45)</option>
                            <option value="0.55">Moderate (0.55)</option>
                            <option value="0.60" selected>Default (0.60)</option>
                            <option value="0.70">Loose (0.70)</option>
                        </select>
                    </div>
                    <div class="setting-group">
                        <label>Max Downloads</label>
                        <select id="maxDownloads">
                            <option value="50">50</option>
                            <option value="100" selected>100</option>
                            <option value="200">200</option>
                            <option value="500">500</option>
                        </select>
                    </div>
                </div>
                <button class="search-btn" id="searchBtn" onclick="startSearch()">
                    Search the Internet
                </button>
            </div>
        </div>
    </div>

    <!-- Progress -->
    <div class="progress-section" id="progressSection">
        <h3><span class="spinner"></span> <span id="progressTitle">Searching...</span></h3>
        <div class="progress-bar-bg"><div class="progress-bar" id="progressBar"></div></div>
        <div class="progress-log" id="progressLog"></div>
    </div>

    <!-- Results -->
    <div class="results-section" id="resultsSection">
        <div class="results-header">
            <h2>Matches Found</h2>
            <span class="results-count" id="resultsCount">0</span>
        </div>
        <div class="results-grid" id="resultsGrid"></div>
    </div>
</div>

<script>
const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const previewSection = document.getElementById('previewSection');
const previewImg = document.getElementById('previewImg');
const fileName = document.getElementById('fileName');
const searchBtn = document.getElementById('searchBtn');
const progressSection = document.getElementById('progressSection');
const progressBar = document.getElementById('progressBar');
const progressTitle = document.getElementById('progressTitle');
const progressLog = document.getElementById('progressLog');
const resultsSection = document.getElementById('resultsSection');
const resultsCount = document.getElementById('resultsCount');
const resultsGrid = document.getElementById('resultsGrid');

let selectedFile = null;
let currentJobId = null;

// Drag and drop
uploadArea.addEventListener('dragover', e => { e.preventDefault(); uploadArea.classList.add('dragover'); });
uploadArea.addEventListener('dragleave', () => uploadArea.classList.remove('dragover'));
uploadArea.addEventListener('drop', e => {
    e.preventDefault(); uploadArea.classList.remove('dragover');
    if (e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]);
});
fileInput.addEventListener('change', e => { if (e.target.files.length) handleFile(e.target.files[0]); });

function handleFile(file) {
    if (!file.type.startsWith('image/')) { alert('Please select an image file.'); return; }
    selectedFile = file;
    const reader = new FileReader();
    reader.onload = e => {
        previewImg.src = e.target.result;
        fileName.textContent = file.name;
        previewSection.classList.add('show');
        resultsSection.classList.remove('show');
        progressSection.classList.remove('show');
    };
    reader.readAsDataURL(file);
}

function startSearch() {
    if (!selectedFile) return;
    searchBtn.disabled = true;
    searchBtn.textContent = 'Searching...';
    progressSection.classList.add('show');
    resultsSection.classList.remove('show');
    progressLog.innerHTML = '';
    progressBar.style.width = '0%';

    const formData = new FormData();
    formData.append('image', selectedFile);
    formData.append('threshold', document.getElementById('threshold').value);
    formData.append('max_downloads', document.getElementById('maxDownloads').value);

    fetch('/api/search', { method: 'POST', body: formData })
        .then(r => r.json())
        .then(data => {
            if (data.job_id) {
                currentJobId = data.job_id;
                pollJob(data.job_id);
            } else {
                addLog('Error: ' + (data.error || 'Unknown error'));
                searchBtn.disabled = false;
                searchBtn.textContent = 'Search the Internet';
            }
        })
        .catch(err => {
            addLog('Network error: ' + err);
            searchBtn.disabled = false;
            searchBtn.textContent = 'Search the Internet';
        });
}

function addLog(msg) {
    const div = document.createElement('div');
    div.className = 'log-line' + (msg.startsWith('[*]') ? ' highlight' : '');
    div.textContent = msg;
    progressLog.appendChild(div);
    progressLog.scrollTop = progressLog.scrollHeight;
}

function pollJob(jobId) {
    fetch('/api/status/' + jobId)
        .then(r => r.json())
        .then(data => {
            // Update log
            if (data.logs) {
                progressLog.innerHTML = '';
                data.logs.forEach(l => addLog(l));
            }
            // Update progress
            if (data.progress !== undefined) {
                progressBar.style.width = data.progress + '%';
            }
            progressTitle.textContent = data.stage || 'Searching...';

            if (data.status === 'done') {
                progressBar.style.width = '100%';
                progressTitle.textContent = 'Complete!';
                renderResults(data.results, data.search_urls);
                searchBtn.disabled = false;
                searchBtn.textContent = 'Search Again';
            } else if (data.status === 'error') {
                addLog('Error: ' + data.error);
                searchBtn.disabled = false;
                searchBtn.textContent = 'Search the Internet';
            } else {
                setTimeout(() => pollJob(jobId), 1000);
            }
        })
        .catch(() => setTimeout(() => pollJob(jobId), 2000));
}

function renderResults(results, searchUrls) {
    resultsSection.classList.add('show');
    resultsGrid.innerHTML = '';
    resultsCount.textContent = results.length;

    if (results.length === 0) {
        resultsGrid.innerHTML = `
            <div class="no-results" style="grid-column:1/-1">
                <h3>No verified face matches found</h3>
                <p>Try these manual search engines for deeper results:</p>
                <div class="manual-links">
                    <a href="https://yandex.com/images/" target="_blank">Yandex Images</a>
                    <a href="https://facecheck.id/" target="_blank">FaceCheck.ID</a>
                    <a href="https://pimeyes.com/en" target="_blank">PimEyes</a>
                    <a href="https://lens.google.com/" target="_blank">Google Lens</a>
                    <a href="https://tineye.com/" target="_blank">TinEye</a>
                </div>
            </div>`;
        return;
    }

    results.forEach(match => {
        const card = document.createElement('div');
        card.className = 'result-card';
        const conf = match.confidence;
        const confClass = conf >= 80 ? 'high' : conf >= 60 ? 'medium' : 'low';
        const pageUrl = match.page_url || match.image_url || '#';
        const imgSrc = match.thumbnail || match.image_url || '';
        const title = match.title || new URL(pageUrl).hostname || 'Unknown source';

        card.innerHTML = `
            <img src="${imgSrc}" alt="match" onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%22200%22 height=%22200%22><rect fill=%22%23161b22%22 width=%22200%22 height=%22200%22/><text fill=%22%238b949e%22 x=%2250%25%22 y=%2250%25%22 text-anchor=%22middle%22 dy=%22.3em%22 font-size=%2214%22>No preview</text></svg>'">
            <a class="open-link" href="${pageUrl}" target="_blank" title="Open source page">&#8599;</a>
            <div class="card-info">
                <span class="confidence ${confClass}">${conf.toFixed(1)}% match</span>
                <div class="engine">${match.source_engine}</div>
                <div class="title" title="${title}">${title}</div>
            </div>`;

        card.addEventListener('click', e => {
            if (e.target.tagName === 'A') return;
            window.open(pageUrl, '_blank');
        });
        resultsGrid.appendChild(card);
    });
}
</script>
</body>
</html>"""


@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route("/api/search", methods=["POST"])
def api_search():
    """Accept an image upload and start a background search job."""
    if "image" not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    file = request.files["image"]
    if not file.filename:
        return jsonify({"error": "Empty filename"}), 400

    threshold = float(request.form.get("threshold", 0.60))
    max_downloads = int(request.form.get("max_downloads", 100))

    # Save uploaded image to temp dir
    job_id = str(uuid.uuid4())[:8]
    job_dir = os.path.join(tempfile.gettempdir(), "face_finder_jobs", job_id)
    os.makedirs(job_dir, exist_ok=True)

    ext = Path(file.filename).suffix or ".jpg"
    input_path = os.path.join(job_dir, f"input{ext}")
    file.save(input_path)

    output_dir = os.path.join(job_dir, "results")
    os.makedirs(output_dir, exist_ok=True)

    JOBS[job_id] = {
        "status": "running",
        "stage": "Initializing...",
        "progress": 0,
        "logs": [],
        "results": [],
        "search_urls": {},
        "error": None,
    }

    # Run search in background thread
    thread = threading.Thread(
        target=_run_search_job,
        args=(job_id, input_path, output_dir, threshold, max_downloads),
        daemon=True,
    )
    thread.start()

    return jsonify({"job_id": job_id})


def _log(job_id, msg):
    if job_id in JOBS:
        JOBS[job_id]["logs"].append(msg)


def _run_search_job(job_id, input_path, output_dir, threshold, max_downloads):
    """Run the full search pipeline in a background thread."""
    job = JOBS[job_id]
    try:
        # Step 1: Face detection
        job["stage"] = "Detecting faces..."
        job["progress"] = 5
        _log(job_id, "[*] Detecting faces in uploaded image...")

        face_path = face_finder.prepare_face_image(input_path, output_dir)
        faces = face_finder.detect_faces(input_path)
        _log(job_id, f"[*] Found {len(faces)} face(s)")
        job["progress"] = 10

        # Step 2: Generate search URLs
        search_urls = face_finder.get_search_urls(face_path)
        job["search_urls"] = search_urls

        # Step 3: Run searches
        all_results = []

        # Direct searches (no API key)
        job["stage"] = "Searching TinEye..."
        job["progress"] = 15
        _log(job_id, "[*] Searching TinEye (direct upload)...")
        try:
            tineye_results = face_finder.search_tineye_direct(face_path)
            all_results.extend(tineye_results)
            _log(job_id, f"    Found {len(tineye_results)} TinEye results")
        except Exception as e:
            _log(job_id, f"    TinEye error: {e}")

        job["stage"] = "Searching Yandex..."
        job["progress"] = 25
        _log(job_id, "[*] Searching Yandex (direct upload)...")
        try:
            yandex_results = face_finder.search_yandex_direct(face_path)
            all_results.extend(yandex_results)
            _log(job_id, f"    Found {len(yandex_results)} Yandex results")
        except Exception as e:
            _log(job_id, f"    Yandex error: {e}")

        # SerpAPI searches
        serpapi_key = CONFIG.get("serpapi_key") or os.environ.get("SERPAPI_KEY")
        if serpapi_key:
            job["stage"] = "Searching Google Lens + Yandex via SerpAPI..."
            job["progress"] = 35
            _log(job_id, "[*] Searching via SerpAPI (Google Lens + Yandex)...")
            try:
                serp_results = face_finder.search_serpapi(face_path, serpapi_key)
                all_results.extend(serp_results)
                _log(job_id, f"    Found {len(serp_results)} SerpAPI results")
            except Exception as e:
                _log(job_id, f"    SerpAPI error: {e}")

        # Bing Visual Search
        bing_key = CONFIG.get("bing_key") or os.environ.get("BING_VISUAL_SEARCH_KEY")
        if bing_key:
            job["stage"] = "Searching Bing Visual Search..."
            job["progress"] = 45
            _log(job_id, "[*] Searching Bing Visual Search...")
            try:
                bing_results = face_finder.search_bing_visual(face_path, bing_key)
                all_results.extend(bing_results)
                _log(job_id, f"    Found {len(bing_results)} Bing results")
            except Exception as e:
                _log(job_id, f"    Bing error: {e}")

        _log(job_id, f"[*] Total search results: {len(all_results)}")
        job["progress"] = 50

        # Step 4: Verify matches
        if all_results:
            job["stage"] = "Downloading & verifying faces..."
            _log(job_id, f"[*] Downloading and verifying up to {max_downloads} candidate images...")

            # Use the verify pipeline but capture progress
            download_dir = os.path.join(output_dir, "downloads")
            os.makedirs(download_dir, exist_ok=True)

            # Deduplicate
            seen = set()
            unique = []
            for r in all_results:
                if r.url and r.url not in seen:
                    seen.add(r.url)
                    unique.append(r)

            total_to_check = min(len(unique), max_downloads)
            _log(job_id, f"[*] {total_to_check} unique images to check")

            # Download in parallel
            from concurrent.futures import ThreadPoolExecutor, as_completed
            downloaded = []
            with ThreadPoolExecutor(max_workers=8) as executor:
                futures = {}
                for r in unique[:max_downloads]:
                    future = executor.submit(face_finder.download_image, r.url, download_dir)
                    futures[future] = r

                done_count = 0
                for future in as_completed(futures):
                    done_count += 1
                    r = futures[future]
                    local_path = future.result()
                    if local_path:
                        downloaded.append((r, local_path))
                    if done_count % 10 == 0:
                        pct = 50 + int((done_count / total_to_check) * 25)
                        job["progress"] = min(pct, 75)
                        job["stage"] = f"Downloaded {done_count}/{total_to_check}..."

            _log(job_id, f"[*] Downloaded {len(downloaded)} images, verifying faces...")
            job["progress"] = 75
            job["stage"] = "Verifying faces with FaceNet512..."

            # Verify
            verified = []
            for i, (result, local_path) in enumerate(downloaded):
                try:
                    is_match, distance = face_finder.compare_faces(
                        face_path, local_path, threshold
                    )
                    if is_match:
                        verified.append({
                            "source_engine": result.engine,
                            "image_url": result.url,
                            "page_url": result.page_url,
                            "title": result.title,
                            "thumbnail": result.thumbnail_url or result.url,
                            "distance": round(distance, 4),
                            "confidence": round(max(0, (1 - distance) * 100), 1),
                        })
                except Exception:
                    continue

                if (i + 1) % 10 == 0:
                    pct = 75 + int(((i + 1) / len(downloaded)) * 20)
                    job["progress"] = min(pct, 95)
                    job["stage"] = f"Verified {i+1}/{len(downloaded)} faces..."
                    _log(job_id, f"    Verified {i+1}/{len(downloaded)}...")

            # Sort by confidence (lowest distance = best)
            verified.sort(key=lambda m: m["distance"])
            job["results"] = verified
            _log(job_id, f"[*] Found {len(verified)} verified face matches!")
        else:
            _log(job_id, "[*] No automated results found.")
            _log(job_id, "[*] Try the manual search links for better results.")
            job["results"] = []

        job["status"] = "done"
        job["progress"] = 100
        job["stage"] = "Complete!"

    except Exception as e:
        job["status"] = "error"
        job["error"] = str(e)
        _log(job_id, f"[!] Error: {e}")


@app.route("/api/status/<job_id>")
def api_status(job_id):
    """Poll job status."""
    job = JOBS.get(job_id)
    if not job:
        return jsonify({"status": "error", "error": "Job not found"}), 404
    return jsonify(job)


def main():
    parser = argparse.ArgumentParser(description="Face Finder - Interactive Web GUI")
    parser.add_argument("--port", "-p", type=int, default=5000, help="Port (default: 5000)")
    parser.add_argument("--host", default="0.0.0.0", help="Host (default: 0.0.0.0)")
    parser.add_argument("--serpapi-key", help="SerpAPI key for automated search")
    parser.add_argument("--bing-key", help="Bing Visual Search API key")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()

    CONFIG["serpapi_key"] = args.serpapi_key or os.environ.get("SERPAPI_KEY")
    CONFIG["bing_key"] = args.bing_key or os.environ.get("BING_VISUAL_SEARCH_KEY")

    print(f"\n{'='*50}")
    print(f"  Face Finder GUI")
    print(f"{'='*50}")
    print(f"  Open: http://localhost:{args.port}")
    if CONFIG["serpapi_key"]:
        print(f"  SerpAPI: configured")
    if CONFIG["bing_key"]:
        print(f"  Bing API: configured")
    print(f"{'='*50}\n")

    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
