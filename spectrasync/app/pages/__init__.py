"""Auto-discovery: importing this package registers every page module.

Drop a new `pXX_thing.py` in this folder with a `@page(...)` function and it
appears in the sidebar. Nothing here needs editing.
"""

import importlib
import pkgutil
from pathlib import Path

for _m in pkgutil.iter_modules([str(Path(__file__).parent)]):
    if not _m.name.startswith("_"):
        importlib.import_module(f"{__name__}.{_m.name}")
