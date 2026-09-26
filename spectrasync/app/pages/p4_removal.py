"""Remove moving objects: align a set of photos (or frames), take a temporal median."""

import numpy as np
import streamlit as st

import spectrasync as ss
from app import components as C
from app.registry import page

#: Photos of one scene with people walking through it. Used when nothing is
#: uploaded. See media/README.md to swap this default for your own set.
SAMPLE_SET = "media/04_object_removal/burst/*.jpg"


@page("Object Removal", order=40, icon="4.",
      help="Applied feature 2 - the same align+reduce engine as stacking. "
           "After alignment each PIXEL is a 1-D signal in time; the background "
           "is its persistent level and a passing object is a transient burst.")
def render():
    with st.sidebar:
        st.markdown("### Input")
        source = st.radio("Source", ["Photo set", "Synthetic", "Video file"],
                          key="rm_src")
        if source == "Photo set":
            max_side = st.slider(
                "working size (longest side, px)", 320, 1600, 640, 32,
                help="Photos are DOWNSCALED to this - never cropped. Larger is "
                     "sharper but slower.")
            colour = st.checkbox("Colour", True,
                                 help="Aligned on luma, then the same shift is "
                                      "applied to R, G and B.")
            mode = st.selectbox("Alignment", ["translation", "auto", "similarity"],
                                index=1, key="rm_mode",
                                help="auto = translation, falling back to "
                                     "rotation + scale when the peak is weak "
                                     "(useful for hand-held shots).")
            photos, names = C.images_uploader(
                "Photos of the same scene (select several)", "rm_photos",
                sample_glob=SAMPLE_SET, max_side=max_side, gray=not colour)
        elif source == "Synthetic":
            base, _ = C.image_uploader("Background", "rm_base",
                                       sample="media/04_object_removal/base.jpg")
            n = st.slider("frames", 4, 24, 12, 1)
            radius = st.slider("object radius (px)", 6, 60, 26, 2)
            noise = st.slider("noise sigma", 0.0, 0.2, 0.01, 0.005)
            shift = st.slider("camera shake (px)", 0.0, 12.0, 4.0, 0.5)
        else:
            vid = st.file_uploader("Video", type=["mp4", "avi", "mov", "mkv"],
                                   key="rm_vid")
            n = st.slider("frames to read", 4, 60, 24, 1)
            step = st.slider("take every Nth frame", 1, 10, 2, 1)

        st.markdown("### Method")
        reducer = C.registry_select(ss.REDUCERS, "Reducer", "shorth", "rm_red")
        show_lti = st.checkbox("Compare linear vs nonlinear filters", True)
        # --- ADD NEW CONTROLS HERE ---

    truth, pad = None, 0
    if source == "Photo set":
        if len(photos) < 3:
            st.info("Upload three or more photos of the same scene - camera "
                    "roughly still, people free to move - or put some in "
                    "media/04_object_removal/burst/.")
            return
        frames = photos
    elif source == "Synthetic":
        if base is None:
            st.warning("Upload a background, or put one in media/04_object_removal/base.jpg.")
            return
        img = ss.even_square(base, max_side=384)
        src = ss.SyntheticSource(img, n=n, max_shift=shift, noise=noise,
                                 mover=ss.moving_disc(radius=radius, value=0.03),
                                 seed=2)
        frames = src.frames()
        truth = ss.fourier_shift(img, src.truth[0]["dy"], src.truth[0]["dx"])
        pad, mode = max(12, int(shift) + 6), "translation"
    else:
        if vid is None:
            st.info("Upload a video, or switch to Synthetic.")
            return
        import tempfile, os
        tmp = os.path.join(tempfile.gettempdir(), "spectrasync_in.mp4")
        with open(tmp, "wb") as f:
            f.write(vid.read())
        try:
            frames = ss.read_video(tmp, max_frames=n, step=step, max_side=384)
        except RuntimeError as e:
            st.error(str(e))
            return
        frames = [ss.even_square(f, 384) for f in frames]
        pad, mode = 16, "translation"

    with st.spinner("aligning and reducing ..."):
        res = ss.remove_moving_objects(frames, reducer=reducer, mode=mode)

    H, W = res.output.shape[:2]
    m = ss.border_mask((H, W), pad)
    # A photo set is trimmed to the area EVERY aligned photo covers: outside it
    # the circular shift wraps content in from the opposite edge.
    y0, y1, x0, x1 = res.stats["valid_box"] if source == "Photo set" else (0, H, 0, W)

    def view(a):
        return a[y0:y1, x0:x1]

    if truth is not None:
        occ = (np.abs(res.aligned[0] - truth) > 0.15) & m
        before = ss.psnr(truth, res.aligned[0], occ)
        after = ss.psnr(truth, res.output, occ)
        C.result_line(f"{after:.1f}<span class='unit'> dB</span> "
                      f"<span class='unit'>inside the object region, from</span> "
                      f"{before:.1f} dB")
        st.markdown(f'<div class="subresult">whole frame: '
                    f'{ss.psnr(truth, res.output, m):.1f} dB &nbsp;·&nbsp; '
                    f'{res.n_frames} frames &nbsp;·&nbsp; reducer "{reducer}"'
                    f'</div>', unsafe_allow_html=True)
    elif source == "Photo set":
        C.result_line(f"{res.n_frames} <span class='unit'>photos,</span> "
                      f"{res.stats['n_locked']}/{res.n_frames} "
                      f"<span class='unit'>aligned with confidence, reduced "
                      f'with "{reducer}"</span>')
        st.markdown(f'<div class="subresult">plate {x1 - x0} x {y1 - y0} px, '
                    f'{100 * (y1 - y0) * (x1 - x0) / (H * W):.0f}% of the '
                    f'{W} x {H} frame &nbsp;·&nbsp; only the border that not '
                    f'every photo covers is trimmed &nbsp;·&nbsp; alignment '
                    f'"{mode}"</div>', unsafe_allow_html=True)
        with st.expander("Per-photo alignment"):
            st.dataframe(
                [{"photo": nm, "dy (px)": round(dy, 2), "dx (px)": round(dx, 2),
                  "peak ratio": "reference" if i == 0 else f"{c:.1f}"}
                 for i, (nm, (dy, dx), c) in enumerate(
                     zip(names, res.shifts, res.stats["confidence"]))],
                width='stretch', hide_index=True)
    else:
        C.result_line(f"{res.n_frames} <span class='unit'>frames reduced with "
                      f'"{reducer}"</span>')
    st.write("")

    c1, c2, c3 = st.columns(3)
    with c1: C.image(view(res.aligned[0]), "frame 0 — object present")
    with c2: C.image(view(res.aligned[len(res.aligned) // 2]),
                     "mid frame — object moved")
    with c3: C.image(view(res.output), f"{reducer} plate — object removed")
    st.download_button("Download the plate (PNG)", ss.png_bytes(view(res.output)),
                       file_name=f"plate_{reducer}.png", mime="image/png")

    st.markdown("#### Each pixel is a signal in time")
    # the pixel that strays furthest from the plate: something moved through it
    region = ss.mask_from_box((H, W), (y0, y1, x0, x1))
    cy, cx = ss.most_disturbed_pixel(res.aligned, res.output, mask=region & m)
    sig, freq, spec = ss.pixel_timeseries(res.aligned, cy, cx)
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 2, figsize=(11, 3.0))
    ax[0].plot(sig, "o-", color=ss.PALETTE["ink"])
    ax[0].axhline(np.median(sig), color=ss.PALETTE["red_ink"], ls="--", lw=1.2)
    ax[0].set_xlabel("frame"); ax[0].set_ylabel("intensity")
    ax[0].set_title(f"pixel ({cy - y0}, {cx - x0}) over time", fontsize=10)
    ax[1].plot(freq, spec, color=ss.PALETTE["blue_ink"])
    ax[1].set_xlabel("cycles / frame"); ax[1].set_ylabel("|FFT|")
    ax[1].set_title("its temporal spectrum", fontsize=10)
    fig.tight_layout()
    C.figure(fig, "the pixel that changes most: the flat level is the "
                  "background, the excursions are something passing through "
                  "(dashed line = the median that survives)")

    if show_lti:
        st.markdown("#### Why the spec says median — and where plain median still fails")
        out = ss.compare_temporal_filters(res.aligned)
        cols = st.columns(len(out))
        for col, (name, img) in zip(cols, out.items()):
            with col:
                cap = name if truth is None else f"{name} — {ss.psnr(truth, img, m):.1f} dB"
                C.image(view(img), cap)
        C.note("The two LINEAR filters ghost: an impulsive outlier cannot be "
               "removed by any LTI filter, only smeared. The mean of the photos "
               "keeps a faint copy of every person, weighted by the fraction of "
               "photos they appear in. Median is nonlinear and usually discards "
               "the outlier outright — but with an EVEN photo count it AVERAGES "
               "the two middle values, so an object present in close to half "
               "the photos (or one photo landing on a soft edge) can still show "
               "as a faint ghost. 'shorth' fixes exactly that: it keeps the "
               "tightest majority-sized run of the sorted values instead of "
               "always trusting the middle two, so that in-between sample gets "
               "outvoted rather than blended in. It's the default reducer here.")
    # --- ADD NEW PANELS HERE ---
