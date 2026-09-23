"""Measure the rotation and scale between two photos with Fourier-Mellin."""

import numpy as np
import streamlit as st

import spectrasync as ss
from app import components as C
from app.registry import page

#: Photos of one scene taken at slightly different angles. The first two are
#: used when nothing is uploaded.
SAMPLE_PAIR = "new_image/3/*.jpg"


@page("Rotation & Scale", order=20, icon="2.",
      help="func_rotation_and_scale - FFT magnitude of both images, log-polar "
           "coordinates, then the SAME phase correlation reads off the angle "
           "and the scale factor.")
def render():
    with st.sidebar:
        st.markdown("### Input")
        source = st.radio("Source", ["Two photos", "Synthetic"], key="rs_src",
                          help="Two photos: MEASURE the rotation and scale between "
                               "your own images. Synthetic: warp one image by a "
                               "known amount, to check the accuracy.")
        if source == "Two photos":
            max_side = st.slider(
                "working size (longest side, px)", 320, 1280, 704, 32,
                help="Photos are DOWNSCALED to this, never cropped. ~700 px is "
                     "plenty for sub-degree accuracy.")
            photos, names = C.pair_uploader(
                ["Reference photo", "Rotated / scaled photo"], "rs_pair",
                sample_glob=SAMPLE_PAIR, max_side=max_side)
        else:
            base, _ = C.image_uploader("Base image", "rs_base",
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
        st.markdown("### Display")
        ov = C.registry_select(ss.OVERLAYS, "Overlay", "anaglyph", "rs_ov")
        # --- ADD NEW CONTROLS HERE ---

    if source == "Two photos":
        if len(photos) < 2:
            st.info("Upload a reference photo and a rotated / scaled photo of "
                    "the same scene, or put two photos in new_image/3/.")
            return
        ref_c, mov_c = (ss.to_even(p) for p in photos)
        ref_full, mov_full = ss.to_gray(ref_c), ss.to_gray(mov_c)
        ref, mov = ss.centre_square(ref_full), ss.centre_square(mov_full)
        truth = None
        labels = (f"reference — {names[0]}", f"second photo — {names[1]}")
    else:
        if base is None:
            st.warning("Upload an image, or put photo_b.jpg in data/raw/.")
            return
        ref = ss.even_square(base, max_side=384)
        mov = ss.warp_similarity(ref, angle, scale, tdy, tdx)
        if noise > 0:
            mov = ss.add_noise(mov, noise)
        ref_c, mov_c, ref_full, mov_full = ref, mov, ref, mov
        truth = (angle, scale)
        labels = ("reference", f"rotated {angle:+.0f}°, scaled {scale:.2f}×")

    presets = None if robust else [ss.PRESETS[0]]
    with st.spinner("Fourier-Mellin ..."):
        r = ss.register_similarity(ref, mov, presets=presets,
                                   n_theta=n_theta, n_rho=n_rho)
    ang = (r.angle_deg + 180.0) % 360.0 - 180.0
    aligned = ss.apply_registration(mov_c, r.angle_deg, r.scale, r.dy, r.dx)
    valid = ss.alignment_valid_mask(ref_full.shape, r.angle_deg, r.scale, r.dy, r.dx)
    aligned_g = ss.to_gray(aligned)

    C.result_line(f"{ang:+.2f}<span class='unit'>° rotation</span> &nbsp;&nbsp; "
                  f"{r.scale:.4f}<span class='unit'>× scale</span> &nbsp;&nbsp; "
                  f"({r.dy:+.1f}, {r.dx:+.1f})<span class='unit'> px shift</span>")
    extra = ""
    if truth:
        a_err = ss.angle_error_deg(ang, truth[0])
        s_err = ss.percent_error(r.scale, truth[1])
        extra = f"&nbsp;·&nbsp; error {a_err:.3f}° / {s_err:.2f}%"
    C.confidence_line(r.stats, extra)
    st.markdown(f'<div class="subresult">{ss.describe_similarity(ang, r.scale)}</div>',
                unsafe_allow_html=True)
    st.write("")

    c1, c2, c3 = st.columns(3)
    with c1: C.image(ref_c, labels[0])
    with c2: C.image(mov_c, labels[1])
    with c3:
        vm = valid[..., None] if aligned.ndim == 3 else valid
        C.image(np.where(vm, aligned, 0.0), "second photo, rotated / scaled back")

    ov_fn = ss.OVERLAYS[ov]
    c1, c2 = st.columns(2)
    with c1:
        C.image(ov_fn(ref_full, mov_full),
                f"{ov} BEFORE — NCC {ss.ncc(ref_full, mov_full, valid):.3f}")
    with c2:
        C.image(ov_fn(ref_full, aligned_g) * (valid[..., None] if ov == "anaglyph" else valid),
                f"{ov} AFTER — NCC {ss.ncc(ref_full, aligned_g, valid):.3f}")
    if source == "Two photos":
        n = ref.shape[0]
        C.note(f"Measured on the centred {n} x {n} square of each photo (the "
               "log-polar stage needs a square spectrum); the result is applied "
               "to the WHOLE photo above. Real hand-held shots also contain a "
               "little perspective change, which a rotation + scale model cannot "
               "express - that is why the AFTER overlay is close but not perfect.")

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
