"""Media storage and caching for sample assets and uploaded files."""

from __future__ import annotations

import functools
import glob
import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np
from fastapi import UploadFile
from PIL import Image

import spectrasync as ss
from . import config


@dataclass
class Media:
    id: str
    name: str
    kind: Literal["image", "video"]
    path: Path
    group: str
    sample: bool
    width: int
    height: int
    n_frames: int | None = None


class MediaStore:
    def __init__(self):
        self._items: dict[str, Media] = {}
        self._sample_groups: dict[str, list[str]] = {}

    def init(self) -> None:
        """Create upload directory and register all sample assets."""
        config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        self.register_samples()

    def register_samples(self) -> None:
        """Glob sample files defined in config and register with stable IDs."""
        self._items.clear()
        self._sample_groups.clear()

        for group_label, pattern, kind in config.SAMPLES:
            full_pattern = str(config.ROOT / pattern)
            paths = sorted(glob.glob(full_pattern))
            group_ids: list[str] = []

            for p_str in paths:
                p = Path(p_str)
                # Create a deterministic stable ID for sample files based on relative path
                rel_path = p.relative_to(config.ROOT).as_posix()
                item_id = "sample_" + rel_path.replace("/", "_").replace(".", "_")

                width, height, n_frames = 0, 0, None
                if kind == "image":
                    try:
                        with Image.open(p) as img:
                            width, height = img.size
                    except Exception:
                        width, height = 512, 512
                elif kind == "video":
                    try:
                        frames = ss.read_video(p, max_frames=1)
                        if frames:
                            height, width = frames[0].shape[:2]
                    except Exception:
                        width, height = 512, 512

                media = Media(
                    id=item_id,
                    name=p.name,
                    kind=kind,  # type: ignore
                    path=p,
                    group=group_label,
                    sample=True,
                    width=width,
                    height=height,
                    n_frames=n_frames,
                )
                self._items[item_id] = media
                group_ids.append(item_id)

            self._sample_groups[group_label] = group_ids

    async def import_upload(self, file: UploadFile) -> Media:
        """Save uploaded file to UPLOAD_DIR and read its dimensions."""
        filename = file.filename or "upload"
        ext = Path(filename).suffix.lower()
        clean_ext = ext.lstrip(".")

        if clean_ext in config.IMAGE_TYPES:
            kind: Literal["image", "video"] = "image"
        elif clean_ext in config.VIDEO_TYPES:
            kind = "video"
        else:
            kind = "image"

        item_id = "upload_" + uuid.uuid4().hex[:12]
        dest_path = config.UPLOAD_DIR / f"{item_id}{ext}"

        contents = await file.read()
        with open(dest_path, "wb") as f:
            f.write(contents)

        width, height, n_frames = 0, 0, None
        if kind == "image":
            try:
                with Image.open(dest_path) as img:
                    width, height = img.size
            except Exception:
                width, height = 512, 512
        else:
            try:
                frames = ss.read_video(dest_path, max_frames=1)
                if frames:
                    height, width = frames[0].shape[:2]
            except Exception:
                width, height = 512, 512

        media = Media(
            id=item_id,
            name=filename,
            kind=kind,
            path=dest_path,
            group="Uploads",
            sample=False,
            width=width,
            height=height,
            n_frames=n_frames,
        )
        self._items[item_id] = media
        return media

    def get(self, item_id: str) -> Media | None:
        return self._items.get(item_id)

    def delete(self, item_id: str) -> bool:
        media = self._items.get(item_id)
        if not media or media.sample:
            return False
        if media.path.exists():
            try:
                media.path.unlink()
            except OSError:
                pass
        del self._items[item_id]
        return True

    def list_all(self) -> list[Media]:
        return list(self._items.values())

    def get_sample_ids(self, group_label: str) -> list[str]:
        return self._sample_groups.get(group_label, [])

    def load(self, ids: tuple[str, ...], max_side: int | None = None, gray: bool = True) -> list[np.ndarray]:
        """Load multiple media items at one size with LRU caching."""
        return self._cached_load(tuple(ids), max_side, gray)

    @functools.lru_cache(maxsize=16)
    def _cached_load(self, ids: tuple[str, ...], max_side: int | None, gray: bool) -> list[np.ndarray]:
        paths = []
        for item_id in ids:
            media = self.get(item_id)
            if not media:
                raise ValueError(f"Media not found: {item_id}")
            paths.append(str(media.path))
        return ss.load_many(paths, max_side=max_side, gray=gray)

    def load_video(self, item_id: str, max_frames: int | None = None, step: int = 1,
                   max_side: int | None = None, gray: bool = True) -> list[np.ndarray]:
        return self._cached_load_video(item_id, max_frames, step, max_side, gray)

    @functools.lru_cache(maxsize=8)
    def _cached_load_video(self, item_id: str, max_frames: int | None, step: int,
                           max_side: int | None, gray: bool) -> list[np.ndarray]:
        media = self.get(item_id)
        if not media:
            raise ValueError(f"Media not found: {item_id}")
        return ss.read_video(media.path, max_frames=max_frames, step=step, max_side=max_side, gray=gray)


media_store = MediaStore()
