"""Lab-notebook theme for the Streamlit shell.

The palette lives in `spectrasync.viz.paper_style` so the CSS here and the
matplotlib figures cannot drift apart -- change a colour in one place only.
"""

import streamlit as st

from spectrasync.viz.paper_style import PALETTE, use_paper_style

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Spectral:ital,wght@0,400;0,600;1,400&family=IBM+Plex+Mono:wght@400;600&display=swap');

:root {
  --paper: %(paper)s; --raised: %(paper_raised)s; --ink: %(ink)s;
  --soft: %(ink_soft)s; --rule: %(rule)s; --red: %(red_ink)s;
  --blue: %(blue_ink)s; --green: %(green_ink)s; --amber: %(amber_ink)s;
}
.stApp { background: var(--paper); }
html, body, [class*="css"], .stMarkdown, p, li, label {
  font-family: 'Spectral', Georgia, 'Times New Roman', serif !important;
  color: var(--ink); font-size: 16px; line-height: 1.65;
}
h1, h2, h3, h4 { font-family: 'Spectral', Georgia, serif !important;
  color: var(--ink); font-weight: 600; letter-spacing: 0.01em; }
h1 { font-variant: small-caps; letter-spacing: 0.06em; }
code, kbd, .mono { font-family: 'IBM Plex Mono', Consolas, monospace !important; }

.masthead { border-bottom: 3px double var(--rule); margin-bottom: 1.2rem;
  padding-bottom: .5rem; display: flex; align-items: baseline;
  justify-content: space-between; }
.masthead .title { font-variant: small-caps; letter-spacing: .10em;
  font-size: 1.9rem; font-weight: 600; }
.masthead .sheet { color: var(--soft); font-size: .82rem; font-style: italic; }

.figure { background: var(--raised); border: 1px solid var(--rule);
  padding: .55rem; border-radius: 2px; }
.caption { text-align: center; color: var(--soft); font-size: .80rem;
  font-style: italic; margin-top: .35rem; }

.result { font-family: 'IBM Plex Mono', monospace !important;
  font-size: 1.55rem; color: var(--red); font-weight: 600; letter-spacing: .02em; }
.result .unit { font-size: .95rem; color: var(--soft); }
.subresult { font-family: 'IBM Plex Mono', monospace !important;
  font-size: .92rem; color: var(--soft); }

.chip { display: inline-block; padding: .10rem .60rem; border-radius: 999px;
  font-family: 'IBM Plex Mono', monospace !important; font-size: .78rem;
  border: 1px solid currentColor; }
.chip.locked   { color: var(--green); }
.chip.marginal { color: var(--amber); }
.chip.nolock   { color: var(--red); }

.note { border-left: 3px solid var(--rule); padding: .35rem .9rem;
  color: var(--soft); font-style: italic; background: var(--raised); }

section[data-testid="stSidebar"] { background: var(--raised);
  border-right: 1px solid var(--rule); }
section[data-testid="stSidebar"] h2 { font-size: 1.05rem; }
hr { border-color: var(--rule); }
[data-testid="stMetricValue"] { font-family: 'IBM Plex Mono', monospace !important;
  color: var(--red); }
.stButton button { border: 1px solid var(--rule); background: var(--raised);
  color: var(--ink); border-radius: 2px; }
</style>
""" % PALETTE


def apply_theme():
    """Inject the CSS and set the matplotlib style. Call once, from main."""
    st.markdown(CSS, unsafe_allow_html=True)
    use_paper_style()


def masthead(title, sheet=""):
    st.markdown(
        f'<div class="masthead"><span class="title">{title}</span>'
        f'<span class="sheet">{sheet}</span></div>', unsafe_allow_html=True)


def verdict_chip(stats):
    cls = {"locked": "locked", "marginal": "marginal", "no lock": "nolock"}[stats.verdict]
    return f'<span class="chip {cls}">{stats.verdict}</span>'
