"""
NotingHill — config.py
"""
import os
from pathlib import Path

APP_NAME = "NotingHill"
APP_VERSION = "1.0.0"
PORT = int(os.environ.get("NH_PORT", 7878))
HOST = os.environ.get("NH_HOST", "127.0.0.1")
WORKERS = int(os.environ.get("NH_WORKERS", 4))

# Data directory
if os.name == "nt":  # Windows
    DATA_DIR = Path(os.environ.get("APPDATA", Path.home())) / "NotingHill"
else:
    DATA_DIR = Path.home() / ".notinghill"

DB_PATH = DATA_DIR / "app.db"
THUMBNAILS_DIR = DATA_DIR / "thumbnails"
CACHE_DIR = DATA_DIR / "cache"
LOG_DIR = DATA_DIR / "logs"

# Frontend static (built React)
STATIC_DIR = Path(__file__).parent / "static"
