"""Image I/O and synthetic test-pair generation.

Milestones M1 and M2 in docs/02-CORE-IMPLEMENTATION.md.

Rule: Pillow is used ONLY to decode/encode files. Every mathematical
operation in this project is numpy written by us.
"""

import numpy as np
from PIL import Image


# ---------------------------------------------------------------------------
# M1 -- loading and saving
# ---------------------------------------------------------------------------

def load_gray(path):
    """Load any image file as float64 grayscale in [0, 1].

    This is the array every estimation function expects.
    Steps: open with Pillow -> convert to RGB -> asarray float64 -> /255 -> to_gray.

    Returns
    -------
    ndarray, shape (H, W), dtype float64, values in [0, 1]

    Acceptance test (M1): dtype is float64, ndim == 2, min >= 0, max <= 1.
    """
    raise NotImplementedError


def load_rgb(path):
    """Load as float64 RGB. FOR DISPLAY ONLY.

    The shift is one number pair for the whole image, so estimation always
    runs on the grayscale version -- never on three channels separately.

    Returns
    -------
    ndarray, shape (H, W, 3), dtype float64, values in [0, 1]
    """
    raise NotImplementedError


def to_gray(rgb):
    """Rec.709 luma: 0.2126*R + 0.7152*G + 0.0722*B.

    Perceptually weighted, unlike a plain mean(axis=2). Edges keep their
    contrast, so the correlation peak comes out slightly sharper.
    Hint: a matrix product `rgb @ weights` collapses the last axis for you.

    Parameters
    ----------
    rgb : ndarray, shape (H, W, 3), float

    Returns
    -------
    ndarray, shape (H, W), float64 -- one channel, same value range as the input
    """
    raise NotImplementedError


def save_png(path, arr):
    """Write a float array in [0, 1] out as an 8-bit PNG.

    Steps: clip to [0, 1] -> multiply by 255 -> round -> uint8 -> Image.save.
    Works for both (H, W) grayscale and (H, W, 3) RGB.

    Returns
    -------
    None -- called for its side effect, the file written at `path`.
    """
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Shape helpers -- needed constantly once real photographs arrive
# ---------------------------------------------------------------------------

def match_shapes(a, b):
    """Crop both arrays to their common top-left overlap.

    phase_correlation() requires identical shapes; two photos off a camera
    usually already match, but crops and video frames may not.

    Returns
    -------
    (a_cropped, b_cropped) : tuple of two ndarrays, both shape
        (min(Ha, Hb), min(Wa, Wb)). Views into the originals, not copies.
    """
    raise NotImplementedError


def to_even(a):
    """Trim to even height and width.

    The FFT is faster on even sizes and the wraparound unwrapping maths
    (dy > H/2  =>  dy -= H) is cleaner when H and W are even.

    Returns
    -------
    ndarray, shape (H - H%2, W - W%2) -- a view, at most one row and one
    column smaller than the input.
    """
    raise NotImplementedError


# ---------------------------------------------------------------------------
# M2 -- test pairs WITH KNOWN GROUND TRUTH (build these before the estimator)
# ---------------------------------------------------------------------------

def make_circular_pair(img, dy, dx):
    """Exactly circular shift -- the pair for which the DFT model is EXACT.

    An unwindowed estimator must return (dy, dx) with ZERO error on this
    pair. Used by the 200-shift test in tests/test_shift_recovery.py.

    Careful: np.roll(img, (dy, dx), axis=(0, 1)) already matches our
    convention mov[y, x] = ref[y - dy, x - dx].

    Returns
    -------
    (ref, mov) : tuple of two ndarrays, both shape (H, W), same dtype as
        `img`. `ref` is `img` unchanged; `mov` is the rolled copy.
    """
    raise NotImplementedError


def make_crop_pair(big, dy, dx, size):
    """Realistic translation: two overlapping windows cut out of one large image.

    New content enters at the edges, exactly like a real camera slide -- this
    is the missing rung between the synthetic circular pair and wild data.

    `mov` is sampled from a window starting dy rows EARLIER in `big`, so the
    content inside mov appears dy rows LOWER than in ref. That is
    mov[y, x] = ref[y - dy, x - dx]. Verify this sign yourself.

    Parameters
    ----------
    big  : ndarray (H_big, W_big), must be larger than `size` by at least
           the shift plus the anchor offset
    size : (H, W) of the crops to cut

    Returns
    -------
    (ref, mov) : tuple of two ndarrays, both exactly `size`, both .copy()
        so later in-place work cannot corrupt `big`.
    """
    raise NotImplementedError


def write_manifest(path, entries):
    """Record every generated pair and its true shift as JSON.

    The report needs an error table (true shift vs estimated shift vs error)
    and you will not remember these numbers later. Target:
    data/synthetic/manifest.json

    Parameters
    ----------
    entries : list of dicts, e.g.
        {"ref": "...png", "mov": "...png", "dy": 7, "dx": -11, "kind": "circular"}

    Returns
    -------
    None -- writes the JSON file at `path`.
    """
    raise NotImplementedError
