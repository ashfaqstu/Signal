# 04_object_removal

- `base.jpg` — used in "Synthetic" mode as the background; a synthetic
  moving disc is composited into it across frames with a known ground truth.
- `burst/*.jpg` — photos of one scene, camera roughly still, something free
  to move through it, used in "Photo set" mode. Any number of files works
  (3 or more required).

This folder is a plain copy of `media/05_highlight/`'s default set — the two
tools happened to ship with the same demo photos, but each folder can be
overridden **independently**: replacing files here does not touch Highlight's
copy, and vice versa.

Read by:
- `app/pages/p4_removal.py` (`SAMPLE_SET`, `sample=` for the base)
- `server/services/remove.py` (`SAMPLE_SET`), via
  `server/services/common.py::get_base_image`/`load_sequence`

To change the default burst: replace the files in `burst/` with your own
photos of one scene with something moving through it.
