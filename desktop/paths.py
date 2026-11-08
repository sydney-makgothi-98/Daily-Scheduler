"""Filesystem locations that work both from source and from a PyInstaller bundle."""

import os
import sys
from pathlib import Path

FROZEN = getattr(sys, "frozen", False)
APP_NAME = "DailySchedule"
# Bundled read-only resources live next to the exe (onedir) / in _MEIPASS; source runs use the repo root.
RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
DATA_DIR = Path(os.environ.get("APPDATA", Path.home())) / APP_NAME
DATA_DIR.mkdir(parents=True, exist_ok=True)
