"""Configuration and paths for SpectraSync Studio server."""

from __future__ import annotations

import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

UPLOAD_DIR = Path(tempfile.gettempdir()) / "spectrasync_studio" / "uploads"

SAMPLES: list[tuple[str, str, str]] = [
    ("Base", "data/raw/photo_b.jpg", "image"),
    ("Pair · rotated", "new_image/3/*.jpg", "image"),
    ("Burst · noisy", "new_image/2_noisy/set_1/*.jpg", "image"),
    ("Burst · clean ref", "new_image/2_noisy/_clean/set_1.png", "image"),
    ("Crowd", "new_image/1/*.jpg", "image"),
]

MAX_UPLOAD_MB = 200
MAX_RUNS_KEPT = 8

IMAGE_TYPES = ["png", "jpg", "jpeg", "bmp", "tif", "tiff", "webp"]
VIDEO_TYPES = ["mp4", "avi", "mov", "mkv", "webm"]

HOST = "127.0.0.1"
PORT = 8000
