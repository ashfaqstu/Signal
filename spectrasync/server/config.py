"""Configuration and paths for SpectraSync Studio server."""

from __future__ import annotations

import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

UPLOAD_DIR = Path(tempfile.gettempdir()) / "spectrasync_studio" / "uploads"

#: One row per default sample, sourced from media/<workspace>/ -- see
#: media/README.md. Editing a file in that tree changes what shows up here.
SAMPLES: list[tuple[str, str, str]] = [
    ("Base · translation", "media/01_translation/base.jpg", "image"),
    ("Pair · translation", "media/01_translation/pair/*.jpg", "image"),
    ("Base · rotation & scale", "media/02_rotation_scale/base.jpg", "image"),
    ("Pair · rotated", "media/02_rotation_scale/pair/*.jpg", "image"),
    ("Base · stacking", "media/03_stacking/base.jpg", "image"),
    ("Burst · noisy", "media/03_stacking/burst/*.jpg", "image"),
    ("Burst · clean ref", "media/03_stacking/clean_reference.png", "image"),
    ("Base · object removal", "media/04_object_removal/base.jpg", "image"),
    ("Crowd · object removal", "media/04_object_removal/burst/*.jpg", "image"),
    ("Base · highlight", "media/05_highlight/base.jpg", "image"),
    ("Crowd · highlight", "media/05_highlight/burst/*.jpg", "image"),
    ("Base · theory", "media/06_theory/base.jpg", "image"),
]

MAX_UPLOAD_MB = 200
MAX_RUNS_KEPT = 8

IMAGE_TYPES = ["png", "jpg", "jpeg", "bmp", "tif", "tiff", "webp"]
VIDEO_TYPES = ["mp4", "avi", "mov", "mkv", "webm"]

HOST = "127.0.0.1"
PORT = 8000
