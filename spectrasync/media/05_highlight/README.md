# 05_highlight

- `base.jpg` — used in "Synthetic" mode as the background; a synthetic
  moving disc is composited into it across frames.
- `burst/*.jpg` — photos of one scene, camera roughly still, something free
  to move through it, used in "Photo set" mode (3 or more required).

This folder is its own copy, independent of `media/04_object_removal/` —
override one without touching the other.

Read by:
- `app/pages/p5_highlight.py` (`SAMPLE_SET`, `sample=` for the base)
- `server/services/highlight.py` (`SAMPLE_SET`), via
  `server/services/common.py::get_base_image`/`load_sequence`

To change the default burst: replace the files in `burst/` with your own
photos of one scene with something moving through it.
