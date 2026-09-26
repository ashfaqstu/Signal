# 7. Architecture & engineering decisions

This page is not maths — it's for the "how is this built" / "why two apps" /
"how do you add a new algorithm" questions, which judges ask almost as often
as the signal-processing ones.

## The one rule the whole codebase follows

```
app/            <- Streamlit UI only. Renders things. Owns no maths.
server/, web/   <- FastAPI + React web app. Same rule: owns no maths.
spectrasync/    <- plain numpy (+ matplotlib for viz/). Owns NO UI framework.
```

**`spectrasync/` never imports Streamlit, FastAPI, or React.** This is not a
style preference — it's what makes every algorithm:
- testable with no browser running (`tests/test_translation.py`,
  `test_rotation_scale.py`, `test_features.py` call straight into
  `spectrasync/`);
- runnable from a plain script (`tools/demo_applied.py`,
  `tools/demo_real_photo.py`, `tools/make_noisy_set.py`);
- reusable from **two independent frontends** without duplicating a single
  formula.

Concretely: if a UI page/route is about to compute something with `np.`
beyond reshaping an array for display, that computation belongs in
`spectrasync/` instead, as a small, named, documented function the UI then
just calls.

## Inside `spectrasync/`

```
spectrasync/
  types.py     Every result is a dataclass here (PeakStats, TranslationResult,
               RotationScaleResult, RegistrationResult, StackResult, DetectionResult, ...)
  registry.py  Registry — the plugin mechanism used everywhere below
  core/        Pure numpy. No file I/O, no matplotlib, no UI. Depends on nothing
               else in the package.
  features/    The three applied features, built ONLY from core/
  io/          Image/video/file access — the only place Pillow/imageio appear
  viz/         Matplotlib figures + overlay arrays — no UI framework
```

Dependency direction is strictly one-way: `features`, `io`, `viz` may depend
on `core`; `core` depends on nothing else in the package (two narrow,
deliberate exceptions: `features/highlight.py` reaches into
`viz.overlays.tint` for its overlay image, and `features/stacking.py`
reaches into `io.images.resize_to` for one helper).

| `core/` file | owns |
|---|---|
| `correlation.py` | `phase_correlation` — Page 1's engine |
| `mellin.py`, `logpolar.py` | `estimate_rotation_scale` — Page 2's engine |
| `register.py` | the facade composing both, resolving the 180° ambiguity, reporting results in English |
| `transform.py` | shifting, warping, resampling, every "which pixels are real" mask |
| `filters.py` | every frequency-domain filter, as a transfer function |
| `metrics.py` | `psnr`, `ncc`, `estimate_noise`, confidence, comparison helpers |
| `preprocess.py`, `windows.py`, `subpixel.py` | the building blocks the above are made of |

`features/` is one engine (`align + reduce`, `features/stacking.py::stack`),
called with a different reducer for `remove_moving_objects` and `highlight`
(see [00-INDEX.md](00-INDEX.md) for the one-paragraph version of this). All
reducers live in `features/temporal.py` as a `Registry` — adding one needs no
changes anywhere else in the codebase.

## The `Registry` plugin mechanism

Every family of interchangeable algorithms — window functions, sub-pixel
refiners, frequency filters, temporal reducers, change detectors, overlay
renderers, and even the Streamlit page list itself — is a
`spectrasync/registry.py::Registry`: an ordered, self-documenting
name→callable map.

```python
WINDOWS = Registry("window")

@WINDOWS.register("hann", doc="Raised cosine, zero at the edges")
def _hann(n):
    return np.hanning(n)

WINDOWS["hann"](64)     # call it directly
WINDOWS.names()          # -> ["hann", ...] drives EVERY UI dropdown, in this order
```

**Adding a new window/reducer/detector/filter is exactly one
`@REGISTRY.register("name", doc="...")`-decorated function, in the matching
`core/` or `features/` file — nothing else changes**, and it appears
automatically in the matching UI dropdown (`app/components.py::registry_select`
reads `REGISTRY.names()` directly; this is unit-tested by
`tests/test_app.py::test_registry_drives_the_dropdowns`, so a registry and its
UI can never silently drift apart). This is the concrete mechanism behind
every "which options exist and why" table in the other viva docs — the option
list you see in the sidebar *is* the registry's contents, not a hand-maintained
duplicate of it.

## Inside `app/` (the Streamlit application)

```
app/
  main.py        Page routing + sidebar shell. No maths.
  theme.py       CSS + matplotlib style, from ONE shared colour palette.
  registry.py    @page(...) decorator — drop a file in pages/, it appears in the sidebar.
  components.py  Streamlit widgets that call spectrasync and render the result.
  pages/pN_*.py  One screen each.
```

A page function reads, almost without exception: *build inputs from the
sidebar → call one or two `spectrasync` functions → a sequence of
`C.result_line` / `C.image` / `C.figure` calls to lay the answer out.* If a
page starts accumulating `if` branches around raw array indices instead of
calling into `spectrasync`, that's a sign the logic has drifted out of the
math package and should move back — a rule the codebase states explicitly
about itself.

## The second frontend: SpectraSync Studio (`server/` + `web/`)

The Streamlit app (`app/`) and the web app (`server/` FastAPI + `web/`
React/TypeScript/Vite) are **two independent UIs over the same
`spectrasync/` package** — proof by construction that the separation above
actually works, not just a stated intention.

- **`server/main.py`** — a FastAPI app exposing typed JSON endpoints
  (`/api/registries`, `/api/media`, `/api/layers`, `/api/run/{workspace}`,
  `/api/runs/{id}/pixel`, `/api/runs/{id}/export`).
- **`server/services/*.py`** — one thin service per workspace (align, rotate,
  stack, remove, highlight, spectrum), each mapping request parameters
  directly onto the *exact same* `spectrasync` calls the Streamlit pages
  make — e.g. `server/services/align.py::run_align` calls
  `ss.phase_correlation`, `ss.apply_registration`,
  `ss.alignment_valid_mask`, `ss.cross_power_spectrum` — the identical
  function names used on Page 1. No signal-processing logic is duplicated;
  the service layer only reshapes results into the API's response schema
  (readouts, layers, markers for the frontend canvas).
- **Synchronous route handlers by design**: run endpoints are plain
  (non-`async def`) routes, so FastAPI executes the CPU-bound FFT work on its
  background threadpool instead of blocking the single asyncio event loop —
  a small but deliberate concurrency choice, worth mentioning if asked "why
  not `async def`" for compute-heavy endpoints.
- **`server/media.py` / `server/layers.py`** — in-memory, zero-copy ndarray
  caching for uploaded media, and an LRU-evicted store of run results with
  lazy PNG/JPEG encoding, so repeated pixel probes / re-exports don't
  recompute the FFT pipeline.
- **`web/`** — React 18 + TypeScript + Vite, no external CSS framework
  (custom design tokens), with six workspaces mirroring the Streamlit pages
  (Align, Rotate & Scale, Noise Stack, Object Removal, Defect Highlight,
  Spectrum Lab) plus richer interaction affordances a notebook-style app
  can't easily offer: multi-pane synchronized canvas/zoom/pixel-probe, an
  NLE-style frame timeline with confidence sparklines for video sequences.
- Launch with `python run_web.py` (serves the built static bundle + API) or
  `python run_web.py --dev` (hot-reload dev server).

**Why two frontends exist at all** — a good one-line answer if asked: the
Streamlit app is the fast, notebook-style tool for *exploring and verifying*
the algorithms (every control, every intermediate figure, minimal engineering
overhead); the web app is the production-shaped, richer interactive tool for
*presenting and working with results* (multi-pane comparison, timelines,
exports) — and building it cost writing essentially zero new signal-processing
code, because `spectrasync/` already had no UI dependency baked in.

## Testing strategy

| test file | exercises |
|---|---|
| `tests/test_translation.py`, `test_rotation_scale.py`, `test_features.py`, `test_helpers.py` | `spectrasync/` directly — no browser, no server, pure numpy assertions against known/synthetic ground truth |
| `tests/test_app.py` | the real Streamlit app via `streamlit.testing.v1.AppTest`, for every page and every input source — a smoke layer that catches a `spectrasync/` refactor breaking a screen even though it never inspects pixel values |
| `tests/test_server.py` | every FastAPI route, endpoint, layer and media codec |

The layering matters: correctness is proven once, at the `spectrasync/`
level, against known ground truth (synthetic shifts/rotations/scales with a
known answer); the two UI layers are only smoke-tested for "does it still
run end-to-end," because they are not supposed to contain logic that could be
*incorrect* in the mathematical sense — only in the "did I wire this control
up" sense.

## `legacy/`

`legacy/` holds an earlier, single-file version of the core translation
algorithm plus a set of long-form derivation documents
(`legacy/docs/01-THEORY.md` through `07-EVALUATION-PREP.md`) written during
initial development. The current `spectrasync/` package is the refactored,
extended, tested successor — the derivations in `legacy/docs/01-THEORY.md`
are still an accurate, deeper walkthrough of the translation maths
specifically (this viva set's [01-translation.md](01-translation.md)
summarises and extends it to match the current code); `legacy/core/` itself
is not what runs in the app.

## Judges will probably ask

- **"Why not put the maths directly in the Streamlit callbacks — isn't that
  extra indirection?"** — Because then it couldn't be unit-tested without a
  browser, reused from a script, or reused from the second (web) frontend —
  which is exactly the FastAPI/React app that now exists precisely *because*
  the separation was enforced from the start.
- **"How would I add a new window function / reducer / filter?"** — One
  `@REGISTRY.register("name", doc="...")`-decorated function in the matching
  file; it appears in the UI dropdown automatically, with no other code
  changes, and a project test (`test_registry_drives_the_dropdowns`) enforces
  that the dropdown and the registry can never disagree.
- **"Do the Streamlit app and the web app share algorithm code, or did you
  write it twice?"** — Shared: every server service calls the identical
  `spectrasync` functions the Streamlit pages call (e.g. both call
  `ss.phase_correlation`, `ss.apply_registration`); the two frontends differ
  only in how they present the same computed result.
- **"How do you know the algorithms themselves are correct, separate from the
  UI working?"** — `tests/test_translation.py` / `test_rotation_scale.py` /
  `test_features.py` assert against synthetic inputs with a *known* answer
  (e.g. a Fourier-shifted image with a known fractional shift, or a
  `warp_similarity`-generated pair with a known angle/scale) — correctness is
  proven independently of, and before, any UI exists at all.
