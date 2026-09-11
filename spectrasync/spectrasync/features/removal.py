"""Moving-object removal from video.

Methodology (from the spec): the same engine as multi-frame stacking, different
use case. Align the frames so the background is pinned, then take the pixelwise
MEDIAN. A moving object visits any given pixel in only a minority of frames, so
at every pixel it is an outlier, and the median throws it away.

The signals framing, which is the part worth saying out loud: after alignment,
each pixel is a 1-D signal sampled once per frame. The background is its
persistent level; the moving object is a transient burst. Removal is therefore
temporal filtering -- and it is specifically NONLINEAR filtering, because no LTI
filter can reject an impulse without also smearing it. `compare_temporal_filters`
below produces exactly that demonstration.
"""

from __future__ import annotations

import numpy as np

from ..core.preprocess import as_float
from ..types import StackResult
from .stacking import stack
from .temporal import reduce


def remove_moving_objects(frames, reducer="median", mode="translation", **kwargs):
    """Estimate the clean background plate of a sequence.

    Requirements, and they are hard limits worth stating in a report:
      * the object must leave any given pixel in MORE than half the frames
        (that is what "median" means), and
      * the camera motion must be within the alignment model.
    """
    return stack(frames, reducer=reducer, mode=mode, **kwargs)


def background_and_foreground(frames, reducer="median", mode="translation", **kwargs):
    """Returns (StackResult, residuals) where residuals[i] = aligned[i] - plate.

    The residual sequence IS the moving content, isolated. It feeds the
    highlight feature directly.
    """
    res = remove_moving_objects(frames, reducer=reducer, mode=mode, **kwargs)
    residuals = [a - res.output for a in res.aligned]
    return res, residuals


def pixel_timeseries(aligned, y, x):
    """The 1-D temporal signal at one pixel, plus its spectrum.

    Plot this next to a frame with the pixel marked: the flat level is the
    background, the dip or spike is the object crossing. It makes 'each pixel
    is a signal' concrete in one figure.
    """
    sig = np.array([float(as_float(f)[y, x]) for f in aligned])
    spec = np.abs(np.fft.rfft(sig - sig.mean()))
    freq = np.fft.rfftfreq(len(sig))
    return sig, freq, spec


def compare_temporal_filters(aligned, lowpass_frac=0.15):
    """Reduce the same stack with a linear and a nonlinear filter.

    Returns {name: image}. Expect the linear ones to GHOST -- the object stays
    faintly visible -- while the median removes it cleanly. That contrast is the
    lesson: an impulsive outlier is not removable by any LTI filter.
    """
    a = np.stack([as_float(f) for f in aligned], axis=0)
    n = a.shape[0]

    out = {"mean (linear, LTI)": a.mean(axis=0),
           "median (nonlinear)": np.median(a, axis=0)}

    # temporal low-pass: filter along the frame axis in the frequency domain
    F = np.fft.rfft(a, axis=0)
    f = np.fft.rfftfreq(n)
    F = F * np.exp(-0.5 * (f / max(lowpass_frac, 1e-6)) ** 2).reshape(-1, 1, 1)
    out["temporal low-pass (linear, LTI)"] = np.fft.irfft(F, n=n, axis=0).mean(axis=0)

    out["sigma-clipped mean (nonlinear)"] = reduce(list(a), "sigma_clip")
    return out


def running_median(frames, window=5, mode="translation", align=True, **kwargs):
    """Sliding-window median: a TIME-VARYING background plate.

    A single global median assumes the background never changes. With a window,
    slow lighting drift is tracked while fast objects are still rejected --
    the temporal-filter view taken one step further.
    """
    frames = [as_float(f) for f in frames]
    if align:
        from .stacking import align_frames
        frames, _ = align_frames(frames, mode=mode, **kwargs)
    n = len(frames)
    half = max(1, int(window) // 2)
    plates = []
    for i in range(n):
        lo, hi = max(0, i - half), min(n, i + half + 1)
        plates.append(np.median(np.stack(frames[lo:hi], axis=0), axis=0))
    return frames, plates
