# `media/` — one folder per tool's default sample

This is the **single place** every page's "use a sample if nothing is
uploaded" fallback is loaded from, in both UIs (the Streamlit app in `app/`
and the FastAPI+React app in `server/` + `web/`). Previously these defaults
were scattered across `data/raw/photo_b.jpg` and several `new_image/N/`
folders with no obvious naming — this replaces all of that.

**To change a tool's default: drop your own file(s) in the matching
subfolder, keeping the same filename** (or, for a `burst/`/`pair/` folder,
the same *number* of files — extra files are fine, they just get included;
fewer than the code expects falls back to whatever is already there). No
code change is needed for a same-name replacement.

| folder | used by | what's in it |
|---|---|---|
| `01_translation/` | Page 1 · Translation | `base.jpg` — the image used in "Synthetic pair" mode (a known shift is applied to it); `pair/*.jpg` — the real photo pair used in "Upload two images" mode |
| `02_rotation_scale/` | Page 2 · Rotation & Scale | `base.jpg` — synthetic-mode base image; `pair/reference.jpg` + `pair/rotated.jpg` — the real photo pair used in "Two photos" mode |
| `03_stacking/` | Page 3 · Stacking | `base.jpg` — synthetic-mode base image; `burst/*.jpg` — the noisy photo set; `clean_reference.png` — the matching clean ground truth, used only to measure PSNR gain |
| `04_object_removal/` | Page 4 · Object Removal | `base.jpg` — synthetic-mode background; `burst/*.jpg` — photos of one scene with something moving through it |
| `05_highlight/` | Page 5 · Highlight | same shape as `04_object_removal/`, but its **own copy** — override one without touching the other |
| `06_theory/` | Page 6 · How it works | `base.jpg` — the image the live derivation walkthrough runs on |

Exact code that reads each path is listed in that subfolder's own
`README.md`. The two UIs share the same files — a change here changes both
the Streamlit app and the web app's defaults.

`data/raw/` and `new_image/` still exist with the original files (untouched)
— nothing here was moved, only copied — and are still what `tests/` and
`tools/*.py` use directly for ground-truth fixtures; they are independent of
these UI defaults and don't need to change if you edit files here.
