"""Reusable UI pieces. A new page should need almost no raw HTML.

Layering rule for this file: everything here may call Streamlit AND the
`spectrasync` package, but any actual signal/image processing -- resizing,
cropping, registering, reducing -- belongs in `spectrasync`, not here. A
function in this module should only gather input (`st.file_uploader`, ...),
hand it to `spectrasync`, and render the result.
"""

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


IMAGE_TYPES = ["png", "jpg", "jpeg", "bmp", "tif", "tiff", "webp"]


def image_uploader(label, key, sample=None, max_side=768):
    """Upload widget with a sample fallback so a demo never needs a file.

    Uploads are DOWNSCALED to `max_side`, exactly like the sample. Loading a
    12 MP photo at full size and then taking a small centre square is what used
    to leave only a sliver of the picture.
    """
    from spectrasync.io.images import load_gray
    up = st.file_uploader(label, type=IMAGE_TYPES, key=key)
    if up is not None:
        return load_gray(up, max_side=max_side), up.name
    if sample:
        import os
        if os.path.exists(sample):
            return load_gray(sample, max_side=max_side), os.path.basename(sample)
    return None, None


@st.cache_data(show_spinner=False, max_entries=4)
def _decode_many(blobs, max_side, gray):
    import io
    from spectrasync.io.images import load_many
    return load_many([io.BytesIO(b) for b in blobs], max_side=max_side, gray=gray)


def images_uploader(label, key, sample_glob=None, max_side=768, gray=False):
    """Several images at once, all downscaled (never cropped) to one size.

    Falls back to the files matching `sample_glob`. Returns (frames, names).
    """
    ups = st.file_uploader(label, type=IMAGE_TYPES, key=key,
                           accept_multiple_files=True)
    if ups:
        blobs = tuple(u.getvalue() for u in ups)
        return _decode_many(blobs, max_side, gray), [u.name for u in ups]
    if sample_glob:
        import glob
        import os
        paths = sorted(glob.glob(sample_glob))
        if paths:
            blobs = tuple(open(p, "rb").read() for p in paths)
            return (_decode_many(blobs, max_side, gray),
                    [os.path.basename(p) for p in paths])
    return [], []


def pair_uploader(labels, key, sample_glob=None, max_side=768, gray=False):
    """One single-image uploader per label, resized to one common size.

    An empty slot falls back to the matching file from `sample_glob` (first
    file for the first slot, second for the second). Returns (frames, names),
    or ([], []) if a slot has neither.
    """
    import glob
    import os
    samples = sorted(glob.glob(sample_glob)) if sample_glob else []
    blobs, names = [], []
    for i, label in enumerate(labels):
        up = st.file_uploader(label, type=IMAGE_TYPES, key=f"{key}_{i}")
        if up is not None:
            blobs.append(up.getvalue())
            names.append(up.name)
        elif i < len(samples):
            with open(samples[i], "rb") as f:
                blobs.append(f.read())
            names.append(os.path.basename(samples[i]))
        else:
            return [], []
    return _decode_many(tuple(blobs), max_side, gray), names


def zoom(a, frac=0.3):
    """A centred crop, shown larger -- fine detail and noise vanish in a thumbnail."""
    H, W = a.shape[:2]
    h, w = max(1, int(H * frac)), max(1, int(W * frac))
    y0, x0 = (H - h) // 2, (W - w) // 2
    return a[y0:y0 + h, x0:x0 + w]
