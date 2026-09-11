"""Small array helpers used before any transform. All pure, all reusable."""

from __future__ import annotations

import numpy as np


def as_float(a):
    """float64 view of any input. uint8 arithmetic silently wraps -- never
    let an integer array reach an FFT."""
    a = np.asarray(a)
    if a.dtype == np.uint8:
        return a.astype(np.float64) / 255.0
    return a.astype(np.float64, copy=False)


def remove_mean(a):
    """Drop the DC term. It carries no shift information and is usually orders
    of magnitude larger than everything else."""
    a = as_float(a)
    return a - a.mean()


def normalise(a):
    """Zero mean, unit variance."""
    a = remove_mean(a)
    s = a.std()
    return a / s if s > 1e-12 else a


def to_unit(a):
    """Rescale to [0, 1] using the 1st/99th percentile, for display only."""
    a = as_float(a)
    lo, hi = np.percentile(a, [1, 99])
    return np.clip((a - lo) / (hi - lo + 1e-12), 0.0, 1.0)


def match_shapes(*arrays):
    """Crop every input to the common top-left overlap."""
    h = min(a.shape[0] for a in arrays)
    w = min(a.shape[1] for a in arrays)
    return tuple(a[:h, :w] for a in arrays)


def to_even(a):
    """Trim to even dimensions: faster FFTs and simpler wraparound maths."""
    return a[:a.shape[0] - a.shape[0] % 2, :a.shape[1] - a.shape[1] % 2]


def downsample2(a):
    """2x box decimation. The coarse level of a coarse-to-fine search."""
    a = as_float(a)
    H = a.shape[0] // 2 * 2
    W = a.shape[1] // 2 * 2
    return a[:H, :W].reshape(H // 2, 2, W // 2, 2).mean(axis=(1, 3))


def upsample2(a):
    """Nearest-neighbour 2x, the partner of downsample2."""
    return np.repeat(np.repeat(as_float(a), 2, axis=0), 2, axis=1)


def add_noise(a, sigma, rng=None):
    """Additive white Gaussian noise, clipped to [0, 1]. For demos and tests."""
    rng = rng or np.random.default_rng()
    return np.clip(as_float(a) + rng.normal(0.0, sigma, np.shape(a)), 0.0, 1.0)


def pad_to(a, shape):
    """Zero-pad (after mean removal) into a larger canvas, top-left anchored.
    This is how images of different sizes are compared."""
    out = np.zeros(shape, dtype=np.float64)
    a = remove_mean(a)
    out[:a.shape[0], :a.shape[1]] = a
    return out


def common_canvas(a, b):
    """Pad both inputs into one shape big enough for either."""
    shape = (max(a.shape[0], b.shape[0]), max(a.shape[1], b.shape[1]))
    return pad_to(a, shape), pad_to(b, shape)
