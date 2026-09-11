"""Reusable UI pieces. A new page should need almost no raw HTML."""

from __future__ import annotations

import numpy as np
import streamlit as st

from app.theme import verdict_chip
from spectrasync.core.preprocess import to_unit

_counter = {"n": 0}


def reset_figures():
    _counter["n"] = 0


def figure(fig, caption=None):
    """A matplotlib figure in a bordered card with an auto-numbered caption."""
    st.markdown('<div class="figure">', unsafe_allow_html=True)
    st.pyplot(fig, width='stretch')
    if caption:
        _counter["n"] += 1
        st.markdown(f'<div class="caption">Fig. {_counter["n"]} — {caption}</div>',
                    unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


def image(arr, caption=None, clamp=True):
    a = np.asarray(arr)
    a = np.clip(a, 0, 1) if (clamp and a.ndim == 3) else (to_unit(a) if a.ndim == 2 else a)
    st.markdown('<div class="figure">', unsafe_allow_html=True)
    st.image(a, width='stretch')
    if caption:
        _counter["n"] += 1
        st.markdown(f'<div class="caption">Fig. {_counter["n"]} — {caption}</div>',
                    unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


def result_line(text, sub=None):
    st.markdown(f'<div class="result">{text}</div>', unsafe_allow_html=True)
    if sub:
        st.markdown(f'<div class="subresult">{sub}</div>', unsafe_allow_html=True)


def confidence_line(stats, extra=""):
    st.markdown(
        f'<div class="subresult">peak {stats.peak:.3f} &nbsp;·&nbsp; '
        f'PSR {stats.psr:.1f} &nbsp;·&nbsp; ratio {stats.ratio:.2f} &nbsp; '
        f'{verdict_chip(stats)} {extra}</div>', unsafe_allow_html=True)


def note(text):
    st.markdown(f'<div class="note">{text}</div>', unsafe_allow_html=True)


def registry_select(registry, label, default=None, key=None, help=None):
    """A selectbox driven by a Registry -- new options appear automatically."""
    names = registry.names()
    idx = names.index(default) if default in names else 0
    choice = st.selectbox(label, names, index=idx, key=key,
                          help=help or f"{len(names)} available")
    st.caption(registry.doc(choice))
    return choice


def image_uploader(label, key, sample=None):
    """Upload widget with a sample fallback so a demo never needs a file."""
    from spectrasync.io.images import load_gray
    up = st.file_uploader(label, type=["png", "jpg", "jpeg", "bmp", "tif"], key=key)
    if up is not None:
        return load_gray(up), up.name
    if sample:
        import os
        if os.path.exists(sample):
            return load_gray(sample, max_side=768), os.path.basename(sample)
    return None, None


def even_square(a, max_side=512):
    """Crop to an even square -- required by the log-polar stage."""
    a = np.asarray(a, dtype=np.float64)
    n = min(a.shape[0], a.shape[1], max_side)
    n = n // 2 * 2
    y0 = (a.shape[0] - n) // 2
    x0 = (a.shape[1] - n) // 2
    return a[y0:y0 + n, x0:x0 + n]
