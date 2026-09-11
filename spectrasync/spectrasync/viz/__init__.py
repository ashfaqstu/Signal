"""Presentation layer: matplotlib figures and overlay images. No Streamlit."""

from .figures import (figure_correlation, figure_grid, figure_logpolar,
                      figure_pair, figure_spectra, figure_stack)
from .overlays import (OVERLAYS, anaglyph, blend, checkerboard, difference,
                       split, tint)
from .paper_style import (INK_CMAP, PALETTE, PAPER_RC, bare, caption,
                          paper_context, use_paper_style)
