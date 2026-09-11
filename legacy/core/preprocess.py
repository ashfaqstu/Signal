"""Preprocessing applied before the FFT.

Milestone M5 in docs/02-CORE-IMPLEMENTATION.md, theory in
docs/01-THEORY.md section 11 (windowing).

Honest finding from the docs: on our own synthetic sweeps windowed and
unwindowed runs were equally exact. Windowing is INSURANCE -- it pays off
when the periodic extension has a violent discontinuity (bright sky over
dark ground at the frame edge, vignette, scanned border, tiny image).
Keep it a parameter, A/B it on your own photos, report what you measured.
"""

import numpy as np


def remove_mean(a):
    """Subtract the DC component.

    The mean carries no shift information (it lives in bin (0, 0), whose
    phase is always 0) and it swamps the correlation peak if left in.
    phase_correlation() does this internally -- this helper exists for the
    diagnostic figures.

    Returns
    -------
    ndarray, same shape as `a`, float64, with mean ~0. A new array; `a` is
    not modified in place.
    """
    raise NotImplementedError


def normalise(a):
    """Zero mean, unit variance.

    Cosmetic for phase correlation -- the magnitude normalisation in the
    cross-power spectrum already removes gain. Useful for the plain
    cross-correlation comparison figure (beta = 0).

    Returns
    -------
    ndarray, same shape as `a`, float64, mean ~0 and std ~1. When the input
    is flat (std < 1e-12) return the mean-removed array UNCHANGED rather
    than dividing by zero.
    """
    raise NotImplementedError


def hann2d(H, W):
    """Separable 2-D Hann window.

    Built as the outer product of two 1-D Hann windows: np.outer(hann_H, hann_W).
    It tapers the borders to zero so the image's periodic extension has no
    step discontinuity, which would otherwise splash a cross of energy
    through the whole spectrum.

    Returns
    -------
    ndarray, shape (H, W), float64, values in [0, 1], zero on the border and
    1.0 at the centre. Multiply an image by it elementwise.
    """
    raise NotImplementedError


def downsample2(a):
    """2x box decimation: average each 2x2 block into one pixel.

    Gives you a coarse-to-fine (pyramid) search almost for free: estimate on
    the half-size pair, double the answer, shift, then refine at full size.
    Extends the usable shift range and speeds up large images.

    Trick: trim to even H, W then reshape to (H//2, 2, W//2, 2) and take
    mean over axes (1, 3).

    Returns
    -------
    ndarray, shape (H//2, W//2), float64. A shift of (dy, dx) in the original
    becomes (dy/2, dx/2) here -- remember to double the estimate coming back.
    """
    raise NotImplementedError


def add_noise(a, sigma, rng=None):
    """Additive Gaussian noise -- for the robustness demo and the beta sweep.

    Used to reproduce the measured table in docs/02: at sigma 0.25 the
    optimum beta sat at 0.8, not 1.0.

    Parameters
    ----------
    rng : np.random.Generator or None. Pass one (e.g. default_rng(0)) so the
          report's numbers are reproducible.

    Returns
    -------
    ndarray, same shape as `a`, float64. Do NOT clip to [0, 1] -- clipping
    is a nonlinearity and would quietly change what you are measuring.
    """
    raise NotImplementedError
