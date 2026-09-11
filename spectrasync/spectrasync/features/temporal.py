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
    return np.real(np.fft.ifft2(F.mean(axis=0) * gain))


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
