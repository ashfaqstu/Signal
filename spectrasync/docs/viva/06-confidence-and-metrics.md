# 6. Shared infrastructure — confidence, metrics, valid-region masks

Code: [`spectrasync/core/metrics.py`](../../spectrasync/core/metrics.py),
[`spectrasync/core/transform.py`](../../spectrasync/core/transform.py)
(mask functions)

Every page reports numbers built from this module. It's worth having this as
its own answer set because a judge who pokes at "how do you know it worked"
on *any* page is really asking about the functions documented here.

## Why a shift/registration estimate needs a confidence number at all

`phase_correlation` and `estimate_rotation_scale` **always** return *some*
peak — even correlating two completely unrelated images, or a flat grey
image against itself, produces a location of maximum value, because
`argmax` never fails. Nothing about the algorithm itself distinguishes "this
peak is a real, confident lock" from "this peak is noise that happened to be
slightly larger than the rest." A quality/confidence metric is therefore not
an optional nicety — without one, a registration pipeline has no way to
*know* it failed, which matters enormously for the applied features (a
misaligned frame silently corrupts a stack/background plate).

## The three peak-quality metrics (`peak_metrics`)

All three are computed from the same correlation surface, after rolling the
peak to the array centre first (so the "exclusion box" below can't wrap
around the toroidal DFT edge):

- **Peak height** — the raw value at the correlation maximum. With `beta=1`
  normalisation, a perfect match approaches 1.0 (a genuine impulse). Cheap,
  but on its own does not separate "featureless" from "unrelated" images
  (both give a small peak).
- **PSR (peak-to-sidelobe ratio)** — mask out an `(2·exclude+1)²` box around
  the peak (default 11×11), compute the mean `μ` and std `σ` of everything
  *outside* that box, then `PSR = (peak − μ) / σ`. A statistical "how many
  sidelobe-standard-deviations above the noise floor is this peak" score.
- **Peak ratio** — highest peak ÷ second-highest peak **outside** the
  exclusion box. **This is the metric actually used for accept/reject
  decisions** throughout the project (`register_many`'s `min_ratio` gate,
  `register_pair`'s `auto` mode threshold, the "N/M frames locked" UI
  readouts).

Measured reference values on 256×256 crops (yours will differ with content —
worth having your own numbers from your own dataset, but useful to quote the
shape of the pattern):

| case | peak | PSR | peak ratio |
|---|---|---|---|
| clean overlapping crops | 0.87 | 460 | 92 |
| same pair + noise (σ=0.15) | 0.09 | 24 | 4.2 |
| featureless target (flat grey) | 0.024 | 6.2 | 1.08 |
| two unrelated images | 0.020 | 5.1 | 1.04 |

Note how little separation `peak` and `PSR` give between the last two rows —
both metrics are "small but nonzero" for both a bad-but-real registration
attempt and a pair with no relationship at all. **`peak ratio` is the only
one of the three that cleanly separates a real lock (≥ 2, generally ≥ 4 used
as a strict "trust it" cutoff) from no lock (≈ 1.0–1.2)** — because it asks a
sharper question: not "is the peak tall," but "is the peak *singular*," i.e.
does the correlation surface have exactly one dominant candidate rather than
several comparably-sized ones. This is why it, not peak height, drives every
automatic decision in the codebase.

Bonus fact worth having ready: `stats.polarity` (sign of the raw peak) is
also reported — a **negative** peak means the pair has inverted contrast
(e.g. a photographic negative), located correctly anyway because the peak
search uses `argmax(|corr|)`.

## Where peak ratio drives actual decisions

- `register_pair(mode="auto")`: runs translation-only first; if
  `t.stats.ratio < 4.0`, retries with full similarity (Fourier-Mellin)
  registration and keeps whichever gives better NCC on a centre crop.
- `register_many(..., min_ratio=1.5, on_fail=...)`: any frame whose peak
  ratio falls below `min_ratio` is treated as **not locked** — the caller can
  choose to keep it unshifted (`"identity"`, flagged), drop it from the
  sequence (`"drop"`), or trust it anyway (`"keep"`, opt-in only). This is
  the gate behind every "N/M frames locked" number shown on Pages 3–5.
- The measured claim behind this gate: on a near-textureless synthetic image
  at noise σ=0.12, phase correlation fails on roughly half the frames — and
  reliably reports a ratio near 1.07 on those failures, so the failures are
  *detectable*, not silent. On real photographic content at the same noise
  level it did not fail once in 60 trials (median ratio 4.9) — i.e. the
  metric's discriminating power was itself empirically validated, not just
  assumed.

## Image-similarity / quality metrics

- **RMSE / PSNR** — `psnr(a, b, mask) = 20·log10(peak / rmse)`, the standard
  log-scale error metric; `peak=1.0` here because images are float in
  `[0,1]`. Used throughout to quantify "how much did alignment/stacking/
  removal actually improve the image," always evaluated **only inside a
  `mask`** — see below for why that matters.
- **NCC (normalised cross-correlation)** — `Σ(a−ā)(b−b̄) / (‖a−ā‖·‖b−b̄‖)`,
  in `[-1, 1]`, mean-subtracted and magnitude-normalised — a
  brightness/contrast-invariant structural similarity score (same spirit as
  phase correlation's own magnitude normalisation, applied here as a
  *scoring* metric rather than an estimation trick). Used to pick between
  registration candidates (e.g. the 180° Fourier-Mellin ambiguity, the
  `auto`-mode translation-vs-similarity choice) precisely because it doesn't
  care about exposure differences between frames.
- **`estimate_noise`** — Immerkaer's no-reference noise estimator; see
  [03-stacking.md §L3](03-stacking.md#noise-estimation-without-a-clean-reference)
  for the exact formula and rationale.
- **`angle_error_deg` / `percent_error` / `shift_error`** — small
  ground-truth comparison helpers used only in synthetic/known-answer modes.
  `angle_error_deg` specifically wraps at ±180° before taking the absolute
  difference (a naive subtraction would say 179° and −179° are 358° apart
  instead of the correct 2°) — a good "attention to detail" answer if asked
  why it isn't a one-line subtraction.
- **ITF (inter-frame transformation fidelity)** — mean PSNR between
  consecutive frames (with a border margin excluded); higher means a
  sequence is "steadier" frame-to-frame. Used as a general sequence-quality
  summary, most relevant to video input.

## Why every measurement is masked: the valid-region functions

A circular Fourier shift **wraps** content from the opposite edge; a
rotation/scale warp can sample **outside** the source image entirely (filled
with zero by `bilinear_sample`'s clamping). Either way, a strip of pixels
near the border of an aligned image is not real, transformed scene content —
it's filler — and including it in any metric or display silently corrupts
the number. Measured cost of getting this wrong on a real photo, quoted
directly in the code: a mask mismatch reported **18.9 dB instead of the true
88.8 dB** — not a rounding error, a completely different conclusion.

- **`valid_mask(shape, dy, dx)`** — which pixels are real after a raw
  `fourier_shift(img, dy, dx)`. **Direction-sensitive**: this describes the
  result of shifting *by* `(dy, dx)`, not the mask for undoing an estimate
  (which shifts by the *negative*) — mixing the two up is exactly the 18.9 dB
  bug quoted above.
- **`alignment_valid_mask(shape, angle, scale, dy, dx)`** — the correct mask
  for anything produced by `apply_registration` (the actual alignment path
  used everywhere in the UI): combines (1) which output pixels' *unwarp*
  sampled inside the original source image, found from the sampling
  coordinates themselves — not from pixel values, so it's exact even for a
  uniform-colour image — with (2) the circular-wrap band from the translation
  step, applied in the correct order (warp mask translated first, *then*
  ANDed with the wrap band), plus a small erosion for safety margin.
- **`common_valid_mask`** — ANDs `alignment_valid_mask` across an entire
  aligned sequence: the region valid in *every* frame, used to decide what
  region a stack/removal/highlight result can honestly be trusted in.
- **`valid_box` / `mask_from_box` / `border_mask`** — turn a validity mask
  into the largest inscribed axis-aligned rectangle (greedy edge-trimming,
  exact for translation-only stacks) for cropping the displayed "headline"
  result, or provide a simple fixed-margin mask for synthetic ground-truth
  comparisons.

## Judges will probably ask

- **"How do you know an alignment succeeded, not just that it ran?"** — Peak
  ratio, thresholded at (typically) 1.5–4.0 depending on context; below that
  the frame is flagged, not silently trusted.
- **"Why peak ratio and not peak height as the primary confidence signal?"**
  — Peak height alone can't separate "no real signal, correlation surface is
  flat and noisy" from "real but weak/noisy match," because both give a
  small absolute peak; peak ratio asks whether that peak *stands out from its
  own sidelobes*, which is the more scene-independent question.
- **"Why mask every metric — isn't that hiding bad results?"** — The
  opposite: without masking, a circular-shift wraparound or an out-of-bounds
  warp sample contaminates the metric with filler content that was never
  part of the actual alignment question, producing a *wrong* number, not a
  conservative one — the 88.8 dB vs 18.9 dB example is the concrete proof.
