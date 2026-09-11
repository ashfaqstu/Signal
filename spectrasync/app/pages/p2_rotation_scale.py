"""Recover rotation and scale with the Fourier-Mellin transform."""

import numpy as np
import streamlit as st

import spectrasync as ss
from app import components as C
from app.registry import page


@page("Rotation & Scale", order=20, icon="2.",
      help="func_rotation_and_scale - FFT magnitude of both images, log-polar "
           "coordinates, then the SAME phase correlation reads off the angle "
           "and the scale factor.")
def render():
    with st.sidebar:
        st.markdown("### Input")
        base, name = C.image_uploader("Base image", "rs_base",
                                      sample="data/raw/photo_b.jpg")
        angle = st.slider("true rotation (deg)", -180.0, 180.0, 20.0, 1.0)
        scale = st.slider("true scale", 0.70, 2.00, 1.20, 0.01)
        tdy = st.slider("true dy (px)", -30.0, 30.0, 9.0, 1.0)
        tdx = st.slider("true dx (px)", -30.0, 30.0, -14.0, 1.0)
        noise = st.slider("noise sigma", 0.0, 0.20, 0.0, 0.01)

        st.markdown("### Method")
        robust = st.checkbox("Robust: try all presets", True,
                             help="Each preset is scored by the FINAL alignment "
                                  "quality, not by an intermediate confidence.")
        n_theta = st.select_slider("angular bins", [180, 360, 720, 1080], 720)
        n_rho = st.select_slider("log-radius bins", [128, 256, 512, 768], 512)
        # --- ADD NEW CONTROLS HERE ---

    if base is None:
        st.warning("Upload an image, or put photo_b.jpg in data/raw/.")
        return

    ref = C.even_square(base, max_side=384)
    mov = ss.warp_similarity(ref, angle, scale, tdy, tdx)
    if noise > 0:
        mov = ss.add_noise(mov, noise)

    presets = None if robust else [ss.PRESETS[0]]
    with st.spinner("Fourier-Mellin ..."):
        r = ss.register_similarity(ref, mov, presets=presets,
                                   n_theta=n_theta, n_rho=n_rho)
    valid = ss.alignment_valid_mask(ref.shape, r.angle_deg, r.scale, r.dy, r.dx)

    a_err = abs(((r.angle_deg - angle + 180) % 360) - 180)
    s_err = 100 * abs(r.scale - scale) / scale
    C.result_line(f"{r.angle_deg:+.2f}<span class='unit'>°</span> &nbsp;&nbsp; "
                  f"{r.scale:.4f}<span class='unit'>×</span> &nbsp;&nbsp; "
                  f"({r.dy:+.2f}, {r.dx:+.2f})<span class='unit'> px</span>")
    C.confidence_line(r.stats,
                      f"&nbsp;·&nbsp; error {a_err:.3f}° / {s_err:.2f}%")
    st.write("")

    c1, c2, c3 = st.columns(3)
    with c1: C.image(ref, "reference")
    with c2: C.image(mov, f"rotated {angle:+.0f}°, scaled {scale:.2f}×")
    with c3: C.image(r.aligned, "registered")

    c1, c2 = st.columns(2)
    with c1:
        C.image(ss.difference(ref, mov) * valid,
                f"difference BEFORE — NCC {ss.ncc(ref, mov, valid):.3f}")
    with c2:
        C.image(ss.difference(ref, r.aligned) * valid,
                f"difference AFTER — NCC {ss.ncc(ref, r.aligned, valid):.3f}")

    st.markdown("#### Inside the Fourier-Mellin stage")
    C.note("A rotation becomes a VERTICAL shift in log-polar coordinates and a "
           "scale becomes a HORIZONTAL one — which is why the same phase "
           "correlation solves both. The angle is only known modulo 180°, "
           "because the magnitude spectrum of a real image is centrosymmetric; "
           "both candidates are tried and the better alignment wins.")
    rs = ss.estimate_rotation_scale(ref, mov, n_theta=n_theta, n_rho=n_rho)
    C.figure(ss.figure_logpolar(rs),
             "log-polar magnitude spectra and their phase correlation")
    # --- ADD NEW PANELS HERE ---
