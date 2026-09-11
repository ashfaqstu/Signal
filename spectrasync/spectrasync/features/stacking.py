"""The align + reduce engine. All three applied features are this function.

    frames -> register onto a reference -> reduce pixelwise -> output

    multi-frame stacking : reducer = mean / sigma_clip   -> a cleaner image
    object removal       : reducer = median             -> a clean background
    highlight            : reducer = median, then compare each frame to it

Because it is one engine, a change made for one feature is a change made for
all three -- and there is one place to look when something misbehaves.
"""

from __future__ import annotations

import numpy as np

from ..core.metrics import ncc, psnr
from ..core.preprocess import as_float
from ..core.register import register_many
from ..core.transform import alignment_valid_mask
from ..types import StackResult
from .temporal import REDUCERS, reduce, theoretical_gain_db


def align_frames(frames, reference=0, mode="translation", **kwargs):
    """Register every frame onto one reference. Returns (aligned, results)."""
    return register_many(frames, reference=reference, mode=mode, **kwargs)


def common_valid_mask(results, shape):
    """Pixels that are valid in EVERY aligned frame. Reducing outside this
    region mixes real data with wrapped content and produces edge artefacts."""
    m = np.ones((shape[0], shape[1]), dtype=bool)
    for r in results:
        m &= alignment_valid_mask(shape, r.angle_deg, r.scale, r.dy, r.dx)
    return m


def stack(frames, reducer="median", reference=0, mode="translation",
          align=True, mask_invalid=True, reducer_kwargs=None, **kwargs):
    """Align a sequence and collapse it to one image.

    Parameters
    ----------
    reducer : any name in `features.temporal.REDUCERS`
    mode    : "translation" (spec default), "similarity", or "auto"
    align   : set False to reduce without registering -- the A/B that shows
              why alignment matters at all
    mask_invalid : blank pixels that are not valid in every frame

    Returns a StackResult with `.output`, `.aligned`, `.shifts` and `.stats`.
    """
    frames = [as_float(f) for f in frames]
    if not frames:
        raise ValueError("no frames given")

    if align:
        aligned, results = align_frames(frames, reference=reference, mode=mode, **kwargs)
        shifts = [(r.dy, r.dx) for r in results]
        confid = [r.stats.ratio for r in results]
        n_locked = sum(1 for r in results if r.stats.ratio >= 1.5)
    else:
        aligned, results = frames, []
        shifts = [(0.0, 0.0)] * len(frames)
        confid = [float("nan")] * len(frames)
        n_locked = None

    out = reduce(aligned, reducer, **(reducer_kwargs or {}))

    if mask_invalid and results:
        m = common_valid_mask(results, out.shape)
        out = np.where(m, out, reduce(frames, reducer, **(reducer_kwargs or {})))
    else:
        m = np.ones(out.shape[:2], dtype=bool)

    return StackResult(
        output=out, aligned=aligned, shifts=shifts, reducer=reducer,
        n_frames=len(frames),
        stats={"confidence": confid,
               "n_locked": n_locked if align else None,
               "valid_fraction": float(m.mean()),
               "theoretical_gain_db": theoretical_gain_db(len(frames), reducer),
               "mode": mode, "aligned": align})


def stack_report(result, truth=None, single=None, mask=None):
    """Measured quality of a stack. Pass `truth` (the clean image) to get the
    real PSNR gain, and `single` (one raw frame) for the baseline."""
    out = {"n_frames": result.n_frames, "reducer": result.reducer}
    out.update(result.stats)
    if truth is not None:
        base = single if single is not None else result.aligned[0]
        out["psnr_single"] = psnr(truth, base, mask)
        out["psnr_stacked"] = psnr(truth, result.output, mask)
        out["psnr_gain_db"] = out["psnr_stacked"] - out["psnr_single"]
        out["ncc_stacked"] = ncc(truth, result.output, mask)
    return out


def compare_reducers(frames, reducers=None, truth=None, mask=None, **kwargs):
    """Run the same aligned stack through several reducers and measure each.

    This is the figure that justifies the spec's choice of median: it shows the
    mean winning on pure noise and the median winning once outliers appear.
    """
    names = reducers or ["mean", "median", "sigma_clip", "trimmed_mean", "fourier_snr"]
    aligned, results = align_frames(frames, **kwargs)
    rows = []
    for name in names:
        out = reduce(aligned, name)
        row = {"reducer": name,
               "theory_gain_db": theoretical_gain_db(len(frames), name)}
        if truth is not None:
            row["psnr"] = psnr(truth, out, mask)
            row["gain_db"] = row["psnr"] - psnr(truth, aligned[0], mask)
            row["ncc"] = ncc(truth, out, mask)
        rows.append((row, out))
    return rows
