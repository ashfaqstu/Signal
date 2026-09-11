"""Overlays and diagnostic plots -- showing that it worked.

Milestones M7 and M9 in docs/02-CORE-IMPLEMENTATION.md.

Four overlays, each answering a different question. Build all four and let
the UI switch between them later. These functions RETURN arrays ready for
plt.imshow(); matplotlib lives in apps/, not here -- the one exception is
report_figure() at the bottom, which imports it locally.
"""

import numpy as np


def _n(a):
    """Percentile stretch to [0, 1] for display: clip at the 1st and 99th
    percentile, then rescale.

    Plain min/max scaling lets one hot pixel wash out the whole picture.
    DISPLAY ONLY -- never feed the result to the estimator or to a metric.

    Returns
    -------
    ndarray, same shape as `a`, float64, values guaranteed within [0, 1].
    """
    raise NotImplementedError


# ---------------------------------------------------------------------------
# The four overlays
# ---------------------------------------------------------------------------

def anaglyph(ref, mov):
    """ref -> red channel, mov -> green + blue.

    Misalignment shows as coloured fringes; perfect alignment is grey.
    The most readable overlay by far.
    Hint: np.dstack([_n(ref), _n(mov), _n(mov)]).

    Returns
    -------
    ndarray, shape (H, W, 3), float64 in [0, 1] -- an RGB image. Pass to
    imshow() with no cmap.
    """
    raise NotImplementedError


def checkerboard(ref, mov, tile=32):
    """Alternating `tile`-sized squares taken from each image.

    Broken lines at the tile borders mean misalignment; lines that run
    straight through mean success.
    Hint: yy, xx = np.mgrid[0:H, 0:W]; m = ((yy//tile) + (xx//tile)) % 2 == 0;
    then np.where(m, ref, mov).

    Returns
    -------
    ndarray, shape (H, W), float64 -- single-channel, so show it with
    cmap="gray". Same value range as the inputs.
    """
    raise NotImplementedError


def abs_diff(ref, mov):
    """|ref - mov| after normalising both.

    Should collapse towards BLACK after alignment. Put the before and after
    side by side -- this is the money shot.

    Returns
    -------
    ndarray, shape (H, W), float64 in [0, 1]. Show with cmap="gray" (or
    "magma" for drama) and FIX vmin=0, vmax=1 across the before/after pair,
    otherwise imshow rescales each panel and hides the improvement.
    """
    raise NotImplementedError


def blend(ref, mov, alpha=0.5):
    """Simple weighted average: (1-alpha)*ref + alpha*mov, both normalised.

    Returns
    -------
    ndarray, shape (H, W), float64 in [0, 1]. alpha=0 gives pure ref,
    alpha=1 pure mov -- wire it to a slider for a wipe-through demo.
    """
    raise NotImplementedError


# ---------------------------------------------------------------------------
# M9 diagnostics -- these turn a working script into a demonstration
# ---------------------------------------------------------------------------

def log_magnitude(F):
    """log1p(|fftshift(F)|), ready to imshow.

    Plot it for F1 and F2 side by side: they are visually IDENTICAL, because
    shifting an image does not change the magnitude of its transform. That is
    docs/01 section 2 made visible.

    Returns
    -------
    ndarray, shape (H, W), float64 >= 0, DC at the centre (that is what the
    fftshift is for). Log scale, so the values are not in [0, 1] -- let
    imshow autoscale, or normalise with _n() first.
    """
    raise NotImplementedError


def phase_fringes(R):
    """fftshift(angle(R)), ready to imshow.

    Straight, evenly spaced fringes. THE FRINGE SPACING AND TILT LITERALLY
    ARE THE SHIFT -- show them rotating as a shift slider moves and the whole
    project is explained in one visual.

    Returns
    -------
    ndarray, shape (H, W), float64 in [-pi, +pi]. Use a CYCLIC colormap
    (cmap="twilight" or "hsv") with vmin=-np.pi, vmax=np.pi, so the wrap from
    +pi to -pi does not read as a fake edge.
    """
    raise NotImplementedError


def correlation_surface(corr, crop=None):
    """fftshift(corr), optionally cropped to a `crop`-wide box around the peak.

    Returns
    -------
    Z : ndarray, float64. Shape (H, W) when crop is None, else (crop, crop)
        centred on the peak. Zero shift now sits at the CENTRE of the array,
        not at index 0.

    Feed it to ax.plot_surface(X, Y, Z, cmap="viridis") on a 3-D axis: a flat
    plane with one needle. Next to it plot the beta=0 (plain
    cross-correlation) surface -- a broad mushy hill. One slide, argument won.
    Build the X, Y grids yourself with np.meshgrid so the tick labels read as
    pixel offsets from zero.
    """
    raise NotImplementedError


def report_figure(ref, mov, aligned, corr, dy, dx, stats, path=None):
    """The 6-panel figure that sells the project.

        +-------------------+-------------------+
        | ref               | mov               |
        +-------------------+-------------------+
        | |diff| BEFORE     | |diff| AFTER      |   <- dramatic
        +-------------------+-------------------+
        | anaglyph BEFORE   | anaglyph AFTER    |   <- fringes vanish
        +-------------------+-------------------+

    Must display, in text on the figure: the recovered shift, the confidence,
    and the before/after overlay. That is the literal wording of the project
    brief -- a marker has to find all three without hunting.

    Import matplotlib INSIDE this function so the rest of core/ stays
    plot-free.

    Parameters
    ----------
    stats : dict of the numbers to print in the title/caption, e.g.
            {"peak": ..., "psr": ..., "ratio": ..., "psnr_before": ...,
             "psnr_after": ...}
    path  : where to savefig(), or None to skip saving

    Returns
    -------
    matplotlib Figure -- ALWAYS return it, even when `path` was written, so
    the Streamlit UI can call st.pyplot(fig) on the same function the CLI
    uses. Do not call plt.show() in here; that is the caller's decision.
    """
    raise NotImplementedError
