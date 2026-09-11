"""Remove a moving object from a sequence with a temporal median."""

import numpy as np
import streamlit as st

import spectrasync as ss
from app import components as C
from app.registry import page


@page("Object Removal", order=40, icon="4.",
      help="Applied feature 2 - the same align+reduce engine as stacking. "
           "After alignment each PIXEL is a 1-D signal in time; the background "
           "is its persistent level and a passing object is a transient burst.")
def render():
    with st.sidebar:
        st.markdown("### Input")
        source = st.radio("Source", ["Synthetic", "Video file"], key="rm_src")
        if source == "Synthetic":
            base, _ = C.image_uploader("Background", "rm_base",
                                       sample="data/raw/photo_b.jpg")
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
        reducer = C.registry_select(ss.REDUCERS, "Reducer", "median", "rm_red")
        show_lti = st.checkbox("Compare linear vs nonlinear filters", True)
        # --- ADD NEW CONTROLS HERE ---

    if source == "Synthetic":
        if base is None:
            st.warning("Upload a background, or put photo_b.jpg in data/raw/.")
            return
        img = C.even_square(base, max_side=384)
        src = ss.SyntheticSource(img, n=n, max_shift=shift, noise=noise,
                                 mover=ss.moving_disc(radius=radius, value=0.03),
                                 seed=2)
        frames = src.frames()
        truth = ss.fourier_shift(img, src.truth[0]["dy"], src.truth[0]["dx"])
        pad = max(12, int(shift) + 6)
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
        frames = [C.even_square(f, 384) for f in frames]
        truth, pad = None, 16

    with st.spinner("aligning and reducing ..."):
        res = ss.remove_moving_objects(frames, reducer=reducer)

    m = np.zeros(res.output.shape, bool)
    m[pad:-pad, pad:-pad] = True

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
    else:
        C.result_line(f"{res.n_frames} <span class='unit'>frames reduced with "
                      f'"{reducer}"</span>')
    st.write("")

    c1, c2, c3 = st.columns(3)
    with c1: C.image(res.aligned[0], "frame 0 — object present")
    with c2: C.image(res.aligned[len(res.aligned) // 2], "mid frame — object moved")
    with c3: C.image(res.output, f"{reducer} plate — object removed")

    st.markdown("#### Each pixel is a signal in time")
    H, W = res.output.shape
    cy, cx = H // 2, W // 2
    sig, freq, spec = ss.pixel_timeseries(res.aligned, cy, cx)
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 2, figsize=(11, 3.0))
    ax[0].plot(sig, "o-", color=ss.PALETTE["ink"])
    ax[0].axhline(np.median(sig), color=ss.PALETTE["red_ink"], ls="--", lw=1.2)
    ax[0].set_xlabel("frame"); ax[0].set_ylabel("intensity")
    ax[0].set_title(f"pixel ({cy}, {cx}) over time", fontsize=10)
    ax[1].plot(freq, spec, color=ss.PALETTE["blue_ink"])
    ax[1].set_xlabel("cycles / frame"); ax[1].set_ylabel("|FFT|")
    ax[1].set_title("its temporal spectrum", fontsize=10)
    fig.tight_layout()
    C.figure(fig, "the flat level is the background; the excursion is the object "
                  "crossing (dashed line = the median that survives)")

    if show_lti:
        st.markdown("#### Why the spec says median")
        out = ss.compare_temporal_filters(res.aligned)
        cols = st.columns(len(out))
        for col, (name, img) in zip(cols, out.items()):
            with col:
                cap = name if truth is None else f"{name} — {ss.psnr(truth, img, m):.1f} dB"
                C.image(img, cap)
        C.note("The two LINEAR filters ghost: an impulsive outlier cannot be "
               "removed by any LTI filter, only smeared. The median is "
               "nonlinear, so it discards the outlier outright. That contrast "
               "is the whole justification for the method.")
    # --- ADD NEW PANELS HERE ---
