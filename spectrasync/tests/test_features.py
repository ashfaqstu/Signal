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


def test_mode_picks_the_most_frequent_value_not_the_middle():
    """3 frames at 0.0, 4 at 0.5, 5 at 1.0: the median (the sorted middle
    value) is 0.5, but 1.0 is the most frequent value -- the mode must return
    that instead."""
    vals = [0.0] * 3 + [0.5] * 4 + [1.0] * 5
    frames = [np.array([[v]]) for v in vals]
    assert float(reduce(frames, "median")[0, 0]) == 0.5
    assert float(reduce(frames, "mode")[0, 0]) == 1.0


def test_mode_averages_the_winning_bin_instead_of_snapping_to_its_edge():
    """The output is the MEAN of the real, unquantised samples that share the
    winning 8-bit bin -- not the bin's edge value."""
    vals = [0.502, 0.503, 0.501, 0.10, 0.90]   # the first three share one bin
    frames = [np.array([[v]]) for v in vals]
    out = float(reduce(frames, "mode")[0, 0])
    assert out == pytest.approx(np.mean(vals[:3]), abs=1e-9)


def test_mode_keeps_channels_locked_to_the_same_winning_cluster():
    """Colour frames are binned by LUMA, so every channel must report the
    SAME winning frame subset -- no colour fringing at the boundary."""
    majority, minority = 0.4, 0.9
    gray_frames = ([np.full((6, 6), majority) for _ in range(5)]
                   + [np.full((6, 6), minority) for _ in range(2)])
    rgb_frames = [np.stack([f, 0.5 * f, 1.0 - f], axis=-1) for f in gray_frames]
    out = reduce(rgb_frames, "mode")
    assert np.allclose(out[..., 0], majority)
    assert np.allclose(out[..., 1], 0.5 * majority)
    assert np.allclose(out[..., 2], 1.0 - majority)


def test_mode_is_selectable_for_object_removal(square):
    res = remove_moving_objects([square, square, square], reducer="mode")
    assert res.reducer == "mode"
    assert np.allclose(res.output, square, atol=1e-9)


def test_shorth_beats_median_on_a_near_50_50_split():
    """The bug this guards: with an EVEN sample count, np.median AVERAGES the
    two middle order statistics. An object present in exactly half the frames
    -- or one frame landing on a soft edge right at that boundary -- makes
    plain median blend real background with object content instead of
    rejecting it. `shorth` must reject it instead."""
    # 8 background samples, 7 object samples, plus one in-between stray value
    # sitting exactly at the tie-breaking rank -- this is the real pixel that
    # ghosted in new_image/1 before the fix.
    vals = np.array([0.9102, 0.8901, 0.6812, 0.0710, 0.0710, 0.0710, 0.0710,
                     0.0710, 0.1825, 0.9277, 0.0169, 0.0169, 0.0169, 0.8980,
                     0.8761, 0.8624])
    frames = [np.array([[v]]) for v in vals]
    bg_level = 0.05  # the true, majority background level at this pixel
    assert abs(float(reduce(frames, "median")[0, 0]) - bg_level) > 0.05, \
        "median should still be measurably wrong here (the bug)"
    assert abs(float(reduce(frames, "shorth")[0, 0]) - bg_level) < 0.02

    # an exact 4-vs-4 tie: median lands dead in the middle; shorth must not.
    tie = [0.0, 0.0, 0.0, 0.0, 5.0, 5.0, 5.0, 5.0]
    tie_frames = [np.array([[v]]) for v in tie]
    assert float(reduce(tie_frames, "median")[0, 0]) == 2.5
    assert float(reduce(tie_frames, "shorth")[0, 0]) < 2.5


def test_shorth_keeps_channels_locked_and_matches_median_on_a_clean_majority():
    """When the majority is clean (no boundary straddler), shorth must agree
    with median -- it should only differ in the ambiguous case above."""
    rgb = [np.full((4, 4, 3), 0.0) for _ in range(9)]
    for f in rgb[:4]:
        f[:] = 0.9                                   # 4/9 = minority, an object
    out = reduce(rgb, "shorth")
    assert out.shape == (4, 4, 3)
    assert np.allclose(out, 0.0)
    assert np.allclose(reduce(rgb, "shorth"), reduce(rgb, "median"))


def test_object_removal_default_reducer_is_shorth(square):
    """remove_moving_objects must default to the robust reducer, not the
    textbook median that can leave a residue."""
    res = remove_moving_objects([square, square, square])
    assert res.reducer == "shorth"


def test_colour_frames_align_on_luma_and_keep_channels(stackable, interior):
    """Colour frames are registered on luma; the same shift moves all three
    channels, the plate stays (H, W, 3), and the valid box excludes the wrap."""
    rgb = np.stack([stackable, 0.6 * stackable, 1.0 - stackable], axis=-1)
    src = SyntheticSource(rgb, n=6, max_shift=6.0, noise=0.0,
                          mover=moving_disc(radius=20, value=0.03), seed=5)
    frames = src.frames()
    res = remove_moving_objects(frames, reducer="median")
    assert res.output.shape == rgb.shape
    gray = remove_moving_objects([f @ np.array([0.2126, 0.7152, 0.0722])
                                  for f in frames])
    assert np.allclose(res.shifts, gray.shifts, atol=1e-6)

    truth = fourier_shift(rgb, src.truth[0]["dy"], src.truth[0]["dx"])
    y0, y1, x0, x1 = res.stats["valid_box"]
    m = interior(rgb.shape)[y0:y1, x0:x1]
    for c in range(3):
        assert psnr(truth[y0:y1, x0:x1, c], res.output[y0:y1, x0:x1, c], m) > 30


def test_noise_estimate_needs_no_reference(stackable):
    """Immerkaer's estimator reads added noise from ONE image, and stacking
    visibly lowers it -- the number the Stacking page shows for real photos."""
    from spectrasync import add_noise, estimate_noise
    rng = np.random.default_rng(0)
    assert estimate_noise(stackable) < 0.04
    frames = [add_noise(stackable, 0.08, rng) for _ in range(8)]
    one = estimate_noise(frames[0])
    assert 0.06 < one < 0.11
    assert estimate_noise(reduce(frames, "mean")) < one / 2


def test_fourier_snr_reducer_handles_colour(stackable):
    rgb = np.stack([stackable, 0.5 * stackable, 1.0 - stackable], axis=-1)
    out = reduce([rgb + 0.01 * i for i in range(4)], "fourier_snr")
    assert out.shape == rgb.shape and np.isfinite(out).all()


def test_valid_box_is_the_translation_rectangle():
    from spectrasync import alignment_valid_mask, valid_box
    m = alignment_valid_mask((120, 160), dy=5.3, dx=-8.6)
    y0, y1, x0, x1 = valid_box(m)
    assert m[y0:y1, x0:x1].all()
    assert (y1 - y0) * (x1 - x0) >= 0.95 * m.sum()


def test_photo_set_loads_whole_frame_at_one_size():
    """Loading never crops: a 4:3 photo stays 4:3 at the requested size."""
    import glob
    import os
    from spectrasync import load_many
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    paths = sorted(glob.glob(os.path.join(here, "new_image", "1", "*.jpg")))[:3]
    if len(paths) < 3:
        pytest.skip("no sample photo set in new_image/1/")
    frames = load_many(paths, max_side=640, gray=False)
    assert all(f.shape == (480, 640, 3) for f in frames)


def test_highlight_handles_non_square_colour_frames():
    """Regression test: `change_score` used to diff colour frames directly,
    so a colour mask reached `outline_of` -> `fourier_gradient`, which takes
    an unlooped 2-D FFT over the wrong axes -- harmless on a SQUARE image
    (same broadcast shape either way) but a hard crash on a non-square one,
    which is what any real photo is. Detection must run on luma regardless of
    input colour, so this must succeed on a rectangular frame."""
    H, W = 96, 160
    yy, xx = np.mgrid[0:H, 0:W].astype(float)
    base = 0.5 + 0.2 * np.sin(xx / 6.0) * np.cos(yy / 8.0)
    background = np.stack([base, 0.6 * base, 1.0 - base], axis=-1)
    frame = background.copy()
    frame[30:50, 60:90] += 0.3
    det = highlight(frame, background, detector="bandpass", k=2.0)
    assert det.mask.shape == (H, W)          # detection stays single-channel
    assert det.overlay.shape == (H, W, 3)    # the overlay stays colour
    assert det.boxes


def test_highlight_sequence_reuses_a_given_background(square):
    """Passing `background` explicitly must skip recomputing object removal
    and highlight `frames` exactly as given, in order."""
    from spectrasync import highlight_sequence, remove_moving_objects

    src = SyntheticSource(square, n=6, max_shift=3.0, noise=0.0,
                          mover=moving_disc(radius=20, value=0.03), seed=7)
    frames = src.frames()
    res = remove_moving_objects(frames)
    dets, bg = highlight_sequence(res.aligned, background=res.output, k=2.5)
    assert bg is res.output
    assert len(dets) == len(res.aligned)


def test_highlight_valid_mask_suppresses_border_detections(square):
    """A `valid` mask must keep the region outside it from ever registering
    as a detection, even when the raw difference there is large -- exactly
    the wrapped-border case a real photo set produces."""
    background = square.copy()
    frame = square.copy()
    frame[:15, :15] += 0.4            # a big change, but OUTSIDE `valid`
    valid = np.ones(square.shape, bool)
    valid[:15, :15] = False
    det = highlight(frame, background, detector="bandpass", k=2.0, valid=valid)
    assert not det.mask[:15, :15].any()


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
