#!/usr/bin/env bash
#
# setup_login_trigger.sh — Installs the book pipeline to run on login.
# Supports macOS (launchd) and Linux (systemd user service + autostart).
#

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_PATH="$(which python3)"
VENV_PYTHON="$SCRIPT_DIR/venv/bin/python"

if [ -f "$VENV_PYTHON" ]; then
    PYTHON_PATH="$VENV_PYTHON"
fi

echo "=== Book Pipeline Login Trigger Setup ==="
echo "Project dir: $SCRIPT_DIR"
echo "Python:      $PYTHON_PATH"
echo ""

# --- macOS: LaunchAgent ---
if [[ "$(uname)" == "Darwin" ]]; then
    PLIST_DIR="$HOME/Library/LaunchAgents"
    PLIST="$PLIST_DIR/com.bookpipeline.login.plist"

    mkdir -p "$PLIST_DIR"
    cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.bookpipeline.login</string>

    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON_PATH</string>
        <string>$SCRIPT_DIR/orchestrator.py</string>
    </array>

    <key>WorkingDirectory</key>
    <string>$SCRIPT_DIR</string>

    <key>RunAtLoad</key>
    <true/>

    <key>StandardOutPath</key>
    <string>$SCRIPT_DIR/logs/launchd_stdout.log</string>

    <key>StandardErrorPath</key>
    <string>$SCRIPT_DIR/logs/launchd_stderr.log</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin</string>
    </dict>
</dict>
</plist>
EOF

    # Load the agent
    launchctl unload "$PLIST" 2>/dev/null || true
    launchctl load "$PLIST"
    echo "[macOS] LaunchAgent installed: $PLIST"
    echo "[macOS] Pipeline will run each time you log in."
    echo "[macOS] To test now:  launchctl start com.bookpipeline.login"
    echo "[macOS] To remove:    launchctl unload $PLIST && rm $PLIST"

# --- Linux: systemd user service ---
elif [[ "$(uname)" == "Linux" ]]; then
    SERVICE_DIR="$HOME/.config/systemd/user"
    SERVICE="$SERVICE_DIR/book-pipeline.service"

    mkdir -p "$SERVICE_DIR"
    cat > "$SERVICE" <<EOF
[Unit]
Description=Book Pipeline — process new reading list items
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
WorkingDirectory=$SCRIPT_DIR
ExecStart=$PYTHON_PATH $SCRIPT_DIR/orchestrator.py
StandardOutput=append:$SCRIPT_DIR/logs/systemd_stdout.log
StandardError=append:$SCRIPT_DIR/logs/systemd_stderr.log
Environment=PATH=/usr/local/bin:/usr/bin:/bin

[Install]
WantedBy=default.target
EOF

    systemctl --user daemon-reload
    systemctl --user enable book-pipeline.service
    echo "[Linux] systemd user service installed: $SERVICE"
    echo "[Linux] Pipeline will run each time you log in."
    echo "[Linux] To test now:  systemctl --user start book-pipeline.service"
    echo "[Linux] To check:     systemctl --user status book-pipeline.service"
    echo "[Linux] To disable:   systemctl --user disable book-pipeline.service"
fi

mkdir -p "$SCRIPT_DIR/logs"
echo ""
echo "Setup complete!"
