"""Matplotlib figure builders. Every one returns a Figure; none of them show,
save or touch Streamlit. That keeps them usable from scripts, tests and the UI.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np

from ..core.preprocess import to_unit
from .overlays import anaglyph, difference
from .paper_style import INK_CMAP, PALETTE, bare, caption


def _imshow(ax, img, title=None, cmap=None, cap=None, n=None):
    a = np.asarray(img)
    ax.imshow(to_unit(a) if a.ndim == 2 else np.clip(a, 0, 1),
              cmap=cmap or ("gray" if a.ndim == 2 else None))
    bare(ax)
    if title:
        ax.set_title(title, pad=4)
    if cap:
        caption(ax, cap, n)
    return ax


def figure_pair(ref, mov, aligned=None, title="Alignment"):
    """ref / mov / aligned across the top, difference before and after below."""
    ncol = 3 if aligned is not None else 2
    fig, axes = plt.subplots(2, ncol, figsize=(4.2 * ncol, 7.4))
    fig.suptitle(title, y=0.97)
    _imshow(axes[0, 0], ref, "reference")
    _imshow(axes[0, 1], mov, "moved")
    if aligned is not None:
        _imshow(axes[0, 2], aligned, "aligned")
    d0 = difference(ref, mov)
    _imshow(axes[1, 0], d0, "difference BEFORE", cap="misalignment is visible")
    if aligned is not None:
        _imshow(axes[1, 1], difference(ref, aligned), "difference AFTER",
                cap="collapses toward black")
        _imshow(axes[1, 2], anaglyph(ref, aligned), "anaglyph AFTER",
                cap="grey means locked")
    else:
        _imshow(axes[1, 1], anaglyph(ref, mov), "anaglyph")
    fig.tight_layout()
    return fig


def figure_spectra(F1, F2, R=None):
    """Log-magnitude spectra side by side (visibly identical: magnitude is
    shift-invariant) plus the phase fringes of R, whose count IS the shift."""
    n = 3 if R is not None else 2
    fig, axes = plt.subplots(1, n, figsize=(4.2 * n, 4.4))
    _imshow(axes[0], np.log1p(np.abs(np.fft.fftshift(F1))), "log |F1|",
            cmap=INK_CMAP, cap="magnitude spectrum of the reference")
    _imshow(axes[1], np.log1p(np.abs(np.fft.fftshift(F2))), "log |F2|",
            cmap=INK_CMAP, cap="identical to F1 -- shift lives in the phase")
    if R is not None:
        axes[2].imshow(np.angle(np.fft.fftshift(R)), cmap="twilight")
        bare(axes[2])
        axes[2].set_title("angle(R)", pad=4)
        caption(axes[2], "fringe count = the shift in pixels")
    fig.tight_layout()
    return fig


def figure_correlation(corr, dy=None, dx=None, three_d=True):
    """The correlation surface: heat map with the peak circled, plus 3D."""
    cs = np.fft.fftshift(corr)
    H, W = cs.shape
    fig = plt.figure(figsize=(9.2, 4.4))
    ax1 = fig.add_subplot(1, 2, 1)
    ax1.imshow(cs, cmap=INK_CMAP)
    bare(ax1)
    ax1.set_title("correlation surface", pad=4)
    py, px = np.unravel_index(np.argmax(np.abs(cs)), cs.shape)
    ax1.add_patch(plt.Circle((px, py), max(H, W) * 0.035, fill=False,
                             color=PALETTE["red_ink"], lw=1.6))
    if dy is not None:
        caption(ax1, f"peak at dy = {dy:+.3f}, dx = {dx:+.3f} px")

    if three_d:
        ax2 = fig.add_subplot(1, 2, 2, projection="3d")
        step = max(1, max(H, W) // 128)
        Y, X = np.mgrid[0:H:step, 0:W:step]
        ax2.plot_surface(X, Y, cs[::step, ::step], cmap=INK_CMAP,
                         linewidth=0, antialiased=True)
        ax2.set_title("one needle, near-zero elsewhere", pad=4)
        ax2.set_xticks([]); ax2.set_yticks([]); ax2.set_zticks([])
        ax2.set_facecolor(PALETTE["paper"])
    fig.tight_layout()
    return fig


def figure_logpolar(rs_result):
    """The Fourier-Mellin intermediates: both log-polar spectra and their
    correlation. A rotation is a VERTICAL shift here, a scale a HORIZONTAL one."""
    fig, axes = plt.subplots(1, 3, figsize=(13.0, 4.2))
    _imshow(axes[0], rs_result.logpolar_ref, "log-polar |F1|", cmap=INK_CMAP,
            cap="rows = angle, columns = log radius")
    _imshow(axes[1], rs_result.logpolar_mov, "log-polar |F2|", cmap=INK_CMAP,
            cap="rotation shifts it vertically, scale horizontally")
    cs = np.fft.fftshift(rs_result.corr)
    axes[2].imshow(cs, cmap=INK_CMAP)
    bare(axes[2])
    axes[2].set_title("their phase correlation", pad=4)
    caption(axes[2],
            f"angle {rs_result.angle_deg:+.2f} deg, scale {rs_result.scale:.4f}x")
    fig.tight_layout()
    return fig


def figure_stack(frames, output, extra=None, titles=None):
    """A few input frames next to the stacked result."""
    show = list(frames[:3])
    titles = titles or [f"frame {i}" for i in range(len(show))]
    n = len(show) + 1 + (1 if extra is not None else 0)
    fig, axes = plt.subplots(1, n, figsize=(3.6 * n, 4.0))
    for ax, f, t in zip(axes, show, titles):
        _imshow(ax, f, t)
    _imshow(axes[len(show)], output, "stacked result",
            cap="aligned, then reduced pixelwise")
    if extra is not None:
        _imshow(axes[-1], extra, "detail")
    fig.tight_layout()
    return fig


def figure_grid(images, titles=None, caps=None, ncol=3, title=None, cmaps=None):
    """Generic n-up grid. The workhorse for ad-hoc figures and UI panels."""
    n = len(images)
    ncol = min(ncol, n)
    nrow = int(np.ceil(n / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(4.2 * ncol, 4.4 * nrow),
                             squeeze=False)
    for i, ax in enumerate(axes.ravel()):
        if i >= n:
            ax.axis("off")
            continue
        _imshow(ax, images[i],
                titles[i] if titles else None,
                cmap=(cmaps[i] if cmaps else None),
                cap=(caps[i] if caps else None))
    if title:
        fig.suptitle(title, y=0.99)
    fig.tight_layout()
    return fig
