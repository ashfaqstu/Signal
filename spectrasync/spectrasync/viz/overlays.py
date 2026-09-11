"""Overlay images that make an alignment result visible. Each answers a
different question, so build all of them and let the UI switch."""

from __future__ import annotations

import numpy as np

from ..core.preprocess import to_unit
from ..registry import Registry

OVERLAYS = Registry("overlay")


@OVERLAYS.register("anaglyph", doc="ref -> red, mov -> cyan. Grey means aligned.")
def anaglyph(ref, mov):
    r, m = to_unit(ref), to_unit(mov)
    return np.dstack([r, m, m])


@OVERLAYS.register("checkerboard", doc="Alternating tiles. Broken lines = misaligned.")
def checkerboard(ref, mov, tile=32):
    r, m = to_unit(ref), to_unit(mov)
    H, W = r.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W]
    return np.where(((yy // tile) + (xx // tile)) % 2 == 0, r, m)


@OVERLAYS.register("difference", doc="|ref - mov|. Collapses toward black when aligned.")
def difference(ref, mov):
    return np.abs(to_unit(ref) - to_unit(mov))


@OVERLAYS.register("blend", doc="Straight alpha blend.")
def blend(ref, mov, alpha=0.5):
    return (1.0 - alpha) * to_unit(ref) + alpha * to_unit(mov)


@OVERLAYS.register("split", doc="Left half from ref, right half from mov.")
def split(ref, mov, frac=0.5):
    r, m = to_unit(ref), to_unit(mov)
    W = r.shape[1]
    cut = int(W * frac)
    out = m.copy()
    out[:, :cut] = r[:, :cut]
    return out


def tint(gray, rgb=(0.65, 0.19, 0.12), base=None):
    """Colourise a mask or scalar map over an optional grayscale base."""
    g = np.clip(np.asarray(gray, dtype=np.float64), 0.0, 1.0)
    if base is None:
        return np.dstack([g * c for c in rgb])
    b = to_unit(base)
    if b.ndim == 2:
        b = np.dstack([b, b, b])
    a = g[..., None]
    return b * (1 - a) + np.array(rgb)[None, None, :] * a
