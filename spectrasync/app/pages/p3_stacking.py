"""Multi-frame stacking for noise reduction."""

import os

import numpy as np
import streamlit as st

import spectrasync as ss
from app import components as C
from app.registry import page

#: A burst of noisy frames made by tools/make_noisy_set.py from new_image/2.
SAMPLE_SET = "new_image/2_noisy/set_1/*.jpg"
SAMPLE_CLEAN = "new_image/2_noisy/_clean/set_1.png"
COMPARE = ["mean", "median", "sigma_clip", "trimmed_mean", "fourier_snr"]


@page("Stacking", order=30, icon="3.",
      help="Applied feature 1 - align by translation, then reduce pixelwise. "
           "The reducer is the whole story: mean is optimal for Gaussian noise, "
           "median throws outliers away.")
def render():
    with st.sidebar:
        st.markdown("### Input")
        source = st.radio("Source", ["Photo set", "Synthetic"], key="st_src",
                          help="Photo set: stack your own noisy frames. "
                               "Synthetic: add noise to one image, to check the "
                               "gain against theory.")
        if source == "Photo set":
            max_side = st.slider(
                "working size (longest side, px)", 320, 1600, 800, 32,
                help="Frames are downscaled to this, never cropped. Downscaling "
                     "ALSO averages noise away, so keep it at the frames' own "
                     "size to let the stack do the work.")
            colour = st.checkbox("Colour", True, key="st_colour")
            frames, names = C.images_uploader(
                "Noisy frames of one scene (select several)", "st_photos",
                sample_glob=SAMPLE_SET, max_side=max_side, gray=not colour)
            clean_up = st.file_uploader("Clean reference (optional, for PSNR)",
                                        type=C.IMAGE_TYPES, key="st_clean")
        else:
            base, _ = C.image_uploader("Base image", "st_base",
                                       sample="data/raw/photo_b.jpg")
            n = st.slider("frames", 2, 32, 16, 1)
            noise = st.slider("noise sigma", 0.0, 0.4, 0.12, 0.01)
            shift = st.slider("max shift (px)", 0.0, 15.0, 5.0, 0.5)

        st.markdown("### Method")
        reducer = C.registry_select(ss.REDUCERS, "Reducer", "mean", "st_red")
        do_align = st.checkbox("Align before reducing", True,
                               help="Turn this off to see why alignment matters.")
        compare = st.checkbox("Compare all reducers", True)
        # --- ADD NEW CONTROLS HERE ---

    if source == "Synthetic":
        if base is None:
            st.warning("Upload an image, or put photo_b.jpg in data/raw/.")
            return
        _synthetic(base, n, noise, shift, reducer, do_align, compare)
        return

    if len(frames) < 2:
        st.info("Upload two or more noisy frames of the same scene, or generate "
                "some with  python tools/make_noisy_set.py")
        return

    clean = None
    if clean_up is not None:
        clean = (ss.load_rgb if colour else ss.load_gray)(clean_up, max_side=max_side)
    elif not st.session_state.get("st_photos") and os.path.exists(SAMPLE_CLEAN):
        clean = (ss.load_rgb if colour else ss.load_gray)(SAMPLE_CLEAN, max_side=max_side)

    with st.spinner("aligning and stacking ..."):
        res = ss.stack(frames, reducer=reducer, align=do_align)
    H, W = res.output.shape[:2]
    y0, y1, x0, x1 = res.stats["valid_box"]
    box = ss.mask_from_box((H, W), (y0, y1, x0, x1))

    def view(a):
        return a[y0:y1, x0:x1]

    # A clean reference is in ITS OWN frame, and the stack is in the first
    # uploaded frame's: register the two before measuring anything.
    m, clean_al = box, None
    if clean is not None:
        clean_al, m = ss.align_reference_to_output(res.output, clean, valid=box)

    raw = res.aligned[0]
    n_raw, n_out = ss.estimate_noise(raw, m), ss.estimate_noise(res.output, m)
    locked = res.stats.get("n_locked")
    theory = ss.theoretical_gain_db(res.n_frames, reducer)
    if clean_al is not None:
        single = ss.psnr(clean_al, raw, m)
        got = ss.psnr(clean_al, res.output, m)
        C.result_line(f"{got:.2f}<span class='unit'> dB</span> &nbsp;&nbsp; "
                      f"<span class='unit'>from</span> {single:.2f} dB "
                      f"&nbsp;&nbsp; +{got - single:.2f} dB")
    else:
        C.result_line(f"noise σ ≈ {n_out:.3f} &nbsp;&nbsp; "
                      f"<span class='unit'>from</span> {n_raw:.3f} &nbsp;&nbsp; "
                      f"{n_raw / max(n_out, 1e-9):.1f}× <span class='unit'>lower</span>")
    st.markdown(
        f'<div class="subresult">{res.n_frames} frames'
        + (f' &nbsp;·&nbsp; {locked}/{res.n_frames} aligned with confidence'
           if locked is not None else ' &nbsp;·&nbsp; not aligned')
        + f' &nbsp;·&nbsp; theory +{theory:.2f} dB for "{reducer}"'
        + (f' &nbsp;·&nbsp; noise σ ≈ {n_raw:.3f} → {n_out:.3f}'
           if clean_al is not None else ' &nbsp;·&nbsp; no clean reference: '
           'noise is estimated from each image alone')
        + '</div>', unsafe_allow_html=True)
    st.write("")

    c1, c2, c3 = st.columns(3)
    with c1: C.image(view(raw), f"one raw frame — {names[0]}")
    with c2: C.image(view(res.output), f"{reducer} of {res.n_frames} frames")
    with c3:
        if clean_al is not None:
            C.image(view(np.abs(ss.to_gray(res.output) - ss.to_gray(clean_al))
                         * m), "residual vs clean reference")
        else:
            C.image(view(np.abs(ss.to_gray(raw) - ss.to_gray(res.output))),
                    "what the stack removed (raw − stacked)")
    c1, c2 = st.columns(2)
    with c1: C.image(C.zoom(view(raw)), "zoomed centre — raw")
    with c2: C.image(C.zoom(view(res.output)), f"zoomed centre — {reducer}")
    st.download_button("Download the stacked image (PNG)",
                       ss.png_bytes(view(res.output)),
                       file_name=f"stacked_{reducer}.png", mime="image/png")

    if compare:
        st.markdown("#### Which reducer, and why")
        rows = []
        for name in COMPARE:
            out = ss.reduce(res.aligned, name)
            row = {"reducer": name, "noise σ": round(ss.estimate_noise(out, m), 4),
                   "theory (dB)": round(ss.theoretical_gain_db(res.n_frames, name), 2)}
            if clean_al is not None:
                p = ss.psnr(clean_al, out, m)
                row.update({"PSNR (dB)": round(p, 2), "gain (dB)": round(p - single, 2)})
            rows.append((row, out))
        st.dataframe([r for r, _ in rows], width='stretch', hide_index=True)
        C.note("Mean is the best estimate for Gaussian sensor noise: +10·log10(N) "
               "dB. Median gives up about 2 dB — var(median) → (π/2)·var(mean) — "
               "in exchange for the outlier rejection that the object-removal "
               "page depends on. sigma_clip buys most of the mean's performance "
               "back. Noise σ is measured with no reference (Immerkaer), so real "
               "texture leaves a small floor even on a clean image.")
        cols = st.columns(len(rows))
        for col, (r, out) in zip(cols, rows):
            with col:
                C.image(C.zoom(view(out)), f"{r['reducer']} — σ {r['noise σ']:.3f}")
    # --- ADD NEW PANELS HERE ---


def _synthetic(base, n, noise, shift, reducer, do_align, compare):
    """One image, noise and shifts added here, so the true answer is known."""
    img = ss.even_square(base, max_side=384)
    src = ss.SyntheticSource(img, n=n, max_shift=shift, noise=noise, seed=1)
    frames = src.frames()
    truth = ss.fourier_shift(img, src.truth[0]["dy"], src.truth[0]["dx"])
    pad = max(12, int(shift) + 6)
    m = ss.border_mask(img.shape, pad)

    res = ss.stack(frames, reducer=reducer, align=do_align)
    single = ss.psnr(truth, frames[0], m)
    got = ss.psnr(truth, res.output, m)

    C.result_line(f"{got:.2f}<span class='unit'> dB</span> &nbsp;&nbsp; "
                  f"<span class='unit'>from</span> {single:.2f} dB "
                  f"&nbsp;&nbsp; +{got - single:.2f} dB")
    locked = res.stats.get("n_locked")
    st.markdown(f'<div class="subresult">theory +{ss.theoretical_gain_db(n, reducer):.2f} dB'
                + (f' &nbsp;·&nbsp; {locked}/{n} frames locked' if locked is not None else '')
                + '</div>', unsafe_allow_html=True)
    st.write("")

    c1, c2, c3 = st.columns(3)
    with c1: C.image(frames[0], f"one raw frame — {single:.1f} dB")
    with c2: C.image(res.output, f"{reducer} of {n} — {got:.1f} dB")
    with c3: C.image(np.abs(res.output - truth) * m, "residual vs clean")

    if compare:
        st.markdown("#### Which reducer, and why")
        rows = ss.compare_reducers(frames, reducers=COMPARE, truth=truth, mask=m)
        st.dataframe(
            [{"reducer": r["reducer"], "PSNR (dB)": round(r["psnr"], 2),
              "gain (dB)": round(r["psnr"] - single, 2),
              "theory (dB)": round(r["theory_gain_db"], 2),
              "NCC": round(r["ncc"], 4)} for r, _ in rows],
            width='stretch', hide_index=True)
        cols = st.columns(len(rows))
        for col, (r, out) in zip(cols, rows):
            with col:
                C.image(out, f"{r['reducer']} — {r['psnr']:.1f} dB")
