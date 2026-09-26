# 02_rotation_scale

- `base.jpg` — used in "Synthetic" mode: a *known* rotation/scale/shift
  (sidebar sliders) is applied to it with `warp_similarity`, so the true
  answer is always known.
- `pair/reference.jpg` + `pair/rotated.jpg` — the real photo pair used in
  "Two photos" mode. Files are matched by **name order** (first file
  alphabetically → "reference photo", second → "rotated / scaled photo"), so
  keep those two names, or add more files and the first two (sorted) win.

Read by:
- `app/pages/p2_rotation_scale.py` (`SAMPLE_PAIR`, and `sample=` for the base)
- `server/services/rotate.py` (`SAMPLE_PAIR`), via
  `server/services/common.py::get_base_image`/`load_sequence`

To change the default pair: replace `reference.jpg` and `rotated.jpg` with
your own two photos of one scene at different angles/zoom.
