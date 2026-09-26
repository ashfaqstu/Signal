# 4. Object Removal — clean background plate (Applied feature 2)

Code: [`spectrasync/features/stacking.py`](../../spectrasync/features/stacking.py)
(same `stack` engine), [`spectrasync/features/temporal.py`](../../spectrasync/features/temporal.py),
[`spectrasync/core/register.py`](../../spectrasync/core/register.py) (`register_pair`'s
`auto`/`similarity` modes) · UI: [`app/pages/p4_removal.py`](../../app/pages/p4_removal.py)

## L1 — High-level algorithm

**Question:** given several photos (or video frames) of a scene where a
camera was roughly still but people/objects moved through it, produce a
"clean plate" with the moving objects gone.

**Algorithm family:** this is **the exact same align+reduce engine as Page
3** — `remove_moving_objects` is a thin wrapper around `stack` — with two
changes of emphasis: the reducer defaults to `shorth` (a robust, outlier-
rejecting statistic) instead of `mean`, and alignment can automatically fall
back from translation-only to full Fourier-Mellin (rotation+scale) for
hand-held shots. Nothing new is invented here: the entire "removal" behaviour
is a consequence of *which statistic* is applied to the same per-pixel
time-series used on Page 3.

The reframing that makes this work: after alignment, a **background** pixel
holds nearly the same value in every frame (a *persistent* level), while a
pixel a moving object passes through holds the background value in most
frames and a *different*, object value in a few — a **transient burst** in
that pixel's 1-D time signal. A statistic that is robust to a minority of
outliers recovers the persistent (background) level and discards the burst.

## L2 — The pipeline and every UI option

### Pipeline, in code order

Identical call shape to Page 3 (`stack(frames, reducer=..., align=True, mode=...)`
via `remove_moving_objects`), so refer to
[03-stacking.md §L2](03-stacking.md#pipeline-in-code-order-stack) for the
align step — the only difference below is which options this page exposes
and why they're tuned differently.

### UI option: **Source — Photo set / Synthetic / Video file**

- **Photo set** — your own uploaded photos of one scene, people free to move.
- **Synthetic** — a known clean background, with a synthetic moving disc
  composited in (`SyntheticSource(..., mover=moving_disc(radius, value))`) and
  known camera shake — lets you measure **PSNR inside the object's occluded
  region specifically** (`occ` mask = where the truth differs from frame 0 by
  more than 0.15) against ground truth, i.e. directly quantify how well the
  object was actually removed, not just overall image quality.
- **Video file** — frames are decoded and *subsampled* (`step` = take every
  Nth frame) before the same pipeline runs; more temporal spacing between
  kept frames means the moving object is less likely to occupy the same pixel
  in adjacent samples, generally making outlier-style reducers more effective.

### UI option: **Alignment** (`translation`, `auto`, `similarity`)

This is a control on `register_pair`'s `mode` (see
[02-rotation-scale.md](02-rotation-scale.md)):
- `translation` — Page 1's method only. Fastest, and the spec's stated
  default for the applied features; correct when the camera truly only
  translated (e.g. tripod nudged, or handheld with negligible rotation).
- `similarity` — always runs full Fourier-Mellin (rotation+scale+translation)
  on every frame. Needed when the camera visibly rotated/zoomed between
  shots, at roughly 3× the per-frame cost.
- `auto` (default) — runs the cheap translation-only registration first; if
  its **peak ratio confidence** falls below a threshold (weak lock — see
  [06-confidence-and-metrics.md](06-confidence-and-metrics.md)), it retries
  with full similarity registration and keeps whichever alignment scores
  better by NCC on the centre crop. This is the practical default for
  real hand-held photo sets: cheap when translation alone is enough, robust
  when it isn't.

### UI option: **Reducer** — why `shorth` is the *default here*, unlike Page 3

`shorth` (Rousseeuw's "shortest half"): sort the N samples at a pixel, look at
**every contiguous run of `h = N/2 + 1` consecutive order statistics**, keep
whichever run has the smallest spread (`max − min` within the run), and
average *just that run*.

*Why plain `median` is not always enough here:* with an **even** frame count,
`numpy`'s median is the *mean of the two middle order statistics*. If an
object occupies a given pixel in close to half the frames — or even one frame
lands with an in-between value right at that boundary (a soft edge, a shadow,
a slightly imperfect alignment) — that averaging step blends one real
background sample together with one object sample, and the object survives as
a faint ghost in the "clean" plate. `shorth` instead evaluates *every*
majority-sized run and keeps whichever is most **internally self-consistent**
— a stray in-between sample gets **outvoted** rather than blended in.

| reducer | outlier handling | typical artefact if wrong choice |
|---|---|---|
| `mean` | none | a semi-transparent ghost of every moving object, weighted by the fraction of frames it appears in |
| `median` | good, but the even-N averaging gap above | a faint ghost when the object occupies ~half the frames at a pixel |
| `shorth` (default here) | closes exactly that gap | needs `N ≥ 3` to be well-defined (falls back to median below that) |
| `sigma_clip` | good, iterative | can under- or over-clip depending on `sigma`/`iters` tuning |

### UI option: **Compare linear vs. nonlinear filters**

Runs `compare_temporal_filters` — puts a couple of **linear (LTI)** combiners
(e.g. mean-style) next to **median** on the same aligned stack, side by side.
The two linear filters visibly **ghost**: this is the direct, visual proof of
the L3 argument below (no LTI filter can reject an impulsive outlier, only
smear it). It's presented explicitly because "why not just blur/average it
away" is a very natural judge question, and this panel answers it with a
picture instead of only an equation.

### The "pixel is a signal in time" panel

The page picks the single pixel with the largest disagreement between a raw
frame and the reduced output (`most_disturbed_pixel`) — i.e. the pixel most
likely to have had an object pass through it — and plots two things:
1. Its **raw intensity across frames**, with the median level drawn as a
   dashed reference line: visually, a flat baseline with one or two spikes.
2. Its **temporal Fourier spectrum** (`|FFT|` of that same 1-D signal across
   frames, via `pixel_timeseries`): a transient burst has broadband spectral
   content (a delta-like disturbance in time spreads across *all* temporal
   frequencies), which is the time-domain/frequency-domain restatement of "an
   outlier cannot be removed by smoothing (a low-pass filter in time) — you
   have to reject it directly."

## L3 — The mathematics

### Formalising "outlier" and why no LTI filter can remove it

Per-pixel time signal across N frames: `x_i = b + o_i·k_i`, where `b` is the
persistent background value, `k_i ∈ {0,1}` flags whether an object occupied
that pixel in frame `i`, and `o_i` is the (different) object value when it
does. If `k_i = 1` for a *minority* of frames, `b` is the **mode/majority**
value of the sequence, not necessarily its mean.

Any **linear time-invariant** combiner is `y = Σ w_i x_i` with fixed weights
`w_i` (mean: `w_i = 1/N` for all `i`). Substituting,

```
y = b·Σw_i + Σ w_i·o_i·k_i = b·Σw_i + (residual term from the object frames)
```

Since every `w_i > 0` for a real averaging filter, the residual term is
**never exactly zero** whenever any `k_i = 1` and `w_i ≠ 0` — the object
always contributes *something*, proportional to its weight. This is a general
fact about linear systems: linearity guarantees superposition, and
superposition guarantees that every input component (including an unwanted
transient) shows up, scaled, in the output. There is no choice of *fixed*
weights that zeroes out a component whose *location in the sequence* is
unknown in advance and different at every pixel.

A **nonlinear**, order-statistic-based combiner breaks this: `median` and
`shorth` effectively choose *data-dependent* weights (implicitly 0 or
`1/h`) — decided *after* looking at the actual values — so a pixel correctly
identified as an outlier gets weight exactly 0, not merely a small weight.
That data-dependence is precisely what "nonlinear" means here, and it's the
whole reason median-family reducers can do something no fixed-kernel filter
(Gaussian blur, box blur, any LTI system) can ever do.

### The `shorth` selection formula

Given sorted samples `y_(1) ≤ y_(2) ≤ ... ≤ y_(N)` and `h = ⌊N/2⌋ + 1`:

```
start* = argmin_{s=1..N-h+1} ( y_(s+h-1) - y_(s) )       # tightest run's start
output = mean( y_(start*) .. y_(start*+h-1) )
```

i.e. scan every window of `h` consecutive order statistics, pick the one with
minimum range, average it. Because `h > N/2`, this window is guaranteed to
contain a **strict majority** of the samples — so if the object occupies
fewer than half the frames at a pixel, the tightest majority run is
necessarily drawn from background-only samples, and the object's minority of
samples (which sit apart from that tight cluster) are excluded entirely.

### Why the `median` failure mode specifically needs even N

For **odd** N, the median is a single order statistic `y_((N+1)/2)` — one
actual sample, no averaging, so it either *is* a background sample or *is*
an object sample; there's no blending. For **even** N, the definition is the
mean of `y_(N/2)` and `y_(N/2+1)` — two *different* order statistics — and if
the object's population straddles that N/2 boundary (occupies close to, but
not exactly, half the sorted values), those two middle values can come from
different populations, and *that specific* average is where the ghost comes
from. This is a precise, checkable claim — good to have ready verbatim if
pressed on "why even N specifically."

### Where the border-fallback mask matters more here than on Page 3

`alignment_valid_mask` (see
[06-confidence-and-metrics.md](06-confidence-and-metrics.md)) excludes the
band of pixels near the border that at least one frame's circular shift
wrapped content into. For object removal this is doubly important: a wrapped
strip is not just "slightly wrong," it can itself look like a spurious
transient the reducer has to reject, so trimming to `valid_box` keeps the
displayed "plate" honest.

## Judges will probably ask

- **"Isn't this just Photoshop's content-aware fill?"** — No: content-aware
  fill synthesizes plausible texture from spatial neighbours in a *single*
  image; this method needs no synthesis at all — it has the *real* background
  value sitting in other frames of the *same* pixel location, recovered by a
  temporal (not spatial) statistic.
- **"What if the object never leaves that pixel across all your frames?"** —
  Then there genuinely is no background sample to recover there and the
  method fails honestly (the reducer returns the object's own value/an
  average of it) — worth admitting proactively; the fix is "capture more
  frames, or frames spread over more time," not a code change.
- **"Why default to shorth over plain median here specifically?"** — Directly
  answered in L2 above: it closes the even-N averaging gap that lets an
  object survive as a faint ghost.
- **"Could you do this with a low-pass filter in time instead?"** — No — see
  the L3 LTI argument: any linear filter, temporal low-pass included, can only
  *attenuate* an outlier, never remove it exactly; the "compare linear vs.
  nonlinear" panel shows the resulting ghosting directly.
