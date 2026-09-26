"""A guided walk through the mathematics, computed live on your own image."""

import numpy as np
import streamlit as st

import spectrasync as ss
from app import components as C
from app.registry import page

STAGES = [
    ("The problem", r"f_2(x,y) = f_1(x - x_0,\; y - y_0)",
     "Two images, one a pure translation of the other. Two unknowns over H x W "
     "measurements - massively over-determined, which is why the answer can be "
     "so accurate."),
    ("Shift theorem", r"F_2(u,v) = F_1(u,v)\, e^{-j2\pi(u x_0 + v y_0)}",
     "Shifting multiplies the transform by a complex exponential. The magnitude "
     "is untouched; the shift becomes a LINEAR PHASE RAMP."),
    ("Magnitude is boring", r"\left|F_2\right| = \left|F_1\right|",
     "The two magnitude spectra are identical, so every bit of shift "
     "information lives in the phase - and the magnitude can be discarded."),
    ("Cross-power spectrum",
     r"R = \frac{F_2 \overline{F_1}}{\left|F_2 \overline{F_1}\right|}",
     "Dividing out the magnitude leaves a unit-magnitude exponential: all image "
     "content gone, only the ramp left. Those are the fringes."),
    ("Back to a delta", r"\mathcal{F}^{-1}\{R\} = \delta(x - x_0,\; y - y_0)",
     "The inverse transform of a pure exponential is an impulse - in a discrete "
     "image, a single bright pixel."),
    ("Find the spike", r"(\hat d_y, \hat d_x) = \arg\max\; r \pmod{H, W}",
     "Take the argmax, then unwrap: an index above half a dimension represents "
     "a negative shift, because the DFT only knows circular shifts."),
    ("Rotation and scale",
     r"|F| \text{ rotates with the image and scales as } 1/s",
     "Resample the magnitude spectrum onto a log-polar grid and a rotation "
     "becomes a vertical shift, a scale a horizontal one - solved by the same "
     "phase correlation. That is the Fourier-Mellin transform."),
]


@page("How it works", order=60, icon="6.",
      help="The derivation, one stage at a time, computed live on the image "
           "you choose.")
def render():
    with st.sidebar:
        st.markdown("### Data")
        base, _ = C.image_uploader("Image", "th_base",
                                   sample="media/06_theory/base.jpg")
        dy = st.slider("dy (px)", -30.0, 30.0, 12.0, 0.5)
        dx = st.slider("dx (px)", -30.0, 30.0, -8.0, 0.5)
        st.markdown("### Stage")
        i = st.slider("stage", 1, len(STAGES), 1) - 1

    if base is None:
        st.warning("Upload an image, or put one in media/06_theory/base.jpg.")
        return

    ref = ss.even_square(base, max_side=320)
    mov = ss.fourier_shift(ref, dy, dx)
    R, F1, F2 = ss.cross_power_spectrum(ref, mov)
    r = ss.phase_correlation(ref, mov)

    dots = " ".join("[#]" if j <= i else "[ ]" for j in range(len(STAGES)))
    st.markdown(f'<div class="subresult">{dots}</div>', unsafe_allow_html=True)
    st.write("")

    title, formula, text = STAGES[i]
    left, right = st.columns([1, 1.15])
    with left:
        st.markdown(f"### {i+1}. {title}")
        st.latex(formula)
        st.markdown(text)
        if i == 5:
            C.result_line(f"dy = {r.dy:+.3f} &nbsp; dx = {r.dx:+.3f}",
                          f"true ({dy:+.2f}, {dx:+.2f})")
    with right:
        if i == 0:
            C.image(np.hstack([ref, mov]), "reference (left) and moved (right)")
        elif i == 1:
            C.figure(ss.figure_spectra(F1, F2), "the two magnitude spectra")
        elif i == 2:
            C.image(ss.phase_swap(ref, mov),
                    "magnitude of A with the phase of B - structure follows PHASE")
        elif i == 3:
            C.figure(ss.figure_spectra(F1, F2, R),
                     "angle(R): the fringes ARE the shift")
        elif i == 4:
            C.figure(ss.figure_correlation(r.corr, r.dy, r.dx), "one needle")
        elif i == 5:
            C.image(ss.difference(ref, ss.apply_registration(mov, 0, 1, r.dy, r.dx)),
                    "difference after applying the estimate")
        else:
            rs = ss.estimate_rotation_scale(ref, ss.warp_similarity(ref, 20.0, 1.15))
            C.figure(ss.figure_logpolar(rs),
                     "log-polar spectra: a rotation is a vertical shift here")
