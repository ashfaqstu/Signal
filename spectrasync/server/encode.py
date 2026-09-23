"""Encoding utilities: ndarray -> PNG / JPEG / colormapped heatmap bytes."""

from __future__ import annotations

import io
import matplotlib
import matplotlib.cm
import numpy as np
from PIL import Image

import spectrasync as ss


def to_png(arr: np.ndarray | list) -> bytes:
    """Encode an array as PNG bytes.
    
    If 2D float array is not already in [0, 1], applies ss.to_unit.
    If 3D array, clips to [0, 1].
    """
    a = np.asarray(arr, dtype=np.float64)
    if a.ndim == 2:
        a = ss.to_unit(a)
    elif a.ndim == 3:
        a = np.clip(a, 0.0, 1.0)
    return ss.png_bytes(a)


def heatmap_png(arr: np.ndarray | list, cmap: str = "inferno") -> bytes:
    """Normalize 2D array and map through matplotlib colormap to RGB PNG bytes."""
    a = np.asarray(arr, dtype=np.float64)
    if a.ndim > 2:
        a = a.squeeze()
    unit = ss.to_unit(a)
    try:
        cm = matplotlib.colormaps[cmap]
    except (AttributeError, KeyError):
        cm = matplotlib.cm.get_cmap(cmap)
    rgba = cm(unit)  # float in [0, 1], shape (H, W, 4)
    rgb = (rgba[..., :3] * 255.0).round().astype(np.uint8)
    buf = io.BytesIO()
    Image.fromarray(rgb).save(buf, format="PNG")
    return buf.getvalue()


def thumb_jpeg(arr: np.ndarray | list, max_side: int = 160) -> bytes:
    """Downsample and encode as compact JPEG bytes for thumbnails."""
    a = np.asarray(arr, dtype=np.float64)
    if a.ndim == 2:
        a = ss.to_unit(a)
        rgb = (np.clip(a, 0.0, 1.0) * 255.0).round().astype(np.uint8)
        img = Image.fromarray(rgb, mode="L").convert("RGB")
    elif a.ndim == 3:
        rgb = (np.clip(a, 0.0, 1.0) * 255.0).round().astype(np.uint8)
        img = Image.fromarray(rgb, mode="RGB")
    else:
        raise ValueError(f"Unsupported array shape for thumbnail: {a.shape}")

    w, h = img.size
    if max(w, h) > max_side:
        k = max_side / float(max(w, h))
        img = img.resize((max(1, int(round(w * k))), max(1, int(round(h * k)))), Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def log_spectrum(F: np.ndarray) -> np.ndarray:
    """Log-magnitude spectrum shifted to center."""
    return np.log1p(np.abs(np.fft.fftshift(F)))


def phase_image(R: np.ndarray) -> np.ndarray:
    """Phase angle spectrum shifted to center."""
    return np.angle(np.fft.fftshift(R))
