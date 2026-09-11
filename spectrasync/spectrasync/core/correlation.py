"""func_translation -- spatial translation by phase correlation.

    Fourier shift theorem  ->  Dirac delta  ->  spike  ->  coordinate  ->  shift

Theory: a translation in space is a LINEAR PHASE RAMP in frequency.

    f2(x,y) = f1(x-x0, y-y0)   <=>   F2 = F1 * exp(-j2pi(u*x0 + v*y0))

The magnitude is untouched, so divide it out and only the ramp survives:

    R = F2 conj(F1) / |F2 conj(F1)|  =  exp(-j2pi(u*x0 + v*y0))

whose inverse transform is a delta at the shift. Find the spike, read its
coordinate. Full derivation in legacy/docs/01-THEORY.md.

CONVENTION, fixed project-wide and covered by tests:
    mov[y, x] = ref[y - dy, x - dx]
    +dy = content moved DOWN,  +dx = content moved RIGHT
    Rc = F2 * conj(F1)  -- the MOVED image goes first.
"""

from __future__ import annotations

import numpy as np

from ..types import TranslationResult
from .metrics import peak_metrics
from .preprocess import as_float, downsample2
from .subpixel import SUBPIXEL
from .windows import window2d


def cross_power_spectrum(ref, mov, window="hann", beta=1.0, eps=1e-12):
    """The normalised cross-power spectrum R, plus the two transforms.

    `beta` is the magnitude-normalisation exponent:
        1.0 -> textbook phase correlation (sharpest peak, noise sensitive)
        0.0 -> plain cross-correlation    (broad peak, noise robust)
    Measured optimum on a noisy pair: about 0.8, not 1.0.

    Returns (R, F1, F2) so callers can plot the spectra without recomputing.
    """
    a = as_float(ref)
    b = as_float(mov)
    if a.shape != b.shape:
        raise ValueError(f"shape mismatch: {a.shape} vs {b.shape}")
    a = a - a.mean()
    b = b - b.mean()
    if window and window != "none":
        w = window2d(a.shape, window)
        a = a * w
        b = b * w
    F1 = np.fft.fft2(a)
    F2 = np.fft.fft2(b)
    Rc = F2 * np.conj(F1)
    R = Rc / (np.abs(Rc) ** beta + eps)
    return R, F1, F2


def correlation_surface(ref, mov, window="hann", beta=1.0, spectral_mask=None):
    """Inverse transform of R: ideally a delta at the shift.

    `spectral_mask` is an optional multiplicative mask applied to R before the
    inverse FFT -- see core.filters. Low-passing R broadens the peak, which is
    the visible proof that localisation lives in the high frequencies.
    """
    R, _, _ = cross_power_spectrum(ref, mov, window=window, beta=beta)
    if spectral_mask is not None:
        R = R * spectral_mask
    return np.real(np.fft.ifft2(R))


def unwrap_peak(py, px, shape):
    """DFT indices above half the dimension represent negative shifts."""
    H, W = shape
    dy = py - H if py > H / 2 else py
    dx = px - W if px > W / 2 else px
    return float(dy), float(dx)


def phase_correlation(ref, mov, window="hann", subpixel="parabolic", beta=1.0,
                      spectral_mask=None, keep_corr=True):
    """Estimate the translation (dy, dx) between two same-shaped images.

    Returns a TranslationResult (`.dy`, `.dx`, `.stats`, `.corr`).

    Peak location uses |corr|, so a contrast-inverted pair is still located and
    is flagged by `result.stats.polarity == -1` instead of silently failing.
    """
    corr = correlation_surface(ref, mov, window=window, beta=beta,
                               spectral_mask=spectral_mask)
    py, px = np.unravel_index(np.argmax(np.abs(corr)), corr.shape)
    sy, sx = SUBPIXEL[subpixel](corr, py, px)
    dy, dx = unwrap_peak(py + sy, px + sx, corr.shape)
    return TranslationResult(dy=dy, dx=dx, stats=peak_metrics(corr),
                             corr=corr if keep_corr else None)


def phase_correlation_pyramid(ref, mov, levels=2, **kwargs):
    """Coarse-to-fine search, for shifts beyond about 40% of the frame.

    Verified: recovers dy = 40, 90 and 120 px on a 256 px frame, agreeing with
    the full-resolution estimate to 0.02 px.
    """
    from .transform import fourier_shift

    if levels <= 0:
        return phase_correlation(ref, mov, **kwargs)
    coarse = phase_correlation_pyramid(downsample2(ref), downsample2(mov),
                                       levels - 1, **kwargs)
    gy, gx = 2.0 * coarse.dy, 2.0 * coarse.dx
    fine = phase_correlation(ref, fourier_shift(mov, -gy, -gx), **kwargs)
    return TranslationResult(dy=gy + fine.dy, dx=gx + fine.dx,
                             stats=fine.stats, corr=fine.corr)


def second_peak(corr, exclude=8):
    """Location and height of the strongest peak that is NOT the main one.

    With two independently moving regions, phase correlation produces one peak
    per motion (linearity of the transform), so this returns the secondary
    motion directly. Verified: recovers an object displacement exactly for
    objects up to 26% of the frame area.

    The result is modulo (H, W) like any DFT shift, so a secondary motion larger
    than half a dimension comes back as its negative complement -- on a 256 px
    axis, +130 and -126 are the same point and cannot be told apart.
    """
    H, W = corr.shape
    py, px = np.unravel_index(np.argmax(np.abs(corr)), corr.shape)
    c = np.roll(corr, (H // 2 - py, W // 2 - px), axis=(0, 1))
    cy, cx = H // 2, W // 2
    c = c.copy()
    c[cy - exclude:cy + exclude + 1, cx - exclude:cx + exclude + 1] = -np.inf
    qy, qx = np.unravel_index(np.argmax(c), c.shape)
    dy0, dx0 = unwrap_peak(py, px, corr.shape)
    return (dy0 + (qy - cy), dx0 + (qx - cx), float(c[qy, qx]))
