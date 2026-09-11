"""Shared fixtures. Every test knows the right answer before it runs."""

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PHOTO = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "data", "raw", "photo_a.jpg")


@pytest.fixture(scope="session")
def rng():
    return np.random.default_rng(0)


@pytest.fixture(scope="session")
def textured():
    """A synthetic scene with broadband content: the default test image."""
    r = np.random.default_rng(0)
    H, W = 256, 320
    yy, xx = np.mgrid[0:H, 0:W]
    a = (np.sin(xx / 7.0) * np.cos(yy / 11.0)
         + 0.5 * np.sin((xx + yy) / 23.0)
         + r.normal(0, 0.3, (H, W)))
    return (a - a.min()) / (a.max() - a.min())


@pytest.fixture(scope="session")
def square():
    """A square, even-sized scene -- required by the log-polar stage."""
    r = np.random.default_rng(1)
    S = 256
    yy, xx = np.mgrid[0:S, 0:S].astype(float)
    a = (0.5 + 0.22 * np.sin(xx / 9.0) * np.cos(yy / 12.0)
         + 0.20 * np.exp(-(((xx - 90) ** 2 + (yy - 160) ** 2) / (2 * 35.0 ** 2)))
         + 0.18 * np.exp(-(((xx - 170) ** 2 + (yy - 80) ** 2) / (2 * 22.0 ** 2)))
         + 0.12 * (np.abs(xx - yy) < 6).astype(float)
         + r.normal(0, 0.02, (S, S)))
    return np.clip(a, 0, 1)


@pytest.fixture(scope="session")
def stackable():
    """A BROADBAND image for the stacking tests.

    The `square` fixture is deliberately smooth, and at noise sigma 0.12 phase
    correlation genuinely cannot register it -- measured 25-37 failures in 60
    trials, with the peak ratio correctly reporting ~1.07 ("no lock"). Real
    photographic content failed 0/60 under the same noise. Stacking accuracy
    must therefore be measured on textured content; see
    test_low_texture_is_reported_not_silently_wrong for the other half.
    """
    path = os.path.join(os.path.dirname(PHOTO), "photo_b.jpg")
    if not os.path.exists(path):
        pytest.skip("no textured sample photo in data/raw/")
    from spectrasync.io import load_gray
    return load_gray(path, max_side=512)[:256, :256]


@pytest.fixture(scope="session")
def photo():
    """A real photograph, if one is present. Tests using it skip otherwise."""
    if not os.path.exists(PHOTO):
        pytest.skip("no sample photo in data/raw/")
    from spectrasync.io import load_gray
    return load_gray(PHOTO, max_side=640)


@pytest.fixture(scope="session")
def interior():
    """Mask factory: the region unaffected by border wrap."""
    def _make(shape, margin=45):
        m = np.zeros(shape[:2], dtype=bool)
        m[margin:-margin, margin:-margin] = True
        return m
    return _make
