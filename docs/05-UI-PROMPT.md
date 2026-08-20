# 05 — The UI: Decisions and the Build Prompt

Build this **last**, once [02-CORE-IMPLEMENTATION.md](02-CORE-IMPLEMENTATION.md)
is at M9. The UI must be a thin skin over working code, never a place where logic
lives.

---

## Your answers, and what they settle

| Question | Your answer |
|---|---|
| Theme | **Lab notebook / scientific paper** — warm paper, serif, ink-drawn plots, printed figure captions |
| Stack | *"whichever is easiest to edit and connect and show, because at the final evaluation we will be asked to implement or modify a small thing"* |
| Screens | **Core aligner + live math**, and **Guided theory walkthrough** |
| Interaction | **Live sliders that recompute instantly** |

### The stack decision: Streamlit

Your requirement was not "prettiest", it was "easiest to modify under pressure in
front of an examiner". That rules the field down decisively:

| | Add a new slider live | Connect to your numpy core | Risk during a live edit |
|---|---|---|---|
| **Streamlit** | **1 line** | `import` and call — no glue at all | **Lowest**: save the file, the page reloads itself |
| Flask + HTML/JS | ~15 lines across 3 files | write an endpoint, serialise, fetch, render | High: any of three layers can break |
| PyQt6 | ~8 lines, signal wiring | direct, but inside widget classes | Medium: restart the app on every edit |
| Matplotlib widgets | ~6 lines, callback plumbing | direct | Medium, and the theming ceiling is far too low for paper styling |

**Use Streamlit.** `pip install streamlit`, then `streamlit run apps/ui.py`. It
hot-reloads on save, so an examiner watching you type sees the result appear
immediately. Its default look is nothing like a lab notebook, but that is fixed
with one injected CSS block plus a matplotlib style sheet — both fully specified
in the prompt below.

The one real constraint: Streamlit re-runs your whole script on every widget
change, so expensive work **must** sit behind `@st.cache_data`. That is handled
in the prompt.

### About the two bonus screens

You did not select them, so the prompt builds the two screens you asked for and
**leaves a documented extension point** for the bonuses. Adding a third tab later
is one entry in a list and one function — deliberately, because you will be
building the bonuses after this.

---

## Before you run the prompt — pre-flight

The prompt assumes these exist and are tested. Check each one:

- [ ] `core/io_utils.py` — `load_gray`, `load_rgb`, `to_gray`, `match_shapes`
- [ ] `core/phase_correlation.py` — `phase_correlation(ref, mov, window, subpixel, beta) -> (dy, dx, corr)`
- [ ] `core/transform.py` — `fourier_shift`, `valid_mask`, `align`
- [ ] `core/metrics.py` — `peak_metrics`, `psnr`, `ncc`
- [ ] `core/viz.py` — `anaglyph`, `checkerboard`, `abs_diff`, `blend`
- [ ] `tests/` all green, including 200/200 exact circular shifts
- [ ] Two sample images in `data/raw/` that you know align correctly

If any signature differs from the above, **say so when you paste the prompt** —
the generated code calls these by name.

---

## THE PROMPT

Paste everything between the markers into a fresh conversation, with the repo
open. It is written to be executed, not read.

---
### ===== BEGIN PROMPT =====

Build a Streamlit UI for my Signals and Systems course project: a
frequency-domain image aligner based on phase correlation. The numpy core is
already written, tested and working — **do not reimplement any maths.** Import it
and call it.

**Existing API you must use, unchanged:**

```python
core.io_utils        : load_gray(path) -> (H,W) float64 [0,1]
                       load_rgb(path)  -> (H,W,3) float64 [0,1]
                       to_gray(rgb), match_shapes(a, b)
core.phase_correlation : phase_correlation(ref, mov, window=True, subpixel=True,
                                           beta=1.0) -> (dy, dx, corr)
core.transform       : fourier_shift(img, dy, dx), valid_mask(shape, dy, dx),
                       align(ref, mov, dy, dx) -> (aligned, mask)
core.metrics         : peak_metrics(corr) -> (peak, psr, ratio)
                       psnr(a, b, mask), ncc(a, b, mask)
core.viz             : anaglyph(ref, mov), checkerboard(ref, mov, tile),
                       abs_diff(ref, mov), blend(ref, mov, alpha)
```

Convention, already fixed throughout the project: `mov[y,x] = ref[y-dy, x-dx]`.
Positive `dy` means content moved down, positive `dx` means right. Do not
renegotiate it.

#### 1. Theme — lab notebook / scientific paper

Commit fully. This is a light-only design; do not add a dark mode.

**Palette (define once as Python constants AND as CSS variables):**

```
paper        #F7F3EA   page background
paper_raised #FCFAF4   cards, plot backgrounds
ink          #1F1B16   primary text, plot lines, axes
ink_soft     #5F574B   secondary text, captions
rule         #D9D0BF   hairlines, borders, dividers
red_ink      #A6301F   annotations, the measured result, arrows
blue_ink     #2A5570   secondary data series
green_ink    #3F6B3A   good/locked confidence
amber_ink    #B07A1E   marginal confidence
```

**Typography:** headings and body in a serif — load `Spectral` from Google Fonts
with `Georgia, 'Times New Roman', serif` as the fallback stack. All numeric
readouts and code in `IBM Plex Mono`, fallback `Consolas, monospace`. Body 16px,
line-height 1.65, measure capped around 70 characters.

**Page furniture:** a masthead with the project title in small-caps serif, a thin
double rule beneath it, and a right-aligned "sheet n of N" style label. Section
headings are numbered like a paper (`2.1 Cross-power spectrum`). Every figure
sits on `paper_raised` inside a 1px `rule` border with a centred caption below in
`ink_soft` small caps: `Fig. 4 — Correlation surface, beta = 0.80`. Number the
figures automatically with a counter so they stay correct when panels are
reordered.

**Ink annotation accents:** the measured result and the confidence verdict are
drawn like margin notes in red ink — `red_ink`, slightly larger, with a hand-drawn
feel achieved by a 1.5px underline that has a small random vertical wobble baked
in as an SVG path. Keep this to two or three places; restraint is the theme.

**Matplotlib must match.** Write `ui/paper_style.py` exporting a `PAPER_RC` dict
and a `use_paper_style()` helper, then apply it to every figure:

- `figure.facecolor` and `axes.facecolor` = `paper_raised`
- `text.color`, `axes.labelcolor`, `axes.edgecolor`, tick colors = `ink`
- serif font family, `font.size` 10, `axes.titlesize` 11, italic axis labels
- only the left and bottom spines visible, `linewidth` 0.8
- grid off by default; where a grid helps, `color=rule, linestyle=":", lw=0.6`
- default line color `ink`, second series `blue_ink`, highlight `red_ink`
- images: `cmap="gray"`, `interpolation="nearest"`
- correlation surfaces and spectra: a custom `LinearSegmentedColormap` running
  `paper -> amber_ink -> red_ink -> ink` so heat maps still read as ink on paper
- `savefig.facecolor` = `paper`, `savefig.dpi` = 200

Inject the CSS with a single `st.markdown(..., unsafe_allow_html=True)` call from
`ui/theme.py`, and set `.streamlit/config.toml` to a light base with
`backgroundColor="#F7F3EA"`, `secondaryBackgroundColor="#FCFAF4"`,
`textColor="#1F1B16"`, `primaryColor="#A6301F"`, `font="serif"` so Streamlit's
own chrome matches instead of fighting the CSS.

#### 2. Screen A — "Aligner" (the default screen)

Wide layout. A left sidebar holds every control; the main column is the paper.

**Sidebar controls, all live — the page recomputes on release:**

- Two file uploaders, `Reference image` and `Moved image`, plus a
  `Use sample pair` button that loads from `data/raw/`
- `beta` slider, 0.0 to 1.0, default 1.0, step 0.05, captioned
  "1.0 = phase correlation, 0.0 = plain cross-correlation"
- `window` toggle (Hann), default on
- `subpixel` toggle, default on
- `Overlay` radio: Anaglyph / Checkerboard / Difference / Blend
- `Checkerboard tile` slider, 8 to 128, shown only when Checkerboard is selected
- `Blend alpha` slider, shown only when Blend is selected
- A `Synthetic test` expander: sliders for a known `dy`, `dx` and a
  `Generate shifted pair` button that builds the moved image with
  `fourier_shift`, so a demo works with no upload at all. When this is active,
  display the true shift next to the estimate and the absolute error.

**Main column, top to bottom:**

1. **The result block.** Large, red-ink, monospace numbers:
   `dy = +12.483 px` and `dx = -7.219 px`. Directly beneath, a confidence line:
   `peak 0.874 · PSR 461.5 · ratio 91.8` with a verdict chip coloured by the
   peak ratio — `>= 2.0` green_ink "locked", `1.2` to `2.0` amber_ink "marginal",
   `< 1.2` red_ink "no lock". Use the thresholds exactly; they come from our
   measurements. When the synthetic generator is active, add a fourth line:
   `true (+12.000, -7.000) · error (0.483, 0.219) px`.
2. **Figure row 1:** reference, moved, and the chosen overlay, three columns.
3. **Figure row 2:** difference image before alignment and after alignment, side
   by side, sharing one colour scale so the collapse toward black is honest.
   Caption the PSNR for each, computed inside `valid_mask`.
4. **Figure row 3 — the live math, three columns:**
   - log-magnitude spectrum of `ref`, fftshifted, `log1p(abs(F))`
   - log-magnitude spectrum of `mov` — caption must point out they are identical
   - `np.angle(R)` fftshifted, showing the phase fringes. Caption:
     "the fringe spacing and tilt are the shift"
5. **Figure row 4 — the correlation surface**, two columns: a 2D fftshifted heat
   map with a red-ink circle annotating the peak, and a 3D `plot_surface` of the
   same data. Add a small `beta = 0` inset or a toggle so the needle can be
   compared against the broad cross-correlation hill.
6. **Download buttons:** the aligned image as PNG, and a combined report figure
   as PNG at 200 dpi.

#### 3. Screen B — "How it works" (guided walkthrough)

Same data as Screen A, presented one stage at a time. A `Stage` slider (1 to 7)
plus `Previous` / `Next` buttons, and a progress line rendered as seven small
squares that fill with ink as you advance.

Each stage is a two-column layout: the mathematics on the left in a bordered
`paper_raised` box, the live picture from the *current* images on the right.

| Stage | Left: formula and one-paragraph explanation | Right: live figure |
|---|---|---|
| 1 | The problem: `f2(x,y) = f1(x-x0, y-y0)` | the two input images |
| 2 | Shift theorem: `F2 = F1 exp(-j2pi(u x0 + v y0))` | the two magnitude spectra, visibly identical |
| 3 | Magnitude carries no shift information | the magnitude/phase swap experiment on the two images |
| 4 | Cross-power spectrum `R = F2 conj(F1) / abs(...)` | `angle(R)`, the phase fringes |
| 5 | `IFFT(R) = delta(x-x0, y-y0)` | the correlation surface, 3D |
| 6 | `argmax`, then unwrap modulo (H, W) | the surface with the peak circled and the index annotated |
| 7 | Apply `-dy, -dx` with the shift theorem | before/after difference images |

Render the formulas with `st.latex`. Keep each explanation under 60 words. This
screen must work end to end with the synthetic pair so it can be demonstrated
without any upload.

#### 4. Behaviour and performance

- Cache with `@st.cache_data` keyed on `(image bytes, window, subpixel, beta)`:
  one cached function returns `dy, dx, corr, F1, F2, R` so no widget change
  recomputes an FFT it does not need. Overlay style, tile size and blend alpha
  must **not** invalidate that cache.
- Downscale any input whose longest side exceeds 1024 px before estimating, and
  scale the reported shift back up. State the downscale factor in a caption.
- Guard every failure path with a paper-styled note rather than a traceback:
  mismatched shapes (offer to crop to the common overlap), single-channel or
  RGBA input, and a peak ratio below 1.2 (show the numbers and say the estimator
  did not find a lock — that is a correct answer, not an error).

#### 5. Code structure — optimised for being edited live in an exam

This is a hard requirement, not a preference. At the final evaluation we will be
asked to add or change a small feature in front of the examiner, so:

- **One config block at the very top of `apps/ui.py`**, above everything, holding
  every threshold, default, label and colour in plain named constants. Changing a
  default must never mean hunting through the file.
- **One function per panel**, named for what it draws: `panel_result()`,
  `panel_overlay()`, `panel_spectra()`, `panel_correlation()`,
  `panel_walkthrough_stage(n)`. Each takes explicit arguments and returns a
  matplotlib figure. No panel reads global state.
- **Screens registered in a plain list of `(label, function)` tuples** so adding
  a third screen — the object animator or the video stabiliser from
  `docs/03` and `docs/04` — is one list entry plus one function.
- **No classes, no decorators beyond `@st.cache_data`, no dynamic dispatch, no
  metaprogramming.** Boring, linear, greppable code.
- **A comment marker `# --- ADD NEW CONTROLS HERE ---`** in the sidebar builder
  and `# --- ADD NEW PANELS HERE ---` in the main column, so a new widget is
  provably a one-line insertion.
- Every function gets a one-line docstring saying what it draws. No file over
  400 lines; split into `ui/` modules if it grows past that.

**Files to create:**

```
apps/ui.py              entry point: config block, screens list, layout
ui/theme.py             CSS injection, colour constants, figure-caption helper
ui/paper_style.py       PAPER_RC, use_paper_style(), the custom colormap
ui/panels.py            one function per figure panel
ui/walkthrough.py       the seven stages, text and figures
.streamlit/config.toml  light theme matching the palette
```

#### 6. Deliverable

Working `streamlit run apps/ui.py`, both screens functional against the sample
pair and against the synthetic generator with no upload, every slider live, and
the whole thing looking like a well-typeset paper rather than a default
Streamlit app. Add a short `README` section documenting how to add a new control
and a new screen, with the exact lines to change.

### ===== END PROMPT =====

---

## Live-edit cheat sheet for the final evaluation

You told me the examiner will ask you to implement or modify a small thing on the
spot. Rehearse these. Each one is a real change, and each is small **because the
prompt above forced the structure that makes it small.**

| If they ask for... | What you change | Lines |
|---|---|---|
| A new tunable parameter | add a `st.slider` after `# --- ADD NEW CONTROLS HERE ---`, pass it into the call | 2 |
| A different overlay (e.g. horizontal split) | add a function to `core/viz.py`, add its name to the `Overlay` radio list | ~6 |
| Show a new metric | call it in the result block, add one line to the confidence string | 1 |
| A different window function (Hamming, Blackman) | swap `np.hanning` for `np.hamming` in `phase_correlation`, or add a selectbox | 1 to 3 |
| Report the shift in millimetres | add a `px per mm` number input, multiply in the result block | 2 |
| Invert the sign convention | **decline politely and explain why** — the convention is fixed and tested; show them the circular test instead |
| Add a whole new screen | one `(label, function)` tuple in the screens list, one function | ~20 |
| Make it handle three images | loop `phase_correlation(ref, mov_i)` over a list; the core is already pairwise | ~10 |
| Show the second correlation peak | mask a box around the peak, `argmax` again — this is Bonus 1's method | ~5 |

Two rehearsal rules:

1. **Practise editing with the app running.** Streamlit reloads on save, so the
   examiner watches the change appear. That is worth more than the change itself.
2. **Know which file each thing lives in without looking.** Sidebar controls and
   config in `apps/ui.py`; figures in `ui/panels.py`; colours in `ui/theme.py`;
   maths in `core/`. Being able to say "that's in `ui/panels.py`" before opening
   anything reads as ownership of the code.

---

## When you are ready

1. Finish the core through M9 and get the tests green.
2. `pip install streamlit`
3. Paste the prompt block above into a fresh session with this repo open.
4. Correct any function signature that drifted from the pre-flight list.
5. `streamlit run apps/ui.py`

After the bonuses are built, come back and extend the screens list — the prompt
deliberately left that door open.

Back to: **[README](../README.md)** ·
**[02 Core](02-CORE-IMPLEMENTATION.md)** ·
**[06 Troubleshooting and viva](06-TROUBLESHOOTING-AND-VIVA.md)**
