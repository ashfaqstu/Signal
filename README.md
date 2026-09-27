# SpectraSync

**Frequency-domain image alignment and analysis.** SpectraSync measures how one
image has moved, turned or zoomed relative to another, then uses that
alignment to denoise photo bursts, erase moving objects and highlight what
moved. Nearly all of the computation is FFTs, elementwise multiplications and
inverse FFTs.

Built for CSE220 (Signals & Systems). The Fourier theory is the method, not a
side topic: every feature follows from the shift theorem, the convolution
theorem or the differentiation property.

---

## Features

| # | Feature | What it does | Core idea |
|---|---|---|---|
| 1 | **Translation** | Finds the shift `(dy, dx)` between two images to sub-pixel accuracy | Phase correlation |
| 2 | **Rotation & scale** | Finds the angle, zoom and shift between two images | Fourier–Mellin (log-polar + phase correlation) |
| 3 | **Stacking** | Merges a burst of noisy frames into one clean image | Align, then average each pixel |
| 4 | **Object removal** | Builds a clean background plate from photos with people walking through | Align, then a robust per-pixel statistic (shorth / median) |
| 5 | **Highlight** | Outlines what moved in each photo | Band-pass filter, threshold, Fourier-domain gradient |

A sixth screen, **How it works / Spectrum**, walks through the derivation on
an image of your choice, computing each stage live.

---

## How the algorithms work

### The shared idea

> **One trick, applied three ways, plus one engine, applied three ways.**

- **The trick:** a geometric transform becomes a *shift* in some domain, and
  finding a shift means finding **one bright peak**.
- **The engine:** register every frame onto a reference, then collapse each
  pixel's values over time with a chosen statistic.

### 1 · Translation: phase correlation

By the **Fourier shift theorem**, moving an image only changes the *phase* of
its spectrum:

```
f₂(x,y) = f₁(x − x₀, y − y₀)   ⟺   F₂(u,v) = F₁(u,v) · e^{−j2π(u·x₀ + v·y₀)}
```

Here `u, v` are spatial frequencies (cycles/pixel). Dividing out the magnitude
leaves only the phase ramp, and its inverse transform is a delta at the shift:

```
R = F₂·F₁* / |F₂·F₁*| = e^{−j2π(u·x₀ + v·y₀)}      →      IFFT(R) = δ(x − x₀, y − y₀)
```

Steps: `argmax` → unwrap (an index past N/2 means a negative shift) →
parabolic sub-pixel fit. Cost is **O(N² log N)**, against O(N⁴) for a
brute-force search.
The **peak ratio** (highest peak ÷ next-highest peak) is the confidence
score. It separates a real lock (≳ 2–4) from no match (≈ 1).

Options: window (Hann, Blackman, …), sub-pixel method, and `β`, the
magnitude-normalisation exponent. `β = 1` is phase correlation and `β = 0` is
plain cross-correlation.

### 2 · Rotation & scale: Fourier–Mellin

1. Take **|F|** of both images. It is shift-invariant, so any translation
   drops out. It rotates *with* the image and scales by *1/s*.
2. Resample |F| onto a **log-polar grid** `(log ρ, θ)`. Rotation becomes a
   vertical shift and scale becomes a horizontal shift.
3. Run the **same phase correlation** on the two log-polar images to read off
   `θ` and `s`.
4. Undo the rotation and scale, then phase-correlate a **third time** to get
   the remaining translation.

A real image's |F| is centro-symmetric, so `θ` is only known modulo 180°.
Both candidates are tried, and the one with the stronger final translation
peak wins. Three parameter presets (sharp / medium / robust) are scored the
same way.

### 3–5 · The align + reduce engine

After alignment, **every pixel is a 1-D signal in time**. The reducer applied
to that signal decides what the output is:

| Feature | Reducer | Why |
|---|---|---|
| Stacking | `mean` | The minimum-variance estimator for Gaussian noise: `Var = σ²/N`, a gain of **10·log₁₀N dB** |
| Object removal | `shorth` / `median` | A passer-by is a short *outlier* burst. Mean (a linear filter) can only dilute it into a ghost. Order statistics give it **zero** weight. `shorth` averages the tightest majority run of sorted values, which avoids median's even-N blending |
| Highlight | object-removal plate, then compare | See below |

**Highlight pipeline**, where every filter is a multiplication in the
frequency domain:

```
score   = |IFFT( FFT(|photo − plate|) · (G_high − G_low) )|   band-pass: drops fine noise AND slow lighting drift
mask    = score > mean + k·σ, then blur and re-cut at 0.5      adaptive threshold + morphology as filtering
outline = |∇ mask| via  ∂/∂x ⟺ j2πu·F                          differentiation property, no contour tracer
```

---

## Architecture

```
spectrasync/
├── spectrasync/        The maths. Pure numpy (+ matplotlib in viz/). Imports no UI framework.
│   ├── core/           correlation, mellin, logpolar, register, filters, windows, subpixel, metrics, transform
│   ├── features/       stacking (the align+reduce engine), temporal reducers, removal, highlight
│   ├── io/             image / video loading
│   └── viz/            figures and overlays
├── app/                Streamlit UI: one page per feature, no maths
├── server/             FastAPI backend: thin services that call spectrasync
├── web/                React + TypeScript + Vite frontend (the primary UI)
├── media/              Default sample images, one folder per tool
├── tests/              pytest: algorithms against known ground truth, plus UI and API smoke tests
├── docs/viva/          Per-feature Q&A notes (overview, options, derivations)
└── tools/              Scripts that generate test data and demos
```

**Rules that keep it maintainable:**

- **`spectrasync/` never imports a UI.** Every algorithm is testable without a
  browser and shared by both frontends. Neither frontend reimplements any
  maths.
- **Every family of interchangeable algorithms is a `Registry`.** That covers
  windows, sub-pixel refiners, filters, reducers, change detectors and
  overlays. Adding one is a single decorated function, and it appears in the
  UI dropdowns automatically.
- **Confidence gating.** A frame whose peak ratio falls below the threshold
  is flagged and never silently stacked.
- **Honest metrics.** PSNR and NCC are computed only inside
  `alignment_valid_mask`, which excludes the border strip that a circular
  shift wraps in from the opposite edge.

More detail: [`spectrasync/ARCHITECTURE.md`](spectrasync/ARCHITECTURE.md).

---

## Getting started

Requires Python 3.12. The web UI also needs Node 18+.

```bash
cd spectrasync
pip install -r requirements.txt

# Web app (React + FastAPI). Build the frontend once, then serve it:
cd web && npm install && npm run build && cd ..
python run_web.py               # http://127.0.0.1:8000
python run_web.py --dev         # hot reload while editing the frontend

# Streamlit app (lighter, notebook-style)
python run.py

# Tests
python -m pytest tests -q
```

In the default mode, `run_web.py` serves the compiled `web/dist/`. After
changing frontend code, run `npm run build` again or use `--dev`.

### Sample images

Every tool runs on a built-in sample when you haven't uploaded anything. The
samples live in [`spectrasync/media/`](spectrasync/media/README.md), one
subfolder per tool (`01_translation/`, `02_rotation_scale/`, …). To change a
tool's default, replace the files in its folder. Both UIs pick up the change
with no code edits.

---

## Limitations

- **Translation:** the DFT only knows circular shifts, so shifts are
  recovered modulo the image size. Shifts up to about 30–40% of the frame are
  reliable. A coarse-to-fine pyramid handles larger ones.
- **Rotation & scale:** reliable for zoom between about **0.7× and 2.0×**. The
  model covers rotation, zoom and shift only, so the perspective change in
  hand-held photos leaves a small residual.
- **Removal / highlight:** a pixel is only recovered if the background is
  visible in most frames there. An object that never moves off a pixel cannot
  be erased from it.
