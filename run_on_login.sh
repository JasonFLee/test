#!/usr/bin/env bash
#
# run_on_login.sh — Triggered on login to process new books from Google Tasks.
# Set this up as a login item (macOS) or autostart entry (Linux).
#

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Activate virtualenv if it exists
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

# Run the pipeline
python orchestrator.py >> logs/cron.log 2>&1
