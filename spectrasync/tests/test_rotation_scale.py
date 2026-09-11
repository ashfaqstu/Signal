"""func_rotation_and_scale -- Fourier-Mellin, and the registration facade."""

import numpy as np
import pytest

from spectrasync import (alignment_valid_mask, estimate_rotation_scale, ncc,
                         register_pair, register_similarity, warp_similarity)


@pytest.mark.parametrize("angle", [-40, -25, -12, -5, 0, 5, 12, 25, 40])
def test_rotation_accuracy(square, angle):
    mov = warp_similarity(square, angle, 1.0)
    r = estimate_rotation_scale(square, mov)
    assert abs(r.angle_deg - angle) < 0.2


@pytest.mark.parametrize("scale", [0.75, 0.85, 1.0, 1.15, 1.4, 1.8])
def test_scale_accuracy(square, scale):
    mov = warp_similarity(square, 0.0, scale)
    r = estimate_rotation_scale(square, mov)
    assert abs(r.scale - scale) / scale < 0.02


def test_scale_is_inverted_relative_to_the_spectrum(square):
    """Magnifying an image SHRINKS its magnitude spectrum, so the log-radius
    shift carries -log(s). If this ever inverts, every scale comes back as 1/s."""
    r = estimate_rotation_scale(square, warp_similarity(square, 0.0, 1.25))
    assert r.scale > 1.0


def test_translation_does_not_disturb_the_estimate(square):
    """The magnitude spectrum is shift-invariant: that is the entire point."""
    from spectrasync import fourier_shift
    mov = fourier_shift(warp_similarity(square, 15.0, 1.1), 11, -7)
    r = estimate_rotation_scale(square, mov)
    assert abs(r.angle_deg - 15.0) < 0.5
    assert abs(r.scale - 1.1) / 1.1 < 0.03


@pytest.mark.parametrize("angle,scale", [(0, 1.0), (7, 1.10), (-20, 0.90),
                                         (30, 1.30), (-33, 0.80), (150, 1.0)])
def test_full_registration(square, angle, scale, interior):
    mov = warp_similarity(square, angle, scale, 9, -14)
    r = register_similarity(square, mov)
    m = alignment_valid_mask(square.shape, r.angle_deg, r.scale, r.dy, r.dx)
    assert m.mean() > 0.3
    assert ncc(square, r.aligned, m) > 0.95


def test_180_degree_ambiguity_is_resolved(square):
    """The magnitude spectrum is centrosymmetric, so Fourier-Mellin alone only
    knows the angle mod 180. The facade must pick the right one."""
    r = register_similarity(square, warp_similarity(square, 150.0, 1.0))
    assert abs(((r.angle_deg - 150.0 + 180) % 360) - 180) < 1.0


def test_auto_mode_prefers_translation_when_that_is_enough(square):
    from spectrasync import fourier_shift
    r = register_pair(square, fourier_shift(square, 12, -9), mode="auto")
    assert r.is_translation_only
    assert abs(r.dy - 12) < 0.1 and abs(r.dx + 9) < 0.1


def test_registration_on_a_real_photo(photo):
    from spectrasync import centre_crop
    base = centre_crop(photo, 0.6)
    n = min(base.shape) // 2 * 2
    base = base[:n, :n]
    for angle, scale in [(7, 1.0), (20, 1.20), (-30, 0.85)]:
        mov = warp_similarity(base, angle, scale)
        r = register_similarity(base, mov)
        m = alignment_valid_mask(base.shape, r.angle_deg, r.scale, r.dy, r.dx)
        assert abs(r.angle_deg - angle) < 0.5
        assert abs(r.scale - scale) / scale < 0.02
        assert ncc(base, r.aligned, m) > 0.95
