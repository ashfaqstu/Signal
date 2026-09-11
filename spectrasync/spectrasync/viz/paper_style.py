"""The lab-notebook / scientific-paper look, for matplotlib.

One palette, defined once, shared by the figures and by the Streamlit CSS so
the app and its plots cannot drift apart.
"""

from __future__ import annotations

import matplotlib as mpl
from matplotlib.colors import LinearSegmentedColormap

PALETTE = {
    "paper":        "#F7F3EA",
    "paper_raised": "#FCFAF4",
    "ink":          "#1F1B16",
    "ink_soft":     "#5F574B",
    "rule":         "#D9D0BF",
    "red_ink":      "#A6301F",
    "blue_ink":     "#2A5570",
    "green_ink":    "#3F6B3A",
    "amber_ink":    "#B07A1E",
}

#: Heat maps that still read as ink on paper.
INK_CMAP = LinearSegmentedColormap.from_list(
    "ink_on_paper",
    [PALETTE["paper"], PALETTE["amber_ink"], PALETTE["red_ink"], PALETTE["ink"]])

PAPER_RC = {
    "figure.facecolor": PALETTE["paper"],
    "figure.edgecolor": PALETTE["paper"],
    "savefig.facecolor": PALETTE["paper"],
    "savefig.edgecolor": PALETTE["paper"],
    "savefig.dpi": 200,
    "axes.facecolor": PALETTE["paper_raised"],
    "axes.edgecolor": PALETTE["ink"],
    "axes.labelcolor": PALETTE["ink"],
    "axes.titlecolor": PALETTE["ink"],
    "axes.linewidth": 0.8,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": False,
    "grid.color": PALETTE["rule"],
    "grid.linestyle": ":",
    "grid.linewidth": 0.6,
    "text.color": PALETTE["ink"],
    "xtick.color": PALETTE["ink_soft"],
    "ytick.color": PALETTE["ink_soft"],
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "font.family": "serif",
    "font.serif": ["Georgia", "Times New Roman", "DejaVu Serif"],
    "font.size": 10,
    "axes.titlesize": 11,
    "axes.labelsize": 9,
    "legend.frameon": False,
    "image.cmap": "gray",
    "image.interpolation": "nearest",
    "lines.linewidth": 1.3,
    "lines.color": PALETTE["ink"],
}


def use_paper_style():
    """Apply globally. Call once at app or script start."""
    mpl.rcParams.update(PAPER_RC)
    return PAPER_RC


def paper_context():
    """Context manager form, for scripts that must not touch global state."""
    return mpl.rc_context(PAPER_RC)


def caption(ax, text, fignum=None):
    """A printed figure caption under an axis: `Fig. 3 - what it shows`."""
    label = f"Fig. {fignum} — {text}" if fignum is not None else text
    ax.set_xlabel(label, fontsize=8, color=PALETTE["ink_soft"],
                  style="italic", labelpad=6)


def bare(ax):
    """Strip an image axis down to nothing but the picture."""
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_color(PALETTE["rule"])
        s.set_linewidth(0.8)
    return ax
