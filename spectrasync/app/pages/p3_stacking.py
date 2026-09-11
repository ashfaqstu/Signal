"""Multi-frame stacking for noise reduction."""

import numpy as np
import streamlit as st

import spectrasync as ss
from app import components as C
from app.registry import page


@page("Stacking", order=30, icon="3.",
      help="Applied feature 1 - align by translation, then reduce pixelwise. "
           "The reducer is the whole story: mean is optimal for Gaussian noise, "
           "median throws outliers away.")
def render():
    with st.sidebar:
        st.markdown("### Input")
        base, _ = C.image_uploader("Base image", "st_base",
                                   sample="data/raw/photo_b.jpg")
        n = st.slider("frames", 2, 32, 16, 1)
        noise = st.slider("noise sigma", 0.0, 0.4, 0.12, 0.01)
        shift = st.slider("max shift (px)", 0.0, 15.0, 5.0, 0.5)

        st.markdown("### Method")
        reducer = C.registry_select(ss.REDUCERS, "Reducer", "median", "st_red")
        do_align = st.checkbox("Align before reducing", True,
                               help="Turn this off to see why alignment matters.")
        compare = st.checkbox("Compare all reducers", True)
        # --- ADD NEW CONTROLS HERE ---

    if base is None:
        st.warning("Upload an image, or put photo_b.jpg in data/raw/.")
        return

    img = C.even_square(base, max_side=384)
    src = ss.SyntheticSource(img, n=n, max_shift=shift, noise=noise, seed=1)
    frames = src.frames()
    truth = ss.fourier_shift(img, src.truth[0]["dy"], src.truth[0]["dx"])
    m = np.zeros(img.shape, bool)
    pad = max(12, int(shift) + 6)
    m[pad:-pad, pad:-pad] = True

    res = ss.stack(frames, reducer=reducer, align=do_align)
    single = ss.psnr(truth, frames[0], m)
    got = ss.psnr(truth, res.output, m)

    C.result_line(f"{got:.2f}<span class='unit'> dB</span> &nbsp;&nbsp; "
                  f"<span class='unit'>from</span> {single:.2f} dB "
                  f"&nbsp;&nbsp; +{got - single:.2f} dB")
    locked = res.stats.get("n_locked")
    C.confidence_line(
        type("S", (), {"peak": got / 100, "psr": 0.0, "ratio": 9.9,
                       "verdict": "locked"})(),
        f"&nbsp;·&nbsp; theory +{ss.theoretical_gain_db(n, reducer):.2f} dB "
        f"&nbsp;·&nbsp; {locked}/{n} frames locked"
        if locked is not None else "")
    st.write("")

    c1, c2, c3 = st.columns(3)
    with c1: C.image(frames[0], f"one raw frame — {single:.1f} dB")
    with c2: C.image(res.output, f"{reducer} of {n} — {got:.1f} dB")
    with c3: C.image(np.abs(res.output - truth) * m, "residual vs clean")

    if compare:
        st.markdown("#### Which reducer, and why")
        rows = ss.compare_reducers(frames, truth=truth, mask=m)
        st.dataframe(
            [{"reducer": r["reducer"], "PSNR (dB)": round(r["psnr"], 2),
              "gain (dB)": round(r["psnr"] - single, 2),
              "theory (dB)": round(r["theory_gain_db"], 2),
              "NCC": round(r["ncc"], 4)} for r, _ in rows],
            width='stretch', hide_index=True)
        C.note("Mean tracks 10·log10(N) closely. Median gives up about 2 dB — "
               "var(median) → (π/2)·var(mean) — which is the price of the "
               "outlier rejection that the object-removal page depends on. "
               "sigma_clip buys most of the mean's performance back.")
        cols = st.columns(min(len(rows), 5))
        for col, (r, out) in zip(cols, rows):
            with col:
                C.image(out, f"{r['reducer']} — {r['psnr']:.1f} dB")
    # --- ADD NEW PANELS HERE ---
