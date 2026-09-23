"""Temporal reducers -- the pivot of all three applied features.

Think of a registered stack as one 1-D signal PER PIXEL, sampled once per frame.
Reducing that signal to a single number is a filtering choice, and the choice is
the whole difference between the three features:

    noise reduction  -> you want the statistically best estimate  -> MEAN
    object removal   -> you want to reject outliers               -> MEDIAN

For zero-mean Gaussian noise, var(median) -> (pi/2) * var(mean) as N grows,
so the median is about 1.96 dB WORSE at pure denoising. It is nevertheless the
right choice when a moving object makes some samples outliers, because no
linear (LTI) filter can reject an impulse. `sigma_clip` is the compromise that
gets close to mean performance while still throwing outliers away.
"""

from __future__ import annotations

import numpy as np

from ..registry import Registry

REDUCERS = Registry("temporal reducer")


def _stack(frames):
    return np.stack([np.asarray(f, dtype=np.float64) for f in frames], axis=0)


@REDUCERS.register("mean", doc="Optimal for Gaussian noise: +10*log10(N) dB. No outlier rejection.")
def reduce_mean(frames, **kw):
    return _stack(frames).mean(axis=0)


@REDUCERS.register("median", doc="Rejects outliers. ~1.96 dB worse than mean on pure noise.")
def reduce_median(frames, **kw):
    return np.median(_stack(frames), axis=0)


@REDUCERS.register("mode", doc="Most frequent value at each pixel: the literal mode, not the middle.")
def reduce_mode(frames, levels=256, **kw):
    """The value that occurs most often at each pixel, across frames -- the
    literal statistical mode, as distinct from `median`'s "middle value" and
    `shorth`'s "tightest majority run".

    Continuous pixel intensities essentially never repeat exactly, so "most
    frequent" is made well-defined by quantising to `levels` evenly spaced
    bins first (256, the default, matches an 8-bit image -- the source of
    virtually every photo here). A tie between equally frequent bins is
    broken toward the darker one.

    Multi-channel frames are binned by LUMA, so every channel keeps the SAME
    per-pixel subset of frames -- no colour fringing at the boundary, exactly
    as in `shorth`. The reported value is the MEAN of the actual, unquantised
    samples that fell in the winning bin, not the bin's edge, so the result
    is not visibly banded.
    """
    a = _stack(frames)                       # (N, H, W) or (N, H, W, C)
    n = a.shape[0]
    lum = a if a.ndim == 3 else a @ np.array([0.2126, 0.7152, 0.0722])
    bins = np.clip((lum * (levels - 1)).round(), 0, levels - 1).astype(np.int64)

    # Sort each pixel's bin values so identical ones become one contiguous
    # run -- the run with the most members IS the mode.
    order = np.argsort(bins, axis=0)                      # (N, H, W), ascending
    sorted_bins = np.take_along_axis(bins, order, axis=0)
    starts_run = np.empty_like(sorted_bins, dtype=bool)
    starts_run[0] = True
    starts_run[1:] = sorted_bins[1:] != sorted_bins[:-1]
    run_of_rank = np.cumsum(starts_run, axis=0) - 1        # 0 .. n_runs-1, per rank

    # Express each frame's run membership in FRAME order rather than sorted
    # rank order (the same "ranks" trick `shorth` uses).
    rank = np.arange(n).reshape((n,) + (1,) * (order.ndim - 1))
    ranks = np.empty_like(order)
    np.put_along_axis(ranks, order, np.broadcast_to(rank, order.shape), axis=0)
    run_of_frame = np.take_along_axis(run_of_rank, ranks, axis=0)   # (N, H, W)

    # Tally each run's size with one scatter-add per frame -- bounded by N
    # rows, so this costs no more memory than the stack itself.
    flat_run = run_of_frame.reshape(n, -1)
    cols = np.arange(flat_run.shape[1])
    run_size = np.zeros((n, flat_run.shape[1]), dtype=np.int64)
    for f in range(n):
        run_size[flat_run[f], cols] += 1

    winner = np.argmax(run_size, axis=0)                    # winning run, per pixel
    keep = run_of_frame == winner.reshape(bins.shape[1:])   # (N, H, W): this pixel's mode frames
    count = run_size[winner, cols].reshape(bins.shape[1:])  # how many frames agreed
    if a.ndim == 4:
        keep, count = keep[..., None], count[..., None]
    return (a * keep).sum(axis=0) / count


@REDUCERS.register("sigma_clip", doc="Iterated mean with outliers removed. Best of both.")
def reduce_sigma_clip(frames, sigma=2.5, iters=3, **kw):
    a = _stack(frames)
    mask = np.ones_like(a, dtype=bool)
    for _ in range(int(iters)):
        n = mask.sum(axis=0)
        mu = np.where(n > 0, (a * mask).sum(axis=0) / np.maximum(n, 1), 0.0)
        var = np.where(n > 1, ((a - mu) ** 2 * mask).sum(axis=0) / np.maximum(n - 1, 1), 0.0)
        sd = np.sqrt(var)
        new = np.abs(a - mu) <= (sigma * sd + 1e-9)
        new |= (sd <= 1e-9)                      # never clip a constant pixel away
        if np.array_equal(new, mask):
            break
        mask = new
    n = mask.sum(axis=0)
    return np.where(n > 0, (a * mask).sum(axis=0) / np.maximum(n, 1),
                    np.median(a, axis=0))


@REDUCERS.register("shorth", doc="Shortest majority run, averaged. Fixes median's near-50/50 blend.")
def reduce_shorth(frames, **kw):
    """The 'shortest half' (Rousseeuw's shorth): of every run of
    h = N//2 + 1 consecutive order statistics, keep the tightest (smallest
    max - min) and average just that run.

    Why plain `median` is not enough: with an EVEN frame count, numpy's median
    is the MEAN of the two middle order statistics. If the object occupies a
    pixel in close to half the frames -- or one frame lands with an in-between
    value right at that boundary (a soft edge, a shadow, a slightly
    misaligned frame) -- that average blends a real background sample with
    object content, and the object stays faintly visible. `shorth` instead
    looks at every majority-sized run of the sorted values and keeps
    whichever one is most self-consistent, so a stray in-between sample gets
    OUTVOTED rather than averaged in.

    Multi-channel frames are ranked by LUMA, so every channel keeps the SAME
    per-pixel subset of frames -- no colour fringing at the boundary.
    """
    a = _stack(frames)                       # (N, H, W) or (N, H, W, C)
    n = a.shape[0]
    h = n // 2 + 1
    if n < 3:
        return np.median(a, axis=0)

    lum = a if a.ndim == 3 else a @ np.array([0.2126, 0.7152, 0.0722])
    order = np.argsort(lum, axis=0)                        # (N, H, W), ascending
    sorted_lum = np.take_along_axis(lum, order, axis=0)
    span = sorted_lum[h - 1:] - sorted_lum[:n - h + 1]      # (N-h+1, H, W)
    start = np.argmin(span, axis=0)                         # (H, W): best run's start rank

    rank = np.arange(n).reshape((n,) + (1,) * (order.ndim - 1))
    ranks = np.empty_like(order)
    np.put_along_axis(ranks, order, np.broadcast_to(rank, order.shape), axis=0)
    keep = (ranks >= start) & (ranks < start + h)           # (N, H, W): this pixel's h frames
    if a.ndim == 4:
        keep = keep[..., None]
    return (a * keep).sum(axis=0) / h


@REDUCERS.register("trimmed_mean", doc="Mean after dropping the extremes at each pixel.")
def reduce_trimmed_mean(frames, trim=0.2, **kw):
    a = np.sort(_stack(frames), axis=0)
    n = a.shape[0]
    k = int(np.floor(n * float(trim) / 2.0))
    return a[k:n - k].mean(axis=0) if n - 2 * k > 0 else a.mean(axis=0)


@REDUCERS.register("min", doc="Pixelwise minimum. Removes bright transients.")
def reduce_min(frames, **kw):
    return _stack(frames).min(axis=0)


@REDUCERS.register("max", doc="Pixelwise maximum. Removes dark transients; star trails.")
def reduce_max(frames, **kw):
    return _stack(frames).max(axis=0)


@REDUCERS.register("weighted_mean", doc="Mean weighted per frame (e.g. by alignment confidence).")
def reduce_weighted_mean(frames, weights=None, **kw):
    a = _stack(frames)
    if weights is None:
        return a.mean(axis=0)
    w = np.asarray(weights, dtype=np.float64).reshape(-1, *([1] * (a.ndim - 1)))
    w = np.clip(w, 0.0, None)
    tot = w.sum()
    return (a * w).sum(axis=0) / (tot if tot > 0 else 1.0)


@REDUCERS.register("fourier_snr", doc="Per-frequency SNR-weighted average (Wiener-style).")
def reduce_fourier_snr(frames, noise_band=0.35, **kw):
    """Combine frames in the FREQUENCY domain, weighting each bin by its
    estimated signal-to-noise ratio.

    The noise floor is estimated from the high-frequency tail (above
    `noise_band` cycles/pixel), where a natural image has almost no signal.
    Bins with little signal above that floor are attenuated. This is the
    matched-filter / Wiener argument applied to stacking.
    """
    from ..core.filters import radial_freq

    a = _stack(frames)
    n = a.shape[0]
    F = np.fft.fft2(a, axes=(1, 2))
    power = (np.abs(F) ** 2).mean(axis=0)
    rad = radial_freq(a.shape[1:3])
    tail = rad >= noise_band
    noise = float(power[tail].mean()) if tail.any() else 0.0
    signal = np.maximum(power - noise, 0.0)
    gain = signal / (signal + noise + 1e-20)     # Wiener gain per bin
    return np.real(np.fft.ifft2(F.mean(axis=0) * gain, axes=(0, 1)))


def reduce(frames, method="median", **kw):
    """Apply a named reducer. `REDUCERS.names()` drives every UI dropdown."""
    return REDUCERS[method](frames, **kw)


def theoretical_gain_db(n, method="mean"):
    """Expected PSNR improvement over a single frame, for white Gaussian noise.

    mean       10*log10(N)
    median     10*log10(N) - 10*log10(pi/2)   (about 1.96 dB less, large N)
    """
    if n <= 1:
        return 0.0
    base = 10.0 * np.log10(n)
    if method == "median":
        return float(base - 10.0 * np.log10(np.pi / 2.0))
    return float(base)
