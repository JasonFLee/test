"""
Google Drive Agent
------------------
Uploads organized book folders to Google Drive.
Each book gets its own folder containing:
  - The book file (PDF/EPUB)
  - Podcast summary audio (MP3)
  - Podcast summary script (TXT)
  - Audiobook (WAV)
"""

import os
import mimetypes
from pathlib import Path
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from utils.google_auth_helper import get_credentials

MIME_FOLDER = "application/vnd.google-apps.folder"


def _get_drive_service():
    creds = get_credentials()
    return build("drive", "v3", credentials=creds)


def _find_or_create_folder(service, name: str, parent_id: str = None) -> str:
    """Find an existing folder or create a new one. Returns folder ID."""
    query = f"name = '{name}' and mimeType = '{MIME_FOLDER}' and trashed = false"
    if parent_id:
        query += f" and '{parent_id}' in parents"

    results = service.files().list(q=query, spaces="drive", fields="files(id, name)").execute()
    files = results.get("files", [])

    if files:
        print(f"[Drive] Found existing folder: {name}")
        return files[0]["id"]

    # Create folder
    metadata = {"name": name, "mimeType": MIME_FOLDER}
    if parent_id:
        metadata["parents"] = [parent_id]

    folder = service.files().create(body=metadata, fields="id").execute()
    print(f"[Drive] Created folder: {name}")
    return folder["id"]


def _upload_file(service, local_path: Path, parent_id: str, filename: str = None) -> str:
    """Upload a file to a Drive folder. Returns file ID."""
    if not local_path.exists():
        print(f"[Drive] Skipping {local_path} — does not exist")
        return None

    name = filename or local_path.name
    mime_type, _ = mimetypes.guess_type(str(local_path))
    mime_type = mime_type or "application/octet-stream"

    # Check if file already exists in folder
    query = f"name = '{name}' and '{parent_id}' in parents and trashed = false"
    existing = service.files().list(q=query, spaces="drive", fields="files(id)").execute()
    if existing.get("files"):
        print(f"[Drive] File already exists, updating: {name}")
        file_id = existing["files"][0]["id"]
        media = MediaFileUpload(str(local_path), mimetype=mime_type, resumable=True)
        service.files().update(fileId=file_id, media_body=media).execute()
        return file_id

    metadata = {"name": name, "parents": [parent_id]}
    media = MediaFileUpload(str(local_path), mimetype=mime_type, resumable=True)

    file = service.files().create(
        body=metadata,
        media_body=media,
        fields="id",
    ).execute()

    print(f"[Drive] Uploaded: {name} ({mime_type})")
    return file["id"]


def upload_book_folder(
    book_title: str,
    book_path: Path = None,
    podcast_audio_path: Path = None,
    podcast_script_path: Path = None,
    audiobook_path: Path = None,
    root_folder_id: str = None,
) -> dict:
    """
    Create a folder for the book in Google Drive and upload all artifacts.

    Returns dict with folder_id and file_ids.
    """
    root_id = root_folder_id or os.getenv("GOOGLE_DRIVE_ROOT_FOLDER_ID")
    if not root_id:
        raise RuntimeError(
            "GOOGLE_DRIVE_ROOT_FOLDER_ID must be set in .env. "
            "Create a folder in Google Drive and use its ID."
        )

    service = _get_drive_service()

    # Create book folder
    folder_id = _find_or_create_folder(service, book_title, parent_id=root_id)

    uploaded = {"folder_id": folder_id}

    # Upload each artifact
    if book_path:
        uploaded["book_file_id"] = _upload_file(
            service, book_path, folder_id,
            f"{book_title}{book_path.suffix}"
        )

    if podcast_audio_path:
        uploaded["podcast_audio_id"] = _upload_file(
            service, podcast_audio_path, folder_id,
            f"{book_title} - Podcast Summary.mp3"
        )

    if podcast_script_path:
        uploaded["podcast_script_id"] = _upload_file(
            service, podcast_script_path, folder_id,
            f"{book_title} - Summary Script.txt"
        )

    if audiobook_path:
        uploaded["audiobook_id"] = _upload_file(
            service, audiobook_path, folder_id,
            f"{book_title} - Audiobook.wav"
        )

    print(f"[Drive] All files for '{book_title}' uploaded to folder: {folder_id}")
    return uploaded


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    print("[Drive] Testing Google Drive connection...")
    service = _get_drive_service()
    about = service.about().get(fields="user").execute()
    print(f"[Drive] Connected as: {about['user']['emailAddress']}")
