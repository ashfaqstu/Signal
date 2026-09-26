# 03_stacking

- `base.jpg` — used in "Synthetic" mode: noise and a small shift are added to
  it on the fly, so the true clean image is always known.
- `burst/*.jpg` — the noisy photo set used in "Photo set" mode. Any number of
  files works; add/remove freely.
- `clean_reference.png` — the ground-truth clean shot matching `burst/`, used
  only to measure PSNR gain against theory (optional — remove it and the page
  falls back to a no-reference noise estimate).

Read by:
- `app/pages/p3_stacking.py` (`SAMPLE_SET`, `SAMPLE_CLEAN`, `sample=` for the base)
- `server/services/stack.py` (`SAMPLE_SET`, `SAMPLE_CLEAN`), via
  `server/services/common.py::get_base_image`/`load_sequence`

To change the default burst: replace the files in `burst/` with your own
noisy photos of one static scene (and `clean_reference.png` with a matching
clean shot, if you have one).
