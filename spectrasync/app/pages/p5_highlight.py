"""Highlight what each photo has that the background plate doesn't.

Applied feature 3: run object removal on a set of photos to get the clean
background, then compare EVERY photo against that one background -- band-pass
the difference, threshold it, and outline the surviving blobs via the
differentiation property of the Fourier transform.
"""

import streamlit as st

import spectrasync as ss
from app import components as C
from app.registry import page

#: Photos of one scene with people walking through it. Used when nothing is uploaded.
SAMPLE_SET = "new_image/1/*.jpg"


@page("Highlight", order=50, icon="5.",
      help="Applied feature 3 - object removal gives the background; every "
           "photo is then compared against it, band-passed, thresholded, and "
           "outlined via the DIFFERENTIATION PROPERTY of the Fourier transform.")
def render():
    with st.sidebar:
        st.markdown("### Input")
        source = st.radio("Source", ["Photo set", "Synthetic"], key="hl_src")
        if source == "Photo set":
            max_side = st.slider(
                "working size (longest side, px)", 320, 1600, 640, 32,
                help="Photos are DOWNSCALED to this - never cropped.")
            colour = st.checkbox("Colour", True, key="hl_colour",
                                 help="Aligned on luma, then the same shift is "
                                      "applied to R, G and B.")
            mode = st.selectbox("Alignment", ["translation", "auto", "similarity"],
                                index=1, key="hl_mode",
                                help="auto = translation, falling back to "
                                     "rotation + scale when the peak is weak "
                                     "(useful for hand-held shots).")
            reducer = C.registry_select(ss.REDUCERS, "Background reducer",
                                        "shorth", "hl_red")
            photos, names = C.images_uploader(
                "Photos of the same scene (select several)", "hl_photos",
                sample_glob=SAMPLE_SET, max_side=max_side, gray=not colour)
        else:
            base, _ = C.image_uploader("Background", "hl_base",
                                       sample="data/raw/photo_b.jpg")
            n = st.slider("frames", 4, 24, 12, 1)
            radius = st.slider("object radius (px)", 6, 60, 26, 2)
            noise = st.slider("noise sigma", 0.0, 0.2, 0.01, 0.005)

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

    if source == "Photo set":
        if len(photos) < 3:
            st.info("Upload three or more photos of the same scene - camera "
                    "roughly still, objects free to move - or put some in "
                    "new_image/1/.")
            return
        frames = photos
    else:
        if base is None:
            st.warning("Upload a background, or put photo_b.jpg in data/raw/.")
            return
        img = ss.even_square(base, max_side=384)
        src = ss.SyntheticSource(img, n=n, max_shift=3.0, noise=noise,
                                 mover=ss.moving_disc(radius=radius, value=0.03),
                                 seed=3)
        frames = src.frames()
        reducer, mode = "shorth", "translation"

    with st.spinner("removing moving objects to build the background ..."):
        res = ss.remove_moving_objects(frames, reducer=reducer, mode=mode)

    # A photo set is trimmed to the area EVERY aligned photo covers: outside
    # it the circular shift wraps content in from the opposite edge, and
    # `valid` keeps that band from ever registering as a detection.
    H, W = res.output.shape[:2]
    box = res.stats["valid_box"] if source == "Photo set" else (0, H, 0, W)
    y0, y1, x0, x1 = box
    valid = ss.mask_from_box((H, W), box)

    def view(a):
        return a[y0:y1, x0:x1]

    band = {"low": low, "high": high} if detector == "bandpass" else {}
    with st.spinner("comparing every photo to the background ..."):
        detections, background = ss.highlight_sequence(
            res.aligned, background=res.output, detector=detector, k=k,
            smooth=smooth, min_area=min_area, valid=valid, **band)

    n_photos = len(detections)
    which = (st.slider("photo to inspect", 0, n_photos - 1, n_photos // 2, 1)
             if n_photos > 1 else 0)
    det = detections[which]
    label = names[which] if source == "Photo set" else f"frame {which}"
    total_objects = sum(len(d.boxes) for d in detections)

    if det.boxes:
        by0, bx0, by1, bx1 = det.boxes[0]
        C.result_line(f"{len(det.boxes)} <span class='unit'>object(s) here; "
                      f"largest at</span> ({(by0 + by1) // 2 - y0}, "
                      f"{(bx0 + bx1) // 2 - x0}) <span class='unit'>size</span> "
                      f"{by1 - by0} x {bx1 - bx0}")
    else:
        C.result_line("no object detected here <span class='unit'>- lower k</span>")
    st.markdown(f'<div class="subresult">{total_objects} object(s) total across '
                f'{n_photos} photos &nbsp;·&nbsp; threshold {det.threshold:.4f} '
                f'&nbsp;·&nbsp; mask covers {100 * view(det.mask).mean():.2f}% '
                f'of the frame</div>', unsafe_allow_html=True)
    st.write("")

    score_view = view(det.score)
    score_view = score_view / max(score_view.max(), 1e-9)

    c1, c2, c3, c4 = st.columns(4)
    with c1: C.image(view(res.aligned[which]), label)
    with c2: C.image(view(background), f"background plate ({reducer})")
    with c3: C.image(score_view, "band-passed change score")
    with c4: C.image(view(det.overlay), "outline, drawn over the photo")

    c1, c2 = st.columns(2)
    with c1: C.image(view(det.mask.astype(float)), "thresholded mask")
    with c2: C.image(view(det.outline), "outline = |grad(mask)| via j2*pi*u")

    C.note("The outline is not a contour-tracing algorithm: it is the gradient "
           "magnitude of the mask, computed by multiplying by j2*pi*u and "
           "j2*pi*v in the Fourier domain - the differentiation property of the "
           "transform. Detection always runs on LUMA, even for colour photos; "
           "only the overlay is drawn in colour. Compare the three detectors: "
           "'raw' passes noise and lighting drift straight through, the "
           "band-pass rejects both.")

    st.markdown("#### Every photo")
    cols = st.columns(min(6, n_photos))
    step = max(1, n_photos // len(cols))
    for col, i in zip(cols, range(0, n_photos, step)):
        with col:
            cap = names[i] if source == "Photo set" else f"frame {i}"
            C.image(view(detections[i].overlay), cap)
    # --- ADD NEW PANELS HERE ---
