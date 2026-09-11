"""Smoke tests for the UI.

These run the real Streamlit script through AppTest and assert that every page
renders with no exception. They are what stops a refactor in `spectrasync/`
from silently breaking a screen.
"""

import os

import pytest

st_testing = pytest.importorskip("streamlit.testing.v1")
AppTest = st_testing.AppTest

APP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "app", "main.py")
PAGE_LABELS = ["1. Translation", "2. Rotation & Scale", "3. Stacking",
               "4. Object Removal", "5. Highlight", "6. How it works"]


def _run(label=None, timeout=120):
    at = AppTest.from_file(APP, default_timeout=timeout)
    at.run()
    if label is not None:
        at.sidebar.radio[0].set_value(label).run()
    return at


def test_app_boots():
    at = _run()
    assert not at.exception, at.exception
    assert len(at.sidebar.radio[0].options) == len(PAGE_LABELS)


@pytest.mark.parametrize("label", PAGE_LABELS)
def test_each_page_renders(label):
    at = _run(label)
    assert not at.exception, f"{label}: {at.exception}"


def test_registry_drives_the_dropdowns():
    """A new registry entry must appear in the UI without touching page code."""
    at = _run("1. Translation")
    import spectrasync as ss
    names = {opt for sb in at.sidebar.selectbox for opt in sb.options}
    assert set(ss.WINDOWS.names()) <= names
    assert set(ss.SUBPIXEL.names()) <= names


def _slider_by_label(at, needle):
    for s in at.sidebar.slider:
        if needle.lower() in (s.label or "").lower():
            return s
    raise AssertionError(f"no sidebar slider matching {needle!r}; "
                         f"found {[s.label for s in at.sidebar.slider]}")


def test_beta_slider_changes_the_result():
    """beta = 1 is phase correlation, beta = 0 is plain cross-correlation.
    Dragging it must visibly change the correlation surface."""
    import numpy as np
    import spectrasync as ss
    from spectrasync.io import load_gray
    img = load_gray("data/raw/photo_b.jpg", max_side=256)[:200, :200]
    mov = ss.fourier_shift(img, 8.0, -5.0)
    sharp = ss.phase_correlation(img, mov, beta=1.0)
    broad = ss.phase_correlation(img, mov, beta=0.0)
    assert sharp.stats.ratio > broad.stats.ratio * 2

    at = _run("1. Translation")
    _slider_by_label(at, "beta").set_value(0.0).run()
    assert not at.exception
