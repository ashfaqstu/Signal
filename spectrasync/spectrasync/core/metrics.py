"""Confidence and image-similarity metrics. Pure functions, no state."""

from __future__ import annotations

import numpy as np

from ..types import PeakStats
from .preprocess import as_float


def peak_metrics(corr, exclude=5):
    """Quality of a correlation peak.

    The peak is rolled to the array centre first so the exclusion box cannot
    wrap around the edge. Uses |corr| for location, so a NEGATIVE peak (which
    means the two images have inverted contrast) is found rather than missed.

    Measured reference values on 256x256 crops:
        clean pair      peak 0.87   psr 460   ratio 92
        + noise s=0.15  peak 0.09   psr  24   ratio 4.2
        featureless     peak 0.024  psr 6.2   ratio 1.08
        unrelated       peak 0.020  psr 5.1   ratio 1.04
    `ratio` is the only one that separates the last two: use it to decide.
    """
    corr = np.asarray(corr, dtype=np.float64)
    H, W = corr.shape
    py, px = np.unravel_index(np.argmax(np.abs(corr)), corr.shape)
    signed = float(corr[py, px])

    c = np.roll(np.abs(corr), (H // 2 - py, W // 2 - px), axis=(0, 1))
    cy, cx = H // 2, W // 2
    peak = float(c[cy, cx])

    mask = np.ones_like(c, dtype=bool)
    mask[cy - exclude:cy + exclude + 1, cx - exclude:cx + exclude + 1] = False
    side = c[mask]
    psr = float((peak - side.mean()) / (side.std() + 1e-12))
    ratio = float(peak / (side.max() + 1e-12))
    return PeakStats(peak=peak, psr=psr, ratio=ratio,
                     polarity=float(np.sign(signed)) or 1.0)


def rmse(a, b, mask=None):
    d = (as_float(a) - as_float(b)) ** 2
    return float(np.sqrt(d[mask].mean() if mask is not None else d.mean()))


def psnr(a, b, mask=None, peak=1.0):
    e = rmse(a, b, mask)
    return float("inf") if e == 0 else float(20.0 * np.log10(peak / e))


def ncc(a, b, mask=None):
    a, b = as_float(a), as_float(b)
    if mask is not None:
        a, b = a[mask], b[mask]
    a = a - a.mean()
    b = b - b.mean()
    return float((a * b).sum() / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12))


def estimate_noise(img, mask=None):
    """Noise sigma of ONE image, with no clean reference (Immerkaer, 1996).

    Convolve with the 3x3 kernel [[1,-2,1],[-2,4,-2],[1,-2,1]] -- the
    difference of two Laplacians, which cancels smooth image structure and
    leaves mostly noise -- then

        sigma = sqrt(pi/2) * mean|I * N| / 6

    Real texture still leaks through a little, so a clean photo reads a small
    positive floor rather than zero. Compare values on the SAME scene: a raw
    frame against the stacked output is exactly that comparison.
    """
    from .preprocess import to_gray
    a = to_gray(as_float(img))
    c = (a[:-2, :-2] - 2 * a[:-2, 1:-1] + a[:-2, 2:]
         - 2 * a[1:-1, :-2] + 4 * a[1:-1, 1:-1] - 2 * a[1:-1, 2:]
         + a[2:, :-2] - 2 * a[2:, 1:-1] + a[2:, 2:])
    c = np.abs(c)
    if mask is not None:
        c = c[np.asarray(mask, dtype=bool)[1:-1, 1:-1]]
    return float(np.sqrt(np.pi / 2.0) * c.mean() / 6.0)


def angle_error_deg(estimated_deg, true_deg):
    """Absolute angular error in degrees, wrapped at +-180 first.

    A plain subtraction is wrong at the wrap: 179 deg and -179 deg are 2
    degrees apart, not 358. Wrapping into (-180, 180] before the absolute
    value fixes it. Used to score a `func_rotation_and_scale` estimate
    against a known angle.
    """
    return float(abs(((estimated_deg - true_deg + 180.0) % 360.0) - 180.0))


def percent_error(estimated, true):
    """|estimated - true| / |true|, as a percentage. Used to score a scale
    estimate against a known value."""
    return float(100.0 * abs(estimated - true) / abs(true)) if true else float("inf")


def shift_error(true_dy, true_dx, est_dy, est_dx):
    """Absolute per-axis error and its Euclidean norm."""
    ey, ex = abs(est_dy - true_dy), abs(est_dx - true_dx)
    return {"ey": float(ey), "ex": float(ex), "euclid": float(np.hypot(ey, ex))}


def itf(frames, margin=20):
    """Inter-frame transformation fidelity: mean PSNR between consecutive
    frames. Higher means the sequence is steadier."""
    vals = []
    for a, b in zip(frames[:-1], frames[1:]):
        s = (slice(margin, -margin), slice(margin, -margin))
        vals.append(psnr(a[s], b[s]))
    return float(np.mean(vals)) if vals else float("nan")
