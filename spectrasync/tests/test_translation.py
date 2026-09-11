"""func_translation -- phase correlation.

test_circular_shifts_are_exact is the load-bearing test of the whole project.
The DFT model is EXACT for a circular shift, so with the window off there must
be zero error. If it fails, the sign convention or the unwrapping is wrong and
nothing downstream can be trusted.
"""

import numpy as np
import pytest

from spectrasync import (add_noise, circular_pair, crop_pair, fourier_shift,
                         phase_correlation, phase_correlation_pyramid,
                         second_peak)


def test_circular_shifts_are_exact(textured):
    rng = np.random.default_rng(0)
    for _ in range(200):
        dy, dx = (int(v) for v in rng.integers(-60, 61, size=2))
        _, mov = circular_pair(textured, dy, dx)
        r = phase_correlation(textured, mov, window="none", subpixel="none")
        assert (int(r.dy), int(r.dx)) == (dy, dx)


def test_convention_is_down_and_right(textured):
    """+dy must mean the content moved DOWN, +dx RIGHT."""
    _, mov = circular_pair(textured, 7, -11)
    r = phase_correlation(textured, mov, window="none", subpixel="none")
    assert (r.dy, r.dx) == (7.0, -11.0)


@pytest.mark.parametrize("method", ["parabolic", "centroid"])
def test_subpixel(textured, method):
    rng = np.random.default_rng(1)
    errs = []
    for _ in range(20):
        dy, dx = rng.uniform(-20, 20, 2)
        mov = fourier_shift(textured, dy, dx)
        r = phase_correlation(textured, mov, window="none", subpixel=method)
        errs.append(max(abs(r.dy - dy), abs(r.dx - dx)))
    assert np.median(errs) < 0.35, f"{method}: median error {np.median(errs):.3f} px"


def test_gaussian_refiner_degrades_gracefully(textured):
    """The Gaussian fit needs a positive peak; a phase-correlation peak has
    negative sidelobes, so it must fall back to the integer answer rather than
    return nonsense."""
    mov = fourier_shift(textured, 3.7, -2.3)
    r = phase_correlation(textured, mov, window="none", subpixel="gaussian")
    assert abs(r.dy - 3.7) < 0.6 and abs(r.dx + 2.3) < 0.6


def test_illumination_invariance(textured):
    """Gain and bias change nothing. This is the headline property."""
    _, mov = circular_pair(textured, 13, -21)
    r = phase_correlation(textured, mov * 0.4 + 0.3, window="none", subpixel="none")
    assert (int(r.dy), int(r.dx)) == (13, -21)


def test_noise_robustness(textured):
    _, mov = circular_pair(textured, 9, -14)
    for sigma in (0.05, 0.15, 0.30):
        r = phase_correlation(textured, add_noise(mov, sigma), window="none")
        assert abs(r.dy - 9) < 1 and abs(r.dx + 14) < 1


def test_contrast_inversion_is_detected(textured):
    """An inverted pair still locates, and flags itself via polarity."""
    _, mov = circular_pair(textured, 17, -23)
    r = phase_correlation(textured, 1.0 - mov, window="none", subpixel="none")
    assert (int(r.dy), int(r.dx)) == (17, -23)
    assert r.stats.polarity < 0


def test_unrelated_images_are_rejected(textured):
    rng = np.random.default_rng(2)
    r = phase_correlation(textured, rng.random(textured.shape))
    assert r.stats.ratio < 1.2
    assert r.stats.verdict == "no lock"


def test_real_translation_on_crops(photo):
    for dy, dx in [(17, -23), (-40, 31), (5, 5)]:
        ref, mov = crop_pair(photo, dy, dx, (300, 300))
        r = phase_correlation(ref, mov)
        assert abs(r.dy - dy) < 0.05 and abs(r.dx - dx) < 0.05
        assert r.stats.verdict == "locked"


def test_pyramid_handles_large_shifts(textured):
    for dy in (40, 80):
        _, mov = circular_pair(textured, dy, 0)
        r = phase_correlation_pyramid(textured, mov, levels=1, window="none")
        assert abs(r.dy - dy) < 1.0


def test_second_peak_finds_a_second_motion(square):
    """Two independent motions produce two peaks (linearity of the transform)."""
    def disc(img, cy, cx, r=30):
        yy, xx = np.mgrid[0:img.shape[0], 0:img.shape[1]]
        out = img.copy()
        out[(yy - cy) ** 2 + (xx - cx) ** 2 <= r * r] = 0.05
        return out
    a = disc(square, 120, 70)
    b = disc(square, 100, 170)          # object moved (-20, +100), background still
    r = phase_correlation(a, b, window="none", subpixel="none")
    assert (int(r.dy), int(r.dx)) == (0, 0)             # background dominates
    dy, dx, _ = second_peak(r.corr)
    assert (int(dy), int(dx)) == (-20, 100)
