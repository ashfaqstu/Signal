"""Frame sources -- one interface, several origins.

The UI and the applied features never care whether frames came from a folder of
photographs, a video file, or a synthetic generator. They ask a FrameSource for
frames. Adding a new origin means adding one class with two methods.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import numpy as np


@runtime_checkable
class FrameSource(Protocol):
    """Anything that can hand over a list of float64 frames."""

    name: str

    def frames(self):
        """-> list[np.ndarray], each (H, W) or (H, W, 3) float64 in [0, 1]."""
        ...


class ImageFolderSource:
    """Every image matching a glob pattern, sorted by filename."""

    def __init__(self, pattern, gray=True, max_side=None, limit=None):
        self.pattern, self.gray = pattern, gray
        self.max_side, self.limit = max_side, limit
        self.name = f"folder:{pattern}"
        self.paths = []

    def frames(self):
        from .images import load_folder
        out, self.paths = load_folder(self.pattern, max_side=self.max_side,
                                      gray=self.gray, limit=self.limit)
        return out


class VideoFileSource:
    """Frames decoded from a video file."""

    def __init__(self, path, max_frames=None, step=1, gray=True, max_side=None):
        self.path, self.max_frames, self.step = path, max_frames, step
        self.gray, self.max_side = gray, max_side
        self.name = f"video:{path}"

    def frames(self):
        from .video import read_video
        return read_video(self.path, max_frames=self.max_frames, step=self.step,
                          gray=self.gray, max_side=self.max_side)


class ArraySource:
    """Frames you already have in memory."""

    def __init__(self, arrays, name="arrays"):
        self._arrays = [np.asarray(a, dtype=np.float64) for a in arrays]
        self.name = name

    def frames(self):
        return list(self._arrays)


class SyntheticSource:
    """A generated sequence with KNOWN ground truth.

    Every demo and every test can run with no files on disk, and the true
    answer is stored in `.truth` so accuracy is always measurable.
    """

    def __init__(self, base, n=8, max_shift=6.0, noise=0.05, angle=0.0,
                 scale=1.0, mover=None, seed=0, name="synthetic"):
        self.base = np.asarray(base, dtype=np.float64)
        self.n, self.max_shift, self.noise = n, max_shift, noise
        self.angle, self.scale, self.mover = angle, scale, mover
        self.seed, self.name = seed, name
        self.truth = []

    def frames(self):
        from ..core.transform import fourier_shift, warp_similarity

        rng = np.random.default_rng(self.seed)
        H, W = self.base.shape[:2]
        out, self.truth = [], []
        for i in range(self.n):
            dy, dx = rng.uniform(-self.max_shift, self.max_shift, 2)
            ang = rng.uniform(-self.angle, self.angle) if self.angle else 0.0
            sc = 1.0 + rng.uniform(-1, 1) * (self.scale - 1.0) if self.scale != 1.0 else 1.0
            f = self.base
            if self.mover is not None:
                f = self.mover(f, i, self.n)
            if ang or sc != 1.0:
                f = warp_similarity(f, ang, sc)
            f = fourier_shift(f, dy, dx)
            if self.noise:
                f = np.clip(f + rng.normal(0.0, self.noise, f.shape), 0.0, 1.0)
            out.append(f)
            self.truth.append({"dy": float(dy), "dx": float(dx),
                               "angle": float(ang), "scale": float(sc)})
        return out


def moving_disc(radius=18, value=0.05, path=None):
    """A `mover` callable for SyntheticSource: paints a disc that travels
    across the frame. Drives the object-removal and highlight demos."""
    def _mover(img, i, n):
        H, W = img.shape[:2]
        t = i / max(n - 1, 1)
        cy, cx = (path(t, H, W) if path else (H * 0.5, W * (0.12 + 0.76 * t)))
        yy, xx = np.mgrid[0:H, 0:W]
        m = ((yy - cy) ** 2 + (xx - cx) ** 2) <= radius ** 2
        out = img.copy()
        out[m] = value
        return out
    return _mover
