"""SpectraSync -- Streamlit entry point.

    streamlit run app/main.py

Everything here is shell: theme, sidebar, page routing. All computation lives in
the `spectrasync` package, which knows nothing about Streamlit.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st  # noqa: E402

st.set_page_config(page_title="SpectraSync", page_icon="~",
                   layout="wide", initial_sidebar_state="expanded")

from app import components as C          # noqa: E402
from app.registry import by_label, labels, pages  # noqa: E402
from app.theme import apply_theme, masthead       # noqa: E402
import app.pages                                  # noqa: E402,F401  (registers pages)


def main():
    apply_theme()
    all_pages = pages()

    with st.sidebar:
        st.markdown("## SpectraSync")
        st.caption("Frequency-domain image alignment")
        choice = st.radio("Section", labels(), label_visibility="collapsed")
        st.markdown("---")

    current = by_label(choice)
    idx = [p["title"] for p in all_pages].index(current["title"]) + 1
    masthead(current["title"], f"sheet {idx} of {len(all_pages)}")
    if current["help"]:
        st.markdown(f'<div class="note">{current["help"]}</div>',
                    unsafe_allow_html=True)
        st.write("")

    C.reset_figures()
    current["render"]()


if __name__ == "__main__":
    main()
