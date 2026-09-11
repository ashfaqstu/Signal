"""Window functions, as a registry.

The DFT is the Fourier series of the PERIODIC EXTENSION of the image, so the
right edge butts against the left edge and the resulting step is broadband.
A window that decays to zero at the border makes that extension continuous.

See legacy/docs/01-THEORY.md section 11 -- including the gotcha that windowing
HURTS on an exactly circular (np.roll) test pair, because the window is fixed in
the frame and does not travel with the content.
"""

from __future__ import annotations

import numpy as np

from ..registry import Registry

WINDOWS = Registry("window")

WINDOWS.add("hann", np.hanning, "Raised cosine. Zero at the edges. The default.")
WINDOWS.add("hamming", np.hamming, "Like Hann but does not reach zero at the edges.")
WINDOWS.add("blackman", np.blackman, "Wider main lobe, much lower sidelobes.")
WINDOWS.add("bartlett", np.bartlett, "Triangular. Cheapest useful taper.")


@WINDOWS.register("none", doc="No taper. Correct for exactly circular test pairs.")
def _no_window(n):
    return np.ones(n)


@WINDOWS.register("tukey", doc="Flat centre with cosine skirts (alpha = 0.5).")
def _tukey(n, alpha=0.5):
    if alpha <= 0:
        return np.ones(n)
    w = np.ones(n)
    edge = int(np.floor(alpha * (n - 1) / 2.0))
    if edge < 1:
        return w
    t = np.arange(edge + 1)
    ramp = 0.5 * (1 + np.cos(np.pi * (2 * t / (alpha * (n - 1)) - 1)))
    w[:edge + 1] = ramp
    w[-(edge + 1):] = ramp[::-1]
    return w


def window2d(shape, name="hann"):
    """Separable 2-D window of the given shape: outer(w(H), w(W))."""
    H, W = shape[0], shape[1]
    fn = WINDOWS[name]
    return np.outer(fn(H), fn(W))
