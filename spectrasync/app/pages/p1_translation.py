"""Estimate the spatial translation between two images by phase correlation."""

import numpy as np
import streamlit as st

import spectrasync as ss
from app import components as C
from app.registry import page


@page("Translation", order=10, icon="1.",
      help="func_translation - Fourier shift theorem, Dirac delta, find the "
           "spike, read off the shift.")
def render():
    with st.sidebar:
        st.markdown("### Input")
        src = st.radio("Source", ["Synthetic pair", "Upload two images"],
                       key="t_src")
        if src == "Synthetic pair":
            base, _ = C.image_uploader("Base image (optional)", "t_base",
                                       sample="data/raw/photo_b.jpg")
            dy = st.slider("true dy (px)", -40.0, 40.0, 12.5, 0.5)
            dx = st.slider("true dx (px)", -40.0, 40.0, -7.5, 0.5)
            noise = st.slider("noise sigma", 0.0, 0.4, 0.0, 0.01)
        else:
            base = None
            ref_img, _ = C.image_uploader("Reference", "t_ref")
            mov_img, _ = C.image_uploader("Moved", "t_mov")

        st.markdown("### Method")
        window = C.registry_select(ss.WINDOWS, "Window", "hann", "t_win")
        subpix = C.registry_select(ss.SUBPIXEL, "Sub-pixel", "parabolic", "t_sub")
        beta = st.slider("beta (magnitude normalisation)", 0.0, 1.0, 1.0, 0.05,
                         help="1.0 = phase correlation, 0.0 = plain cross-correlation")
        lp = st.slider("low-pass the cross-power spectrum", 0.0, 0.5, 0.0, 0.01,
                       help="0 = off. Watch the needle broaden: localisation "
                            "lives in the high frequencies.")
        st.markdown("### Display")
        ov = C.registry_select(ss.OVERLAYS, "Overlay", "anaglyph", "t_ov")
        tile = st.slider("tile", 8, 128, 32) if ov == "checkerboard" else 32
        alpha = st.slider("alpha", 0.0, 1.0, 0.5) if ov == "blend" else 0.5
        # --- ADD NEW CONTROLS HERE ---

    if src == "Synthetic pair":
        if base is None:
            st.warning("Upload a base image, or put photo_b.jpg in data/raw/.")
            return
        ref = C.even_square(base)
        mov = ss.fourier_shift(ref, dy, dx)
        if noise > 0:
            ref, mov = ss.add_noise(ref, noise), ss.add_noise(mov, noise)
        truth = (dy, dx)
    else:
        if ref_img is None or mov_img is None:
            st.info("Upload both images to begin.")
            return
        ref, mov = ss.match_shapes(ref_img, mov_img)
        truth = None

    mask = ss.lowpass(ref.shape, lp) if lp > 0 else None
    r = ss.phase_correlation(ref, mov, window=window, subpixel=subpix,
                             beta=beta, spectral_mask=mask)
    aligned = ss.apply_registration(mov, 0.0, 1.0, r.dy, r.dx)
    valid = ss.alignment_valid_mask(ref.shape, 0.0, 1.0, r.dy, r.dx)

    C.result_line(f"dy = {r.dy:+.3f} <span class='unit'>px</span> &nbsp;&nbsp; "
                  f"dx = {r.dx:+.3f} <span class='unit'>px</span>")
    extra = ""
    if truth:
        extra = (f"&nbsp;·&nbsp; true ({truth[0]:+.2f}, {truth[1]:+.2f}) "
                 f"error ({abs(r.dy-truth[0]):.3f}, {abs(r.dx-truth[1]):.3f}) px")
    C.confidence_line(r.stats, extra)
    if r.stats.polarity < 0:
        C.note("Peak is negative: the two images have INVERTED contrast. "
               "Located anyway because the peak search uses |corr|.")
    st.write("")

    ov_fn = ss.OVERLAYS[ov]
    kw = {"tile": tile} if ov == "checkerboard" else ({"alpha": alpha} if ov == "blend" else {})
    c1, c2, c3 = st.columns(3)
    with c1: C.image(ref, "reference")
    with c2: C.image(mov, "moved")
    with c3: C.image(ov_fn(ref, aligned, **kw), f"{ov}, after alignment")

    c1, c2 = st.columns(2)
    with c1:
        C.image(ss.difference(ref, mov) * valid,
                f"difference BEFORE — PSNR {ss.psnr(ref, mov, valid):.1f} dB")
    with c2:
        C.image(ss.difference(ref, aligned) * valid,
                f"difference AFTER — PSNR {ss.psnr(ref, aligned, valid):.1f} dB")

    st.markdown("#### The frequency domain")
    R, F1, F2 = ss.cross_power_spectrum(ref, mov, window=window, beta=beta)
    C.figure(ss.figure_spectra(F1, F2, R),
             "magnitude spectra are identical; the shift is entirely in the phase")
    C.figure(ss.figure_correlation(r.corr, r.dy, r.dx),
             "the correlation surface: one needle at the shift")
    # --- ADD NEW PANELS HERE ---
