#!/usr/bin/env bash
set -e

# Docker entrypoint: patch config.json with Docker-specific defaults
# before starting the app. This avoids changing config.example.json
# which would break the local setup script's auto-detection logic.

CONFIG="/app/config.json"

# Create config.json from example if it doesn't exist
if [ ! -f "$CONFIG" ]; then
  cp /app/config.example.json "$CONFIG"
fi

# Set Docker-specific defaults using Python (only if values are empty)
python3 - <<'PY'
import json, os

config_path = "/app/config.json"
with open(config_path, "r") as f:
    cfg = json.load(f)

changed = False

# Set firefox_profile if empty
if not cfg.get("firefox_profile"):
    cfg["firefox_profile"] = "/data/firefox-profile"
    changed = True

# Enable headless mode for Docker (no display available)
if not cfg.get("headless"):
    cfg["headless"] = True
    changed = True

# Set imagemagick path if it looks like a placeholder
im_path = cfg.get("imagemagick_path", "")
if not im_path or "magick.exe" in im_path:
    cfg["imagemagick_path"] = "/usr/bin/convert"
    changed = True

if changed:
    with open(config_path, "w") as f:
        json.dump(cfg, f, indent=2)
        f.write("\n")
    print("[docker-entrypoint] Patched config.json with Docker defaults")

PY

exec python3 src/main.py "$@"
