# 01_translation

- `base.jpg` — the image used when Page 1's "Synthetic pair" source is
  selected. A *known* (dy, dx) shift (set by the sidebar sliders) is applied
  to it with `fourier_shift`, so the true answer is always known and the
  estimate's error can be measured directly.
- `pair/*.jpg` — the real photo pair used when "Upload two images" is
  selected and nothing has been uploaded. Files are matched by **name
  order** (first file alphabetically → "Reference", second → "Moved"), same
  convention as `media/02_rotation_scale/pair/`.

Read by:
- `app/pages/p1_translation.py` (`sample=` for the base,
  `sample_glob="media/01_translation/pair/*.jpg"` for the pair)
- `server/services/align.py`, via `server/services/common.py::get_base_image`
  (base) / `load_pair` (pair)

To change the default base: replace `base.jpg` with any image of your own
(same filename). To change the default pair: replace the files in `pair/`
with your own two photos of one scene, one a translation of the other.
