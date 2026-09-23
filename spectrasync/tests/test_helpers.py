"""Small pure functions pulled out of the UI pages during the backend/frontend
split, so the maths is unit-tested instead of only exercised through Streamlit.
"""

import numpy as np
import pytest

from spectrasync import (align_reference_to_output, angle_error_deg,
                         border_mask, centre_square, describe_similarity,
                         even_square, mask_from_box, most_disturbed_pixel,
                         ncc, percent_error, phase_swap)


def test_angle_error_deg_wraps_at_180():
    assert angle_error_deg(179.0, -179.0) == pytest.approx(2.0)
    assert angle_error_deg(10.0, 5.0) == pytest.approx(5.0)
    assert angle_error_deg(-170.0, 170.0) == pytest.approx(20.0)


def test_percent_error_basic():
    assert percent_error(1.10, 1.00) == pytest.approx(10.0)
    assert percent_error(0.90, 1.00) == pytest.approx(10.0)
    assert percent_error(5.0, 5.0) == 0.0


def test_describe_similarity_reads_as_a_sentence():
    assert "no measurable rotation" in describe_similarity(0.01, 1.0)
    assert "the same size" in describe_similarity(0.01, 1.0)
    text = describe_similarity(12.0, 1.2)
    assert "12.00" in text and "clockwise" in text and "20.0%" in text
    assert "larger" in text
    assert "counter-clockwise" in describe_similarity(-8.0, 0.9)
    assert "smaller" in describe_similarity(-8.0, 0.9)


def test_border_mask_shape_and_margin():
    m = border_mask((10, 20), 3)
    assert m.shape == (10, 20)
    assert m[3:7, 3:17].all()
    assert not m[0, 0] and not m[9, 19]
    # a zero margin is the identity mask -- the "Photo set" default in the UI
    assert border_mask((10, 20), 0).all()


def test_mask_from_box_matches_the_box():
    m = mask_from_box((8, 8), (2, 5, 1, 6))
    assert m.sum() == (5 - 2) * (6 - 1)
    assert m[2:5, 1:6].all()
    assert not m[0, 0]


def test_most_disturbed_pixel_finds_the_outlier(square):
    plate = square.copy()
    frames = [square.copy() for _ in range(5)]
    frames[2][40, 60] += 0.5          # one frame, one pixel, a clear spike
    y, x = most_disturbed_pixel(frames, plate)
    assert (y, x) == (40, 60)


def test_most_disturbed_pixel_honours_the_mask(square):
    plate = square.copy()
    frames = [square.copy() for _ in range(5)]
    frames[2][5, 5] += 0.9            # the biggest spike, but outside the mask
    frames[3][40, 60] += 0.3          # a smaller spike, inside the mask
    mask = np.zeros(square.shape, bool)
    mask[30:50, 50:70] = True
    y, x = most_disturbed_pixel(frames, plate, mask=mask)
    assert (y, x) == (40, 60)


def test_align_reference_to_output_recovers_a_known_shift(stackable):
    from spectrasync import fourier_shift

    output = stackable
    reference = fourier_shift(stackable, -6.0, 4.0)   # captured independently
    aligned, mask = align_reference_to_output(output, reference)
    assert aligned.shape == output.shape
    assert mask.dtype == bool and mask.any()
    # after alignment the two should agree well inside the valid region
    diff = np.abs(aligned - output)[mask]
    assert diff.mean() < 0.02


def test_align_reference_to_output_intersects_the_given_valid_mask(stackable):
    valid = np.zeros(stackable.shape, bool)
    valid[10:20, 10:20] = True
    _, mask = align_reference_to_output(stackable, stackable, valid=valid)
    assert (mask | ~valid).all()      # mask is a SUBSET of the given valid region


def test_centre_square_crops_the_largest_even_square():
    a = np.zeros((51, 80))
    out = centre_square(a)
    assert out.shape == (50, 50)
    assert out.shape[0] % 2 == 0 and out.shape[1] % 2 == 0


def test_even_square_downscales_before_cropping():
    a = np.zeros((300, 600))          # short side 300, well over max_side
    out = even_square(a, max_side=100)
    assert out.shape == (100, 100)


def test_phase_swap_looks_like_the_phase_source():
    """The classic demonstration that structure lives in the phase: swap
    magnitude and phase between two broadband images and the result must
    resemble the PHASE source far more than the magnitude source."""
    rng = np.random.default_rng(0)
    a = rng.random((64, 64))
    b = rng.random((64, 64))
    out = phase_swap(magnitude_of=a, phase_of=b)
    assert ncc(out, b) > ncc(out, a) + 0.3
