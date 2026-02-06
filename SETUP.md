# Google Tasks Book Pipeline — Setup Guide

Automatically processes your "To Read" Google Tasks into organized Google Drive
folders containing: the book file, a podcast-style summary, and a full audiobook.

## Prerequisites

- Python 3.10+
- A Google Cloud project with **Tasks API** and **Drive API** enabled
- OAuth2 Desktop credentials from Google Cloud Console
- OpenAI API key (for summaries + fallback TTS)
- (Optional) Kokoro TTS installed locally for high-quality audiobooks

## Quick Start

```bash
# 1. Clone and enter the project
cd /path/to/this/project

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy and fill in your config
cp .env.example .env
# Edit .env with your credentials (see below)

# 5. First run (will prompt for Google OAuth login in browser)
python orchestrator.py

# 6. Install login trigger (runs automatically when you log in)
./setup_login_trigger.sh
```

## Configuration (.env)

### Google OAuth2 (Required)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project (or use an existing one)
3. Enable **Google Tasks API** and **Google Drive API**
4. Create **OAuth2 Desktop** credentials
5. Copy the Client ID and Client Secret into `.env`

```
GOOGLE_CLIENT_ID=your_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_client_secret
```

### Google Drive Folder (Required)

1. Create a folder in Google Drive (e.g., "Book Pipeline")
2. Open it and copy the folder ID from the URL:
   `https://drive.google.com/drive/folders/THIS_IS_THE_ID`
3. Set it in `.env`:

```
GOOGLE_DRIVE_ROOT_FOLDER_ID=your_folder_id
```

### OpenAI API Key (Required)

Used for generating podcast summaries and fallback TTS.

```
OPENAI_API_KEY=sk-...
```

### Kokoro TTS (Optional)

For high-quality local audiobook generation. If not installed, falls back to
OpenAI TTS.

```
pip install kokoro soundfile
```

## How It Works

### Pipeline Stages (per book)

1. **Google Tasks Agent** — Scans your "To Read" task list for unchecked items
   added since Feb 6, 2026
2. **Find Book Agent** — Searches Open Library, Project Gutenberg, and Google
   Books for a free digital copy (PDF/EPUB)
3. **Summary Agent** — Extracts text, generates a podcast-style summary with
   GPT-4o, converts to audio with OpenAI TTS
4. **Kokoro Audiobook Agent** — Converts the full book to audio using Kokoro
   TTS. Tracks per-chunk progress so it can **resume** if interrupted
5. **Google Drive Agent** — Creates a folder per book and uploads everything

### Google Drive Structure

```
Book Pipeline/
├── Atomic Habits/
│   ├── Atomic Habits.epub
│   ├── Atomic Habits - Podcast Summary.mp3
│   ├── Atomic Habits - Summary Script.txt
│   └── Atomic Habits - Audiobook.wav
├── Deep Work/
│   ├── Deep Work.pdf
│   ├── Deep Work - Podcast Summary.mp3
│   ├── Deep Work - Summary Script.txt
│   └── Deep Work - Audiobook.wav
└── ...
```

### Resume Support

The audiobook generation can take a long time for full books. If interrupted:
- Each chunk's progress is saved in `.audiobook_progress.json`
- Next run automatically resumes from the last completed chunk
- The orchestrator also tracks per-book stage progress in `state/pipeline_state.json`

## Manual Commands

```bash
# Run the full pipeline manually
python orchestrator.py

# Test individual agents
python -m agents.google_tasks_agent     # List new tasks
python -m agents.find_book_agent "Dune" # Find a book
python -m agents.summary_agent "Dune" book.pdf ./out  # Generate summary
python -m agents.kokoro_audiobook_agent "Dune" book.pdf ./out  # Generate audiobook
python -m agents.google_drive_agent     # Test Drive connection
```

## Troubleshooting

- **"No task list containing 'read' found"** — Make sure you have a Google
  Tasks list with "read" in the name (e.g., "To Read", "Reading List")
- **OAuth errors** — Delete `state/token.json` and re-run to re-authenticate
- **Audiobook stuck** — Check `staging/<book>/audiobook/.audiobook_progress.json`
  for chunk status. Delete it to restart from scratch.
- **Drive upload fails** — Verify `GOOGLE_DRIVE_ROOT_FOLDER_ID` is correct and
  the OAuth token has Drive scope
