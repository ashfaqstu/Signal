"""Sub-pixel peak refiners, as a registry.

For a fractional shift the correlation surface is not a single spike but a
Dirichlet kernel centred on the true shift, so the samples either side of the
peak carry the fraction. Each refiner reads it out differently.

Measured on the parabolic refiner over 50 random fractional shifts:
mean error 0.08 px, worst case 0.12 px.
"""

from __future__ import annotations

import numpy as np

from ..registry import Registry

SUBPIXEL = Registry("subpixel refiner")


@SUBPIXEL.register("none", doc="Integer peak only.")
def _none(corr, py, px):
    return 0.0, 0.0


@SUBPIXEL.register("parabolic", doc="Quadratic fit through 3 samples per axis. Default.")
def _parabolic(corr, py, px):
    H, W = corr.shape
    c0 = corr[py, px]

    def axis(cm, cp):
        den = cm + cp - 2.0 * c0
        if abs(den) < 1e-15:
            return 0.0
        return float(np.clip((cm - cp) / (2.0 * den), -0.5, 0.5))

    dy = axis(corr[(py - 1) % H, px], corr[(py + 1) % H, px])
    dx = axis(corr[py, (px - 1) % W], corr[py, (px + 1) % W])
    return dy, dx


@SUBPIXEL.register("centroid", doc="Amplitude-weighted centre of mass over a 5x5 patch.")
def _centroid(corr, py, px, r=2):
    H, W = corr.shape
    ys = [(py + i) % H for i in range(-r, r + 1)]
    xs = [(px + j) % W for j in range(-r, r + 1)]
    patch = np.clip(corr[np.ix_(ys, xs)], 0.0, None)
    total = patch.sum()
    if total <= 0:
        return 0.0, 0.0
    u = np.arange(-r, r + 1)
    dy = float((patch.sum(axis=1) * u).sum() / total)
    dx = float((patch.sum(axis=0) * u).sum() / total)
    return float(np.clip(dy, -r, r)), float(np.clip(dx, -r, r))


@SUBPIXEL.register("gaussian",
                   doc="Log-parabolic fit. Needs a POSITIVE peak -- see the note.")
def _gaussian(corr, py, px):
    """Exact for a genuinely Gaussian peak, but it needs all three samples to be
    positive, and a PHASE-correlation peak sits on a near-zero floor with
    negative sidelobes (measured: peak 0.739, neighbours 0.315 and -0.172).
    It therefore degenerates to the integer answer here -- measured median error
    0.412 px, identical to "none", versus 0.096 px for "parabolic".

    Keep it for surfaces that are positive by construction: plain
    cross-correlation (beta = 0) or the log-polar magnitude correlation.
    """
    H, W = corr.shape
    eps = 1e-12

    def axis(cm, c0, cp):
        if cm <= 0 or c0 <= 0 or cp <= 0:
            return 0.0
        lm, l0, lp = np.log(cm + eps), np.log(c0 + eps), np.log(cp + eps)
        den = lm + lp - 2.0 * l0
        if abs(den) < 1e-15:
            return 0.0
        return float(np.clip((lm - lp) / (2.0 * den), -0.5, 0.5))

    c0 = corr[py, px]
    dy = axis(corr[(py - 1) % H, px], c0, corr[(py + 1) % H, px])
    dx = axis(corr[py, (px - 1) % W], c0, corr[py, (px + 1) % W])
    return dy, dx
