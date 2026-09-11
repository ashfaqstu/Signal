"""The three applied features, plus the filters they are built from."""

import numpy as np
import pytest

from spectrasync import (Pipeline, REDUCERS, align_frames, apply_filter, bandpass,
                         compare_temporal_filters, fourier_gradient,
                         fourier_shift, highlight, lowpass, ncc, psnr,
                         reduce, remove_moving_objects, stack,
                         theoretical_gain_db, SyntheticSource, moving_disc)


def _truth_in_reference_frame(base, src):
    """The stack is aligned onto frame 0, which is itself shifted, so ground
    truth must be expressed in FRAME 0's coordinates. Comparing against the
    unshifted original instead reads ~8 dB low -- a real trap."""
    t0 = src.truth[0]
    return fourier_shift(base, t0["dy"], t0["dx"])


@pytest.mark.parametrize("n", [4, 8, 16])
def test_mean_stacking_matches_theory(stackable, interior, n):
    src = SyntheticSource(stackable, n=n, max_shift=5.0, noise=0.12, seed=1)
    frames = src.frames()
    truth = _truth_in_reference_frame(stackable, src)
    m = interior(stackable.shape)
    res = stack(frames, reducer="mean")
    gain = psnr(truth, res.output, m) - psnr(truth, frames[0], m)
    assert abs(gain - theoretical_gain_db(n, "mean")) < 1.5


def test_median_is_worse_than_mean_on_pure_noise(stackable, interior):
    """var(median) -> (pi/2) var(mean), i.e. about 1.96 dB worse. The spec picks
    median anyway, for the outlier rejection tested below."""
    src = SyntheticSource(stackable, n=16, max_shift=5.0, noise=0.12, seed=1)
    frames = src.frames()
    truth = _truth_in_reference_frame(stackable, src)
    m = interior(stackable.shape)
    mean_p = psnr(truth, stack(frames, reducer="mean").output, m)
    med_p = psnr(truth, stack(frames, reducer="median").output, m)
    assert mean_p > med_p
    assert 0.5 < (mean_p - med_p) < 3.5


def test_sigma_clip_recovers_mean_performance(stackable, interior):
    src = SyntheticSource(stackable, n=16, max_shift=5.0, noise=0.12, seed=1)
    frames = src.frames()
    truth = _truth_in_reference_frame(stackable, src)
    m = interior(stackable.shape)
    mean_p = psnr(truth, stack(frames, reducer="mean").output, m)
    clip_p = psnr(truth, stack(frames, reducer="sigma_clip").output, m)
    assert clip_p > mean_p - 0.5


def test_object_removal(square, interior):
    src = SyntheticSource(square, n=12, max_shift=4.0, noise=0.01,
                          mover=moving_disc(radius=26, value=0.03), seed=2)
    frames = src.frames()
    truth = _truth_in_reference_frame(square, src)
    m = interior(square.shape)
    res = remove_moving_objects(frames, reducer="median")
    occ = (np.abs(res.aligned[0] - truth) > 0.15) & m
    assert occ.sum() > 100, "the test object should actually be present"
    assert psnr(truth, res.output, occ) - psnr(truth, res.aligned[0], occ) > 15


def test_no_lti_filter_can_remove_the_object(square, interior):
    """mean and temporal low-pass are both LTI and must both ghost; the median
    is nonlinear and must win by a wide margin."""
    src = SyntheticSource(square, n=12, max_shift=4.0, noise=0.01,
                          mover=moving_disc(radius=26, value=0.03), seed=2)
    frames = src.frames()
    truth = _truth_in_reference_frame(square, src)
    m = interior(square.shape)
    res = remove_moving_objects(frames)
    out = compare_temporal_filters(res.aligned)
    med = psnr(truth, out["median (nonlinear)"], m)
    for name in ("mean (linear, LTI)", "temporal low-pass (linear, LTI)"):
        assert med > psnr(truth, out[name], m) + 5.0


def test_highlight_locates_the_object(square):
    src = SyntheticSource(square, n=12, max_shift=3.0, noise=0.01,
                          mover=moving_disc(radius=26, value=0.03), seed=3)
    frames = src.frames()
    res = remove_moving_objects(frames)
    det = highlight(res.aligned[6], res.output, detector="bandpass", k=3.0)
    assert det.boxes, "no blob detected"
    y0, x0, y1, x1 = det.boxes[0]
    H, W = square.shape
    t = 6 / 11.0
    cy, cx = H * 0.5, W * (0.12 + 0.76 * t)
    assert abs((y0 + y1) / 2 - cy) < 15
    assert abs((x0 + x1) / 2 - cx) < 15


def test_outline_is_hollow(square):
    """The outline must be the BOUNDARY, not the filled mask."""
    from spectrasync import outline_of
    mask = np.zeros((128, 128), bool)
    mask[40:90, 40:90] = True
    line = outline_of(mask)
    assert line[65, 65] == 0.0                 # interior is empty
    assert line[40:90, 38:42].sum() > 0        # the edge is drawn
    assert line.sum() < mask.sum() * 0.6


def test_filters_are_transfer_functions(square):
    lp = lowpass(square.shape, 0.05)
    assert 0.99 < lp.max() <= 1.0 and lp.min() >= 0.0
    smooth = apply_filter(square, lp)
    assert smooth.std() < square.std()
    bp = bandpass(square.shape, 0.02, 0.2)
    assert bp[0, 0] < 0.1                      # DC is rejected


def test_fourier_gradient_matches_finite_differences():
    y, x = np.mgrid[0:64, 0:64].astype(float)
    img = np.sin(2 * np.pi * x / 64.0)         # band-limited: exact for the DFT
    gy, gx = fourier_gradient(img)
    expected = (2 * np.pi / 64.0) * np.cos(2 * np.pi * x / 64.0)
    assert np.abs(gx - expected).max() < 1e-9
    assert np.abs(gy).max() < 1e-9


def test_every_reducer_runs(square):
    frames = [square + 0.01 * i for i in range(5)]
    for name in REDUCERS.names():
        out = reduce(frames, name)
        assert out.shape == square.shape
        assert np.isfinite(out).all()


def test_pipeline_composes_and_traces(square):
    src = SyntheticSource(square, n=6, max_shift=3.0, noise=0.08, seed=4)
    p = Pipeline("t").then("align").then("reduce", method="median")
    out = p.run(src.frames())
    assert out.value.shape == square.shape
    assert out.steps() == ["align", "reduce"]
    assert len(out["align"]) == 6


def test_low_texture_is_reported_not_silently_wrong(square):
    """A near-textureless image at sigma 0.12 cannot be registered. The point is
    that the estimator SAYS so (ratio ~1.1, "no lock") instead of returning a
    confident wrong answer -- and that confidence gating then keeps the bad
    frame from poisoning the stack."""
    from spectrasync import phase_correlation, add_noise
    noisy_ref = add_noise(square, 0.12)
    noisy_mov = add_noise(fourier_shift(square, 3.0, -4.0), 0.12)
    r = phase_correlation(noisy_ref, noisy_mov)
    assert r.stats.ratio < 2.0
    assert r.stats.verdict in ("marginal", "no lock")

    # Honest limit of the gate: on this image the spurious peaks score a peak
    # ratio of 3-5, ABOVE any sane threshold, so confidence gating catches the
    # flat-surface failures but NOT these. The estimate is simply wrong, and it
    # is wrong by a consistent amount, which is what a spurious lock looks like.
    src = SyntheticSource(square, n=8, max_shift=5.0, noise=0.12, seed=1)
    frames = src.frames()
    _, results = align_frames(frames)
    errs = [max(abs(r.dy - (t["dy"] - src.truth[0]["dy"])),
                abs(r.dx - (t["dx"] - src.truth[0]["dx"])))
            for r, t in zip(results[1:], src.truth[1:])]
    assert max(errs) > 1.0, "expected this pathological case to fail"
