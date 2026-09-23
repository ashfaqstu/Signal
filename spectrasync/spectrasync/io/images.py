"""Image file I/O. Decoding is not a signals task -- Pillow only appears here."""

from __future__ import annotations

import glob
import os

import io

import numpy as np
from PIL import Image, ImageOps

from ..core.preprocess import LUMA, to_gray  # noqa: F401  (re-exported)


def load_rgb(path, max_side=None):
    """Load any image (path or file-like) as float64 RGB in [0, 1].

    `max_side` DOWNSCALES so the longer side fits -- the whole picture is kept.
    EXIF orientation is applied, so a phone photo comes out upright.
    """
    img = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    if max_side:
        w, h = img.size
        if max(w, h) > max_side:
            k = max_side / float(max(w, h))
            img = img.resize((max(1, int(w * k)), max(1, int(h * k))), Image.LANCZOS)
    return np.asarray(img, dtype=np.float64) / 255.0


def load_gray(path, max_side=None):
    """Load any image as float64 grayscale in [0, 1]."""
    return to_gray(load_rgb(path, max_side=max_side))


def resize_to(a, shape):
    """Resample a float image to (H, W) with Lanczos. Works on (H, W) and (H, W, C)."""
    a = np.asarray(a, dtype=np.float64)
    H, W = int(shape[0]), int(shape[1])
    if a.shape[:2] == (H, W):
        return a
    def one(ch):
        im = Image.fromarray(ch.astype(np.float32)).resize((W, H), Image.LANCZOS)
        return np.asarray(im, dtype=np.float64)
    if a.ndim == 2:
        return one(a)
    return np.stack([one(a[..., c]) for c in range(a.shape[2])], axis=-1)


def resize_max_side(a, max_side):
    """Downscale so the longer side is at most `max_side`. Never crops, never
    upscales -- the aspect ratio and the whole field of view are kept."""
    a = np.asarray(a, dtype=np.float64)
    h, w = a.shape[:2]
    if not max_side or max(h, w) <= max_side:
        return a
    k = max_side / float(max(h, w))
    return resize_to(a, (max(1, round(h * k)), max(1, round(w * k))))


def load_many(sources, max_side=None, gray=True):
    """Load several images (paths or file-like objects) at ONE common size.

    A stack needs identical shapes, and shots from one camera can still differ
    by a pixel or two, so every image is RESIZED to the first one's shape --
    never cropped.
    """
    load = load_gray if gray else load_rgb
    out = [load(s, max_side=max_side) for s in sources]
    if out:
        shape = out[0].shape[:2]
        out = [resize_to(a, shape) for a in out]
    return out


def save_png(path, arr):
    """Write a float array in [0, 1] (or [0,1]^3) as an 8-bit PNG."""
    a = np.clip(np.asarray(arr, dtype=np.float64), 0.0, 1.0)
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    Image.fromarray((a * 255.0).round().astype(np.uint8)).save(path)
    return path


def png_bytes(arr):
    """The same 8-bit PNG as `save_png`, returned as bytes (for a download)."""
    a = np.clip(np.asarray(arr, dtype=np.float64), 0.0, 1.0)
    buf = io.BytesIO()
    Image.fromarray((a * 255.0).round().astype(np.uint8)).save(buf, format="PNG")
    return buf.getvalue()


def centre_square(a):
    """The largest centred even square cropped from an image already at its
    working size -- the log-polar (Fourier-Mellin) stage needs one.

    Unlike `even_square`, this never resizes: call it once the image is
    already the size you want. Because the crop shares the image's centre, an
    angle, scale or shift measured on it applies unchanged to the whole image.
    """
    n = min(a.shape[0], a.shape[1]) // 2 * 2
    y0, x0 = (a.shape[0] - n) // 2, (a.shape[1] - n) // 2
    return a[y0:y0 + n, x0:x0 + n]


def even_square(a, max_side=512):
    """An even square no larger than `max_side` -- required by the log-polar stage.

    Downscales FIRST so the short side fits, then crops to a centred square
    (see `centre_square`), so a big photo keeps its full field of view instead
    of shrinking to a tiny centre patch.
    """
    a = np.asarray(a, dtype=np.float64)
    short, long_ = min(a.shape[:2]), max(a.shape[:2])
    if short > max_side:
        a = resize_max_side(a, int(round(long_ * max_side / short)))
    n = min(a.shape[0], a.shape[1], max_side)
    n = n // 2 * 2
    y0 = (a.shape[0] - n) // 2
    x0 = (a.shape[1] - n) // 2
    return a[y0:y0 + n, x0:x0 + n]


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
