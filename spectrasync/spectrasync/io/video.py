"""Video I/O. Decoding H.264 is not a signals task either.

Tries imageio first, falls back to OpenCV -- whichever is installed. Both are
pure decoders; every frame becomes a plain float64 numpy array immediately.
"""

from __future__ import annotations

import numpy as np


def _backend():
    try:
        import imageio.v3 as iio  # noqa: F401
        return "imageio"
    except Exception:
        pass
    try:
        import cv2  # noqa: F401
        return "cv2"
    except Exception:
        return None


def read_video(path, max_frames=None, step=1, gray=True, max_side=None):
    """Read a video into a list of float64 arrays in [0, 1]."""
    from .images import to_gray

    backend = _backend()
    if backend is None:
        raise RuntimeError("no video backend: pip install imageio imageio-ffmpeg")

    frames = []
    if backend == "imageio":
        import imageio.v3 as iio
        for i, f in enumerate(iio.imiter(path)):
            if i % step:
                continue
            frames.append(np.asarray(f, dtype=np.float64) / 255.0)
            if max_frames and len(frames) >= max_frames:
                break
    else:
        import cv2
        cap = cv2.VideoCapture(str(path))
        i = 0
        while True:
            ok, bgr = cap.read()
            if not ok:
                break
            if i % step == 0:
                frames.append(bgr[:, :, ::-1].astype(np.float64) / 255.0)
            i += 1
            if max_frames and len(frames) >= max_frames:
                break
        cap.release()

    if max_side:
        frames = [_resize(f, max_side) for f in frames]
    return [to_gray(f) for f in frames] if gray else frames


def _resize(a, max_side):
    from PIL import Image
    h, w = a.shape[:2]
    if max(h, w) <= max_side:
        return a
    k = max_side / float(max(h, w))
    img = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))
    img = img.resize((max(1, int(w * k)), max(1, int(h * k))), Image.LANCZOS)
    return np.asarray(img, dtype=np.float64) / 255.0


def write_gif(path, frames, fps=15):
    """Always available -- Pillow needs no ffmpeg."""
    from PIL import Image
    ims = [Image.fromarray((np.clip(np.asarray(f), 0, 1) * 255).astype(np.uint8))
           for f in frames]
    ims[0].save(path, save_all=True, append_images=ims[1:],
                duration=int(1000 / fps), loop=0)
    return path


def write_video(path, frames, fps=30):
    """MP4 if a backend supports it, otherwise fall back to a GIF."""
    try:
        import imageio.v3 as iio
        iio.imwrite(path, [(np.clip(np.asarray(f), 0, 1) * 255).astype(np.uint8)
                           for f in frames], fps=fps)
        return path
    except Exception:
        alt = str(path).rsplit(".", 1)[0] + ".gif"
        return write_gif(alt, frames, fps=min(fps, 20))
