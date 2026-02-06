"""
Find Book Agent
---------------
Searches for a book by title/author and downloads the best available
digital copy (PDF or EPUB). Uses multiple sources:
  1. Open Library (free, legal)
  2. Project Gutenberg (public domain)
  3. Google Books (preview/free ebooks)
"""

import os
import re
import requests
from pathlib import Path

STAGING_DIR = Path(os.getenv("LOCAL_STAGING_DIR", "./staging"))


def _sanitize(name: str) -> str:
    return re.sub(r'[^\w\s-]', '', name).strip().replace(' ', '_')[:80]


def _search_open_library(title: str) -> dict | None:
    """Search Open Library and return best match with download links."""
    print(f"[FindBook] Searching Open Library for: {title}")
    resp = requests.get(
        "https://openlibrary.org/search.json",
        params={"title": title, "limit": 5},
        timeout=30,
    )
    if resp.status_code != 200:
        return None

    docs = resp.json().get("docs", [])
    for doc in docs:
        ebook_access = doc.get("ebook_access", "no_ebook")
        if ebook_access in ("borrowable", "public"):
            edition_key = doc.get("cover_edition_key") or (
                doc["edition_key"][0] if doc.get("edition_key") else None
            )
            if edition_key:
                return {
                    "title": doc.get("title", title),
                    "author": ", ".join(doc.get("author_name", ["Unknown"])),
                    "source": "open_library",
                    "edition_key": edition_key,
                    "ol_key": doc.get("key", ""),
                }
    return None


def _download_from_open_library(edition_key: str, dest_dir: Path) -> Path | None:
    """Try to download PDF or EPUB from Open Library."""
    for fmt, ext in [("pdf", ".pdf"), ("epub", ".epub")]:
        url = f"https://openlibrary.org/books/{edition_key}.{fmt}"
        print(f"[FindBook]   Trying {url}")
        try:
            resp = requests.get(url, timeout=60, stream=True, allow_redirects=True)
            if resp.status_code == 200 and len(resp.content) > 1000:
                out = dest_dir / f"book{ext}"
                out.write_bytes(resp.content)
                print(f"[FindBook]   Downloaded {ext} ({len(resp.content)} bytes)")
                return out
        except Exception as e:
            print(f"[FindBook]   Failed: {e}")
    return None


def _search_gutenberg(title: str) -> dict | None:
    """Search Project Gutenberg for public domain books."""
    print(f"[FindBook] Searching Project Gutenberg for: {title}")
    resp = requests.get(
        "https://gutendex.com/books/",
        params={"search": title},
        timeout=30,
    )
    if resp.status_code != 200:
        return None

    results = resp.json().get("results", [])
    for book in results:
        formats = book.get("formats", {})
        for mime in ["application/epub+zip", "application/pdf"]:
            if mime in formats:
                return {
                    "title": book.get("title", title),
                    "author": ", ".join(
                        a.get("name", "Unknown") for a in book.get("authors", [])
                    ),
                    "source": "gutenberg",
                    "download_url": formats[mime],
                    "format": "epub" if "epub" in mime else "pdf",
                }
    return None


def _download_url(url: str, dest_dir: Path, fmt: str) -> Path | None:
    """Download a file from a direct URL."""
    ext = f".{fmt}"
    try:
        resp = requests.get(url, timeout=120, stream=True)
        if resp.status_code == 200:
            out = dest_dir / f"book{ext}"
            out.write_bytes(resp.content)
            print(f"[FindBook]   Downloaded {ext} ({len(resp.content)} bytes)")
            return out
    except Exception as e:
        print(f"[FindBook]   Download failed: {e}")
    return None


def _search_google_books(title: str) -> dict | None:
    """Search Google Books for free ebooks."""
    api_key = os.getenv("GOOGLE_BOOKS_API_KEY", "")
    params = {"q": title, "maxResults": 5, "filter": "free-ebooks"}
    if api_key:
        params["key"] = api_key

    print(f"[FindBook] Searching Google Books for: {title}")
    try:
        resp = requests.get(
            "https://www.googleapis.com/books/v1/volumes",
            params=params,
            timeout=30,
        )
        if resp.status_code != 200:
            return None

        items = resp.json().get("items", [])
        for item in items:
            info = item.get("volumeInfo", {})
            access = item.get("accessInfo", {})
            pdf_info = access.get("pdf", {})
            epub_info = access.get("epub", {})

            dl_link = None
            fmt = None
            if pdf_info.get("isAvailable") and pdf_info.get("downloadLink"):
                dl_link = pdf_info["downloadLink"]
                fmt = "pdf"
            elif epub_info.get("isAvailable") and epub_info.get("downloadLink"):
                dl_link = epub_info["downloadLink"]
                fmt = "epub"

            if dl_link:
                return {
                    "title": info.get("title", title),
                    "author": ", ".join(info.get("authors", ["Unknown"])),
                    "source": "google_books",
                    "download_url": dl_link,
                    "format": fmt,
                }
    except Exception:
        pass
    return None


def find_and_download(book_title: str) -> dict:
    """
    Main entry point. Searches for the book across multiple sources and
    downloads it. Returns a dict with:
      - title, author, source, file_path (Path to downloaded file)
      - or error key if nothing found
    """
    safe_name = _sanitize(book_title)
    dest_dir = STAGING_DIR / safe_name
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Strategy 1: Open Library
    match = _search_open_library(book_title)
    if match:
        path = _download_from_open_library(match["edition_key"], dest_dir)
        if path:
            return {**match, "file_path": path}

    # Strategy 2: Project Gutenberg
    match = _search_gutenberg(book_title)
    if match:
        path = _download_url(match["download_url"], dest_dir, match["format"])
        if path:
            return {**match, "file_path": path}

    # Strategy 3: Google Books
    match = _search_google_books(book_title)
    if match:
        path = _download_url(match["download_url"], dest_dir, match["format"])
        if path:
            return {**match, "file_path": path}

    # Nothing found — create placeholder
    placeholder = dest_dir / "BOOK_NOT_FOUND.txt"
    placeholder.write_text(
        f"Could not find a free digital copy of: {book_title}\n"
        f"You may need to purchase this book or check your local library.\n"
    )
    return {
        "title": book_title,
        "author": "Unknown",
        "source": "none",
        "file_path": placeholder,
        "error": "No free digital copy found",
    }


if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv
    load_dotenv()
    title = " ".join(sys.argv[1:]) or "The Great Gatsby"
    result = find_and_download(title)
    print(f"\nResult: {result}")
