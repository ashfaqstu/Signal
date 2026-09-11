"""Image file I/O. Decoding is not a signals task -- Pillow only appears here."""

from __future__ import annotations

import glob
import os

import numpy as np
from PIL import Image

#: Rec.709 luma weights. Perceptually correct, unlike a plain channel mean, so
#: edges keep their contrast and the correlation peak stays sharp.
LUMA = np.array([0.2126, 0.7152, 0.0722])


def to_gray(rgb):
    """(H, W, 3) float -> (H, W) float luma. Passes (H, W) through unchanged."""
    a = np.asarray(rgb, dtype=np.float64)
    return a if a.ndim == 2 else a[..., :3] @ LUMA


def load_rgb(path, max_side=None):
    """Load any image as float64 RGB in [0, 1]."""
    img = Image.open(path).convert("RGB")
    if max_side:
        w, h = img.size
        if max(w, h) > max_side:
            k = max_side / float(max(w, h))
            img = img.resize((max(1, int(w * k)), max(1, int(h * k))), Image.LANCZOS)
    return np.asarray(img, dtype=np.float64) / 255.0


def load_gray(path, max_side=None):
    """Load any image as float64 grayscale in [0, 1]."""
    return to_gray(load_rgb(path, max_side=max_side))


def save_png(path, arr):
    """Write a float array in [0, 1] (or [0,1]^3) as an 8-bit PNG."""
    a = np.clip(np.asarray(arr, dtype=np.float64), 0.0, 1.0)
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    Image.fromarray((a * 255.0).round().astype(np.uint8)).save(path)
    return path


def load_folder(pattern, max_side=None, gray=True, limit=None):
    """Load every image matching a glob, sorted by name. Returns a list."""
    paths = sorted(glob.glob(pattern))
    if limit:
        paths = paths[:limit]
    load = load_gray if gray else load_rgb
    return [load(p, max_side=max_side) for p in paths], paths


def crop_pair(big, dy, dx, size, origin=None):
    """Two overlapping crops of one large image, at a known offset.

    This is the honest test pair: a REAL translation where new content enters at
    the edges, with ground truth you control. `mov` is sampled from a window
    starting dy rows earlier, so its content sits dy rows LOWER -- matching the
    project convention mov[y,x] = ref[y-dy, x-dx].
    """
    big = np.asarray(big, dtype=np.float64)
    H, W = size
    if origin is None:
        origin = ((big.shape[0] - H) // 2, (big.shape[1] - W) // 2)
    y0, x0 = origin
    ref = big[y0:y0 + H, x0:x0 + W]
    mov = big[y0 - dy:y0 - dy + H, x0 - dx:x0 - dx + W]
    if ref.shape[:2] != (H, W) or mov.shape[:2] != (H, W):
        raise ValueError("crop ran off the edge: reduce the shift or the size")
    return np.ascontiguousarray(ref), np.ascontiguousarray(mov)


def circular_pair(img, dy, dx):
    """An exactly circular shift. The DFT model is EXACT for this pair, so an
    unwindowed estimate must be exact too -- this is the correctness test."""
    img = np.asarray(img, dtype=np.float64)
    return img, np.roll(img, (int(dy), int(dx)), axis=(0, 1))
