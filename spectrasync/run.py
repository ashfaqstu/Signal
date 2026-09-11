"""Launch the SpectraSync UI:  python run.py"""
import os
import subprocess
import sys

here = os.path.dirname(os.path.abspath(__file__))
app = os.path.join(here, "app", "main.py")
try:
    import streamlit  # noqa: F401
except ImportError:
    sys.exit("Streamlit is not installed.  pip install streamlit")
sys.exit(subprocess.call([sys.executable, "-m", "streamlit", "run", app]))
