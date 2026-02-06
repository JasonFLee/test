"""
Book Pipeline Orchestrator
==========================
Main entry point that:
  1. Checks Google Tasks for new "to read" books
  2. For each new book:
     a. Finds and downloads the book (PDF/EPUB)
     b. Generates a podcast summary (script + audio)
     c. Generates an audiobook via Kokoro TTS (with resume support)
     d. Uploads everything to a Google Drive folder per book
  3. Marks tasks as processed so they aren't re-processed

Designed to run on login / periodically. Handles interruptions
gracefully — the Kokoro agent tracks per-chunk progress, and
the orchestrator tracks per-book progress.
"""

import os
import sys
import json
import shutil
import traceback
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load env before importing agents
load_dotenv(Path(__file__).resolve().parent / ".env")

from agents.google_tasks_agent import fetch_new_books, mark_processed
from agents.find_book_agent import find_and_download
from agents.summary_agent import generate_podcast
from agents.kokoro_audiobook_agent import generate_audiobook
from agents.google_drive_agent import upload_book_folder

STAGING_DIR = Path(os.getenv("LOCAL_STAGING_DIR", "./staging"))
STATE_DIR = Path(__file__).resolve().parent / "state"
PIPELINE_STATE = STATE_DIR / "pipeline_state.json"
LOG_DIR = Path(__file__).resolve().parent / "logs"


def _load_pipeline_state() -> dict:
    if PIPELINE_STATE.exists():
        return json.loads(PIPELINE_STATE.read_text())
    return {"books": {}}


def _save_pipeline_state(state: dict):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    PIPELINE_STATE.write_text(json.dumps(state, indent=2))


def _log(msg: str):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    log_file = LOG_DIR / f"run_{datetime.now().strftime('%Y%m%d')}.log"
    with open(log_file, "a") as f:
        f.write(line + "\n")


def process_book(task_id: str, title: str, notes: str, pipeline_state: dict) -> bool:
    """
    Process a single book through the full pipeline.
    Returns True if fully completed, False if interrupted/failed.
    """
    book_state = pipeline_state["books"].get(task_id, {
        "title": title,
        "stage": "find_book",
        "started_at": datetime.now().isoformat(),
    })
    pipeline_state["books"][task_id] = book_state

    safe_title = title.replace("/", "-").replace("\\", "-")
    book_dir = STAGING_DIR / safe_title

    # Stage 1: Find and download book
    if book_state["stage"] == "find_book":
        _log(f"[{title}] Stage 1: Finding and downloading book...")
        try:
            result = find_and_download(title)
            book_state["book_path"] = str(result["file_path"])
            book_state["book_source"] = result.get("source", "unknown")
            book_state["book_author"] = result.get("author", "Unknown")
            book_state["stage"] = "summary"
            _save_pipeline_state(pipeline_state)
            _log(f"[{title}] Book found: {result.get('source')} -> {result['file_path']}")
        except Exception as e:
            _log(f"[{title}] ERROR in find_book: {e}")
            traceback.print_exc()
            return False

    # Stage 2: Generate podcast summary
    if book_state["stage"] == "summary":
        _log(f"[{title}] Stage 2: Generating podcast summary...")
        try:
            book_path = Path(book_state["book_path"])
            summary_dir = book_dir / "summary"
            result = generate_podcast(title, book_path, summary_dir)
            book_state["podcast_script_path"] = str(result["script_path"])
            book_state["podcast_audio_path"] = str(result["audio_path"])
            book_state["stage"] = "audiobook"
            _save_pipeline_state(pipeline_state)
            _log(f"[{title}] Podcast summary generated ({result['word_count']} words)")
        except Exception as e:
            _log(f"[{title}] ERROR in summary: {e}")
            traceback.print_exc()
            return False

    # Stage 3: Generate audiobook (resumable)
    if book_state["stage"] == "audiobook":
        _log(f"[{title}] Stage 3: Generating audiobook (Kokoro TTS)...")
        try:
            book_path = Path(book_state["book_path"])
            audiobook_dir = book_dir / "audiobook"
            result = generate_audiobook(title, book_path, audiobook_dir)

            if result["audiobook_path"] and result["completed_chunks"] == result["total_chunks"]:
                book_state["audiobook_path"] = str(result["audiobook_path"])
                book_state["stage"] = "upload"
                _save_pipeline_state(pipeline_state)
                _log(f"[{title}] Audiobook complete: {result['completed_chunks']}/{result['total_chunks']} chunks")
            else:
                _log(f"[{title}] Audiobook incomplete: {result['completed_chunks']}/{result['total_chunks']} chunks. Will resume next run.")
                _save_pipeline_state(pipeline_state)
                return False
        except Exception as e:
            _log(f"[{title}] ERROR in audiobook: {e}")
            traceback.print_exc()
            return False

    # Stage 4: Upload to Google Drive
    if book_state["stage"] == "upload":
        _log(f"[{title}] Stage 4: Uploading to Google Drive...")
        try:
            result = upload_book_folder(
                book_title=title,
                book_path=Path(book_state.get("book_path", "")) if book_state.get("book_path") else None,
                podcast_audio_path=Path(book_state.get("podcast_audio_path", "")) if book_state.get("podcast_audio_path") else None,
                podcast_script_path=Path(book_state.get("podcast_script_path", "")) if book_state.get("podcast_script_path") else None,
                audiobook_path=Path(book_state.get("audiobook_path", "")) if book_state.get("audiobook_path") else None,
            )
            book_state["drive_folder_id"] = result["folder_id"]
            book_state["stage"] = "done"
            book_state["completed_at"] = datetime.now().isoformat()
            _save_pipeline_state(pipeline_state)
            _log(f"[{title}] Uploaded to Drive folder: {result['folder_id']}")
        except Exception as e:
            _log(f"[{title}] ERROR in upload: {e}")
            traceback.print_exc()
            return False

    return True


def run():
    """Main pipeline entry point."""
    _log("=" * 60)
    _log("Book Pipeline starting...")
    _log("=" * 60)

    # Load state
    pipeline_state = _load_pipeline_state()

    # First: resume any incomplete books from previous runs
    incomplete = {
        tid: info for tid, info in pipeline_state["books"].items()
        if info.get("stage") != "done"
    }
    if incomplete:
        _log(f"Found {len(incomplete)} incomplete book(s) from previous runs. Resuming...")
        for task_id, info in incomplete.items():
            title = info["title"]
            _log(f"Resuming: {title} (stage: {info['stage']})")
            success = process_book(task_id, title, "", pipeline_state)
            if success:
                mark_processed(task_id)
                _log(f"COMPLETED: {title}")

    # Then: check for new books
    _log("Checking Google Tasks for new books...")
    new_books = fetch_new_books()

    if not new_books:
        _log("No new books to process.")
        _log("Pipeline complete.")
        return

    for book in new_books:
        _log(f"\nProcessing: {book['title']}")
        success = process_book(
            book["task_id"],
            book["title"],
            book.get("notes", ""),
            pipeline_state,
        )
        if success:
            mark_processed(book["task_id"])
            _log(f"COMPLETED: {book['title']}")
        else:
            _log(f"INCOMPLETE: {book['title']} — will resume next run.")

    _log("\nPipeline run finished.")
    _log("=" * 60)


if __name__ == "__main__":
    run()
