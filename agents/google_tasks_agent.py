"""
Google Tasks Agent
------------------
Connects to Google Tasks API and fetches unchecked tasks from a
"To Read" list that were created on or after Feb 6 2026.
"""

import os
import json
from datetime import datetime, timezone
from pathlib import Path
from googleapiclient.discovery import build
from utils.google_auth_helper import get_credentials

STATE_DIR = Path(__file__).resolve().parent.parent / "state"
STATE_FILE = STATE_DIR / "processed_tasks.json"
CUTOFF_DATE = datetime(2026, 2, 6, tzinfo=timezone.utc)


def _load_processed() -> set:
    if STATE_FILE.exists():
        return set(json.loads(STATE_FILE.read_text()))
    return set()


def _save_processed(ids: set):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(sorted(ids), indent=2))


def _find_reading_list(service):
    """Find a task list whose title contains 'read' (case-insensitive)."""
    results = service.tasklists().list(maxResults=100).execute()
    for tl in results.get("items", []):
        if "read" in tl["title"].lower():
            return tl["id"], tl["title"]
    return None, None


def fetch_new_books() -> list[dict]:
    """
    Return a list of dicts: [{"task_id": ..., "title": ..., "notes": ...}, ...]
    for every uncompleted task in the reading list added since the cutoff date
    that hasn't already been processed.
    """
    creds = get_credentials()
    service = build("tasks", "v1", credentials=creds)

    list_id, list_title = _find_reading_list(service)
    if not list_id:
        print("[Tasks] No task list containing 'read' found. Available lists:")
        results = service.tasklists().list(maxResults=100).execute()
        for tl in results.get("items", []):
            print(f"  - {tl['title']}")
        return []

    print(f"[Tasks] Using list: {list_title}")

    processed = _load_processed()
    new_books = []

    page_token = None
    while True:
        resp = service.tasks().list(
            tasklist=list_id,
            showCompleted=False,
            showHidden=False,
            maxResults=100,
            pageToken=page_token,
        ).execute()

        for task in resp.get("items", []):
            task_id = task["id"]
            if task_id in processed:
                continue

            # Check date — 'updated' is the best proxy for creation date
            updated = task.get("updated", "")
            if updated:
                task_date = datetime.fromisoformat(updated.replace("Z", "+00:00"))
                if task_date < CUTOFF_DATE:
                    continue

            title = task.get("title", "").strip()
            if not title:
                continue

            new_books.append({
                "task_id": task_id,
                "title": title,
                "notes": task.get("notes", ""),
            })

        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    print(f"[Tasks] Found {len(new_books)} new book(s) to process.")
    return new_books


def mark_processed(task_id: str):
    """Record that a task has been fully processed."""
    processed = _load_processed()
    processed.add(task_id)
    _save_processed(processed)


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    books = fetch_new_books()
    for b in books:
        print(f"  [{b['task_id'][:8]}] {b['title']}")
