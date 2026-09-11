# Frequency-Domain Image Aligner

> Signals & Systems course project — estimate the translation between two shifted
> images using **phase correlation** in the 2D Fourier domain, then display the
> recovered shift and the aligned overlay.

Pure `numpy` for every piece of maths. `matplotlib` for every plot. No black boxes.

---

## The whole idea in five lines

1. Shifting an image does **not** change the magnitude of its Fourier transform —
   it only multiplies the transform by a complex exponential (a *phase ramp*).
2. So if you divide out the magnitudes, what is left between two images is
   **pure phase difference** = pure shift information.
3. That phase difference, inverse-transformed, is a **Dirac delta**.
4. A delta in a discrete image is a single bright pixel. Its coordinates *are*
   the shift.
5. Shift one image back by that amount and the two images lock together.

```
  img1 ──▶ FFT2 ──▶ F1 ──┐
                          ├──▶  R = F2·conj(F1) / |F2·conj(F1)|  ──▶ IFFT2 ──▶ δ(y-dy, x-dx)
  img2 ──▶ FFT2 ──▶ F2 ──┘        (cross-power spectrum)                          │
                                                                                   ▼
                                                                         argmax  ⇒  (dy, dx)
                                                                                   │
                                        ┌──────────────────────────────────────────┘
                                        ▼
                   shift img2 by (-dy, -dx)  ⇒  aligned overlay + difference map
```

---

## Documentation map

Read them in order. Each one is self-contained.

| # | File | What it gives you |
|---|------|-------------------|
| 01 | [docs/01-THEORY.md](docs/01-THEORY.md) | The full derivation, from the continuous Fourier transform down to `argmax`. Every formula you must be able to defend in the viva. |
| 02 | [docs/02-CORE-IMPLEMENTATION.md](docs/02-CORE-IMPLEMENTATION.md) | Step-by-step build guide for the core project: milestones, file layout, reference code, tests, figures. |
| 03 | [docs/03-BONUS-1-MOVING-OBJECT.md](docs/03-BONUS-1-MOVING-OBJECT.md) | Bonus 1 — animate an object moving between two photos. Feasibility verdict + full pipeline. |
| 04 | [docs/04-BONUS-2-VIDEO-STABILIZER.md](docs/04-BONUS-2-VIDEO-STABILIZER.md) | Bonus 2 — video stabiliser. Feasibility verdict + full pipeline, including the trajectory-filtering theory. |
| 05 | [docs/05-UI-PROMPT.md](docs/05-UI-PROMPT.md) | The ready-to-paste prompt that builds the themed UI, once the core works. |
| 06 | [docs/06-TROUBLESHOOTING-AND-VIVA.md](docs/06-TROUBLESHOOTING-AND-VIVA.md) | Symptom → cause → fix table, plus the questions your teacher will ask and the answers. |
| 07 | [docs/07-EVALUATION-PREP.md](docs/07-EVALUATION-PREP.md) | **The live evaluation.** What the examiner can ask, the exact fix for each, a verified "what if I do this to the image?" answer key, and the demo knobs that visibly reflect. |

---

## Scope and honest limits

**What this method does perfectly:** pure 2D translation, even with different
brightness/contrast, even with noise, even with moderate occlusion. Sub-pixel
accurate. One FFT pair per image, so it is fast.

**What it does NOT do (by construction):** rotation, scale, perspective, or
per-pixel deformation. If the camera rolled or zoomed between the two shots,
plain phase correlation returns a mushy peak. The standard fix (log-polar /
Fourier–Mellin) is described at the end of [01-THEORY.md](docs/01-THEORY.md) as a
stretch goal — do not attempt it until translation works flawlessly.

Say this limitation out loud in your presentation. Knowing the boundary of your
model is worth more marks than pretending there isn't one.

---

## Environment

Already verified on this machine: Python 3.12.7, numpy 2.5.2, matplotlib 3.10.0,
Pillow, scipy, imageio, cv2.

```bash
python -m venv .venv
# Windows PowerShell:  .venv\Scripts\Activate.ps1
# Git Bash:            source .venv/Scripts/activate
pip install numpy matplotlib pillow
# only for Bonus 2 (video decode/encode, not part of the DSP):
pip install imageio imageio-ffmpeg
```

Rule for the report: **every mathematical operation is numpy written by us.**
Pillow/imageio/cv2 appear only as file readers, which is not a signals task.

---

## Planned repository layout

```
Signal/
├── README.md                 ← you are here
├── docs/                     ← all documentation
├── data/
│   ├── raw/                  ← your source photos / videos
│   └── synthetic/            ← generated test pairs (ground truth known)
├── core/
│   ├── __init__.py
│   ├── io_utils.py           ← load / save / grayscale / float conversion
│   ├── preprocess.py         ← windowing, mean removal, normalisation
│   ├── phase_correlation.py  ← ★ the heart of the project
│   ├── transform.py          ← Fourier-domain sub-pixel shifting
│   ├── metrics.py            ← peak confidence, PSNR, NCC
│   └── viz.py                ← overlays, correlation surface, spectra
├── apps/
│   ├── align_cli.py          ← core deliverable, command line
│   ├── object_anim.py        ← bonus 1
│   └── stabilize.py          ← bonus 2
├── tests/
│   └── test_shift_recovery.py
└── outputs/                  ← figures, gifs, mp4s for the report
```

---

## Milestones

Core (do these in order, do not skip ahead):

- [ ] **M0** Environment + repo skeleton
- [ ] **M1** Load image → float64 grayscale in `[0,1]`
- [ ] **M2** Synthetic shifted-pair generator with known ground truth
- [ ] **M3** `phase_correlation()` returning integer shift
- [ ] **M4** Automated test: 200 random circular shifts recovered **exactly**
- [ ] **M5** Windowing + real photo pairs (non-circular shift)
- [ ] **M6** Sub-pixel refinement, verified against Fourier-shifted pairs
- [ ] **M7** Alignment + overlay visualisations (anaglyph, checkerboard, diff)
- [ ] **M8** CLI + one-page matplotlib report figure
- [ ] **M9** Diagnostics: spectra, correlation surface, confidence score

Bonus (only after M9 is green):

- [ ] **B1** Moving-object animation → [docs/03](docs/03-BONUS-1-MOVING-OBJECT.md)
- [ ] **B2** Video stabiliser → [docs/04](docs/04-BONUS-2-VIDEO-STABILIZER.md)
- [ ] **UI** Themed frontend → [docs/05](docs/05-UI-PROMPT.md)

Before the final evaluation:

- [ ] Work the drills in [docs/07](docs/07-EVALUATION-PREP.md), Part 5
- [ ] Memorise the four rows in [docs/07](docs/07-EVALUATION-PREP.md), Part 3
- [ ] Print the one-page card at the end of [docs/07](docs/07-EVALUATION-PREP.md)

---

## Notation used everywhere in these docs

| Symbol | Meaning |
|--------|---------|
| `ref` | image 1, the reference / fixed image |
| `mov` | image 2, the moved image |
| `H, W` | image height (rows, y) and width (columns, x) |
| `(dy, dx)` | the shift, in pixels, such that `mov[y,x] = ref[y-dy, x-dx]` |
| `F1, F2` | `fft2(ref)`, `fft2(mov)` |
| `R` | normalised cross-power spectrum |
| `corr` | `ifft2(R).real`, the correlation surface |

**One convention, fixed for the whole project:** positive `dy` means the content
moved **down**, positive `dx` means it moved **right**. numpy indexes as
`[row, col] = [y, x]`. Never deviate from this and your signs will never flip.
