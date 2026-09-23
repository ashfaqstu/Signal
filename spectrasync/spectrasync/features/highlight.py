"""Highlight the moving object.

Methodology (from the spec): use object removal, then detect high change, then
detect the outline.

Every step here is a FILTER, done as a multiplication in the frequency domain,
so the feature stays inside the syllabus instead of drifting into ad-hoc image
processing:

    change score  = band-pass( |frame - background| )   convolution theorem
    mask          = adaptive threshold on that score
    outline       = |grad(mask)| via j2*pi*u             differentiation property

The band-pass is the important one: it rejects lighting drift (below `low`) and
sensor noise (above `high`) in a single operation, which is exactly what a
change detector needs before any threshold is applied.
"""

from __future__ import annotations

import numpy as np

from ..core.filters import bandpass, gaussian_blur, gradient_magnitude, lowpass
from ..core.preprocess import as_float, to_gray, to_unit
from ..registry import Registry
from ..types import DetectionResult
from ..viz.overlays import tint

DETECTORS = Registry("change detector")


@DETECTORS.register("bandpass", doc="Difference of Gaussians. Rejects drift AND noise.")
def score_bandpass(diff, low=0.02, high=0.20, **kw):
    from ..core.filters import apply_filter
    return np.abs(apply_filter(np.abs(diff), bandpass(diff.shape, low, high)))


@DETECTORS.register("lowpass", doc="Smooth the difference only. Simple baseline.")
def score_lowpass(diff, sigma=2.0, **kw):
    return np.abs(gaussian_blur(np.abs(diff), sigma))


@DETECTORS.register("raw", doc="No filtering at all. Shows why filtering is needed.")
def score_raw(diff, **kw):
    return np.abs(diff)


def change_score(frame, background, detector="bandpass", **kw):
    """How much each pixel differs from the background, after filtering.

    Always computed on LUMA, even when `frame`/`background` are colour: change
    detection needs no colour information, and `outline_of` below relies on a
    2-D (H, W) mask -- a 3-D (H, W, 3) one would take its Fourier transform
    over the wrong axes. The colour, if any, only reappears later, in the
    overlay drawn over the original `frame`.
    """
    diff = to_gray(as_float(frame)) - to_gray(as_float(background))
    return DETECTORS[detector](diff, **kw)


def adaptive_threshold(score, k=3.0, mask=None):
    """mean + k * std of the score. Simple, scene-independent, one knob."""
    v = score[mask] if mask is not None else score
    return float(v.mean() + k * v.std())


def clean_mask(mask, smooth=1.5, keep=0.5):
    """Fill speckle and close gaps by low-pass filtering the mask itself.

    Blurring a binary mask and re-thresholding is morphological opening/closing
    expressed as filtering -- no structuring elements, no loops.
    """
    if smooth <= 0:
        return mask
    return gaussian_blur(mask.astype(np.float64), smooth) > keep


def outline_of(mask, smooth=1.0, width=0.15):
    """The boundary of a mask, via the differentiation property of the FT.

        d/dx f  <=>  j*2*pi*u * F(u,v)

    A little pre-smoothing keeps the derivative of a hard binary edge from
    ringing. Returns a float map in [0, 1].
    """
    g = gradient_magnitude(mask.astype(np.float64), smooth=smooth)
    peak = g.max()
    return (g / peak > width).astype(np.float64) if peak > 0 else g


def bounding_boxes(mask, min_area=40):
    """Axis-aligned boxes around each connected blob (BFS flood fill, no scipy)."""
    from collections import deque
    m = np.asarray(mask, dtype=bool)
    H, W = m.shape
    seen = np.zeros((H, W), dtype=bool)
    boxes = []
    for sy in range(H):
        for sx in range(W):
            if not m[sy, sx] or seen[sy, sx]:
                continue
            q = deque([(sy, sx)])
            seen[sy, sx] = True
            y0 = y1 = sy
            x0 = x1 = sx
            area = 0
            while q:
                y, x = q.popleft()
                area += 1
                y0, y1 = min(y0, y), max(y1, y)
                x0, x1 = min(x0, x), max(x1, x)
                for ny, nx in ((y-1, x), (y+1, x), (y, x-1), (y, x+1)):
                    if 0 <= ny < H and 0 <= nx < W and m[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        q.append((ny, nx))
            if area >= min_area:
                boxes.append((y0, x0, y1, x1))
    boxes.sort(key=lambda b: -((b[2]-b[0]+1) * (b[3]-b[1]+1)))
    return boxes


def highlight(frame, background, detector="bandpass", k=3.0, smooth=1.5,
              min_area=40, colour=(0.65, 0.19, 0.12), valid=None, **kw):
    """Full pipeline: background -> change score -> mask -> outline -> overlay.

    `frame` and `background` may be grayscale or colour; detection runs on
    luma either way (see `change_score`), and the overlay is drawn over
    `frame` exactly as given, so a colour photo gets a colour result.

    `valid`, if given, restricts both the threshold statistics and the score
    itself to the region where every input frame was actually aligned --
    pixels outside it never register as a detection.

    Returns a DetectionResult with `.mask`, `.outline`, `.overlay`, `.boxes`.
    """
    score = change_score(frame, background, detector=detector, **kw)
    if valid is not None:
        score = score * valid
    thr = adaptive_threshold(score, k=k, mask=valid)
    mask = clean_mask(score > thr, smooth=smooth)
    line = outline_of(mask)
    overlay = tint(line, colour, base=frame)
    return DetectionResult(mask=mask, outline=line, overlay=overlay,
                           boxes=bounding_boxes(mask, min_area=min_area),
                           score=score, threshold=thr)


def highlight_sequence(frames, background=None, **kw):
    """Highlight every frame of a sequence against ONE shared background plate.

    `mode` and `reducer` are the only kwargs a caller who has not already run
    object removal needs to supply -- they steer that step (see
    `remove_moving_objects`); every other kwarg (`detector`, `k`, `smooth`,
    `min_area`, `valid`, `low`/`high`, ...) is forwarded to `highlight` for
    each frame.

    Pass `background` explicitly (typically `remove_moving_objects(...).output`,
    computed once by the caller) to skip recomputing it here and to highlight
    `frames` exactly as given, in their own order.

    Returns `(detections, background)`, where `detections[i]` is the
    DetectionResult for `frames[i]`.
    """
    from .removal import remove_moving_objects
    if background is None:
        res = remove_moving_objects(frames, **{k: v for k, v in kw.items()
                                               if k in ("mode", "reducer")})
        frames, background = res.aligned, res.output
    opts = {k: v for k, v in kw.items() if k not in ("mode", "reducer")}
    return [highlight(f, background, **opts) for f in frames], background
