"""Shared input loading and preprocessing for workspace services."""

from __future__ import annotations

from pathlib import Path
import numpy as np

import spectrasync as ss
from .. import config
from ..media import MediaStore


def get_base_image(base_id: str | None, media: MediaStore, max_side: int | None = None,
                   fallback: str = "media/01_translation/base.jpg", colour: bool = False) -> np.ndarray:
    """Retrieve base image array from media ID, or fall back to a sample file.

    `fallback` is a path relative to the repo root and is workspace-specific --
    each service passes its OWN `media/<workspace>/base.jpg`, so changing one
    tool's default sample never affects another's. See `media/README.md`.
    """
    load = ss.load_rgb if colour else ss.load_gray
    if base_id:
        m = media.get(base_id)
        if m and m.path.exists():
            return load(m.path, max_side=max_side)

    path = Path(fallback)
    full = path if path.is_absolute() else config.ROOT / path
    if full.exists():
        return load(full, max_side=max_side)

    raise ValueError(f"Base image not found. Please provide an image or place one at {fallback}.")


def load_pair(
    a_id: str | None,
    b_id: str | None,
    media: MediaStore,
    max_side: int | None = 768,
    gray: bool = True,
    sample_glob: str | None = None,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Load reference and moved images and match their shapes."""
    paths: list[str] = []
    names: list[str] = []

    for item_id in (a_id, b_id):
        if item_id:
            m = media.get(item_id)
            if m and m.path.exists():
                paths.append(str(m.path))
                names.append(m.name)

    if len(paths) < 2 and sample_glob:
        import glob
        full_pattern = str(config.ROOT / sample_glob) if not Path(sample_glob).is_absolute() else sample_glob
        matches = sorted(glob.glob(full_pattern))
        while len(paths) < 2 and len(matches) > len(paths):
            idx = len(paths)
            paths.append(matches[idx])
            names.append(Path(matches[idx]).name)

    if len(paths) < 2:
        raise ValueError("need_two_images")

    loaded = ss.load_many(paths, max_side=max_side, gray=gray)
    ref, mov = ss.match_shapes(loaded[0], loaded[1])
    return ref, mov, names


def frame_pair_from_video(
    media_id: str | None,
    a_index: int,
    b_index: int,
    media: MediaStore,
    max_side: int | None = 768,
    gray: bool = True,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Extract two frames from a video asset as a pair."""
    if not media_id:
        raise ValueError("need_two_images")
    
    m = media.get(media_id)
    if not m or not m.path.exists():
        raise ValueError("bad_media")

    needed = max(a_index, b_index) + 1
    frames = media.load_video(media_id, max_frames=needed, step=1, max_side=max_side, gray=gray)
    if len(frames) <= max(a_index, b_index):
        raise ValueError("need_two_frames")

    ref, mov = ss.match_shapes(frames[a_index], frames[b_index])
    names = [f"{m.name} [frame {a_index}]", f"{m.name} [frame {b_index}]"]
    return ref, mov, names


def load_sequence(
    media_ids: list[str],
    media: MediaStore,
    max_side: int | None = 640,
    gray: bool = False,
    sample_glob: str | None = None,
    min_count: int = 2,
) -> tuple[list[np.ndarray], list[str]]:
    """Load a sequence of photo frames."""
    paths: list[str] = []
    names: list[str] = []

    for item_id in media_ids:
        m = media.get(item_id)
        if m and m.path.exists():
            paths.append(str(m.path))
            names.append(m.name)

    if len(paths) < min_count and sample_glob:
        import glob
        full_pattern = str(config.ROOT / sample_glob) if not Path(sample_glob).is_absolute() else sample_glob
        matches = sorted(glob.glob(full_pattern))
        if matches:
            paths = matches
            names = [Path(p).name for p in paths]

    if len(paths) < min_count:
        if min_count == 2:
            raise ValueError("need_two_frames")
        raise ValueError("need_three_frames")

    frames = ss.load_many(paths, max_side=max_side, gray=gray)
    return frames, names
