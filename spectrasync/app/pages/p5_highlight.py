"""Highlight the moving object: remove it, detect the change, draw the outline."""

import numpy as np
import streamlit as st

import spectrasync as ss
from app import components as C
from app.registry import page


@page("Highlight", order=50, icon="5.",
      help="Applied feature 3 - object removal gives the background; the "
           "difference is band-passed, thresholded, and the outline comes from "
           "the DIFFERENTIATION PROPERTY of the Fourier transform.")
def render():
    with st.sidebar:
        st.markdown("### Input")
        base, _ = C.image_uploader("Background", "hl_base",
                                   sample="data/raw/photo_b.jpg")
        n = st.slider("frames", 4, 24, 12, 1)
        radius = st.slider("object radius (px)", 6, 60, 26, 2)
        noise = st.slider("noise sigma", 0.0, 0.2, 0.01, 0.005)
        which = st.slider("frame to highlight", 0, n - 1, n // 2, 1)

        st.markdown("### Detection")
        detector = C.registry_select(ss.DETECTORS, "Change detector",
                                     "bandpass", "hl_det")
        low, high = 0.02, 0.20
        if detector == "bandpass":
            low = st.slider("band low (cyc/px)", 0.005, 0.10, 0.02, 0.005)
            high = st.slider("band high (cyc/px)", 0.05, 0.45, 0.20, 0.01)
        k = st.slider("threshold k (mean + k sigma)", 0.5, 8.0, 3.0, 0.1)
        smooth = st.slider("mask smoothing", 0.0, 5.0, 1.5, 0.1)
        min_area = st.slider("min blob area (px)", 5, 500, 40, 5)
        # --- ADD NEW CONTROLS HERE ---

    if base is None:
        st.warning("Upload a background, or put photo_b.jpg in data/raw/.")
        return

    img = C.even_square(base, max_side=384)
    src = ss.SyntheticSource(img, n=n, max_shift=3.0, noise=noise,
                             mover=ss.moving_disc(radius=radius, value=0.03),
                             seed=3)
    frames = src.frames()
    with st.spinner("building the background plate ..."):
        res = ss.remove_moving_objects(frames)

    kw = {"low": low, "high": high} if detector == "bandpass" else {}
    frame = res.aligned[which]
    det = ss.highlight(frame, res.output, detector=detector, k=k,
                       smooth=smooth, min_area=min_area, **kw)

    if det.boxes:
        y0, x0, y1, x1 = det.boxes[0]
        C.result_line(f"{len(det.boxes)} <span class='unit'>object(s); largest at</span> "
                      f"({(y0+y1)//2}, {(x0+x1)//2}) "
                      f"<span class='unit'>size</span> {y1-y0} x {x1-x0}")
    else:
        C.result_line("no object detected <span class='unit'>- lower k</span>")
    st.markdown(f'<div class="subresult">threshold {det.threshold:.4f} '
                f'&nbsp;.&nbsp; mask covers {100*det.mask.mean():.2f}% of the frame'
                f'</div>', unsafe_allow_html=True)
    st.write("")

    c1, c2, c3, c4 = st.columns(4)
    with c1: C.image(frame, f"frame {which}")
    with c2: C.image(res.output, "background plate (median)")
    with c3: C.image(det.score / max(det.score.max(), 1e-9), "band-passed change score")
    with c4: C.image(det.overlay, "outline, drawn over the frame")

    c1, c2 = st.columns(2)
    with c1: C.image(det.mask.astype(float), "thresholded mask")
    with c2: C.image(det.outline, "outline = |grad(mask)| via j2*pi*u")

    C.note("The outline is not a contour-tracing algorithm: it is the gradient "
           "magnitude of the mask, computed by multiplying by j2*pi*u and "
           "j2*pi*v in the Fourier domain - the differentiation property of the "
           "transform. Compare the three detectors: 'raw' passes noise and "
           "lighting drift straight through, the band-pass rejects both.")

    st.markdown("#### Every frame")
    dets, _ = ss.highlight_sequence(res.aligned, background=res.output,
                                    detector=detector, k=k, smooth=smooth,
                                    min_area=min_area, **kw)
    cols = st.columns(min(6, len(dets)))
    step = max(1, len(dets) // len(cols))
    for col, i in zip(cols, range(0, len(dets), step)):
        with col:
            C.image(dets[i].overlay, f"frame {i}")
    # --- ADD NEW PANELS HERE ---
