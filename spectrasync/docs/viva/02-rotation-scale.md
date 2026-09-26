# 2. Rotation & Scale — Fourier-Mellin (`func_rotation_and_scale`)

Code: [`spectrasync/core/mellin.py`](../../spectrasync/core/mellin.py),
[`spectrasync/core/logpolar.py`](../../spectrasync/core/logpolar.py),
[`spectrasync/core/register.py`](../../spectrasync/core/register.py) ·
UI: [`app/pages/p2_rotation_scale.py`](../../app/pages/p2_rotation_scale.py)

## L1 — High-level algorithm

**Question:** given two photos of the same scene, one rotated and zoomed
relative to the other (and possibly also translated), recover the rotation
angle and scale factor.

**Algorithm family:** **Fourier-Mellin registration**. It reuses the exact
same `phase_correlation` primitive from Page 1 **three times**:

1. FFT the **magnitude** spectrum of both images (translation drops out here
   automatically — see why below).
2. Resample both magnitude spectra onto a **log-polar grid**
   `(log ρ, θ)`. In these coordinates a rotation of the original image becomes
   a pure vertical **shift along θ**, and a scale becomes a pure horizontal
   **shift along log ρ**.
3. Run phase correlation *on the two log-polar images* — the exact same
   function as Page 1 — to read off that shift, i.e. (angle, scale), in one
   shot.
4. Undo the recovered rotation/scale, then run phase correlation a *third*
   time to get the residual translation.

So the "new" algorithm here is not a new correlation method at all — it is a
**coordinate change** (Cartesian → log-polar) that turns rotation and scaling
into the same kind of "find the shift" problem already solved on Page 1, plus
one extra normalisation step (taking the magnitude first) that buys shift
invariance for free.

## L2 — The pipeline and every UI option

### Pipeline, in code order

```
M1, M2   = spectrum_for_mellin(ref), spectrum_for_mellin(mov)   # |FFT|, log-compressed, emphasised
L1, L2   = logpolar(M1, ...), logpolar(M2, ...)                  # Cartesian -> (log rho, theta)
corr     = correlation_surface(L1, L2, window="none", beta=beta)  # SAME phase-correlation core
(d_theta, d_rho) = argmax + subpixel, unwrapped
angle    = d_theta * (180 / n_theta)                              # direct sign
scale    = exp(-d_rho * log_step)                                 # INVERTED sign (see L3)
```

Then the **registration facade** (`register.py`) wraps this:

```
for each preset in PRESETS (sharp -> medium -> robust):
    (angle, scale) = estimate_rotation_scale(..., preset settings)
    for candidate_angle in (angle, angle + 180):     # 180-deg ambiguity, see below
        un = unwarp_similarity(mov, candidate_angle, scale)
        t  = phase_correlation(ref, un)               # translation, SAME primitive again
        score = t.stats.peak
    keep the (preset, angle-candidate) combination with the best FINAL score
```

`spectrum_for_mellin` itself: optional Gaussian pre-smoothing → subtract mean
→ optional window → `|FFT|` → `fftshift` (put DC at the centre) →
`log1p` compression → multiply by a **Reddy–Chatterji emphasis filter**
(`(1−X)(2−X)`, `X = cos(πy)cos(πx)` on a centred `[-0.5,0.5]` grid) that
suppresses the huge low-frequency blob that would otherwise dominate the
log-polar correlation and drown out the higher-frequency structure that
actually encodes rotation/scale detail.

### Why magnitude-first buys translation-invariance

From the shift theorem (Page 1): `F2 = F1 · e^{-j2π(u·dy+v·dx)}`, so
`|F2| = |F1|` **exactly**, for *any* translation. Working on the magnitude
spectrum from the very first step means a translated-*and*-rotated-*and*-
scaled pair still gives magnitude spectra related by rotation/scale alone —
translation is already gone before log-polar resampling even happens. This is
why the UI note correctly says "translation between the two images does NOT
need to be removed first — that is the entire point of working on the
magnitude spectrum."

### UI option: **Two photos vs. Synthetic**

- **Two photos** — measures the unknown rotation/scale/shift between two of
  your own uploaded images; there is no ground truth, so the page reports the
  estimate and its confidence, and lets you *see* the quality via the
  before/after overlay.
- **Synthetic** — takes one image, applies a *known* `warp_similarity(angle,
  scale, dy, dx)` (with optional Gaussian noise), and asks the pipeline to
  recover exactly that. This is the accuracy-verification mode: it reports
  `angle_error_deg` and `percent_error` against the known truth. Measured
  headline numbers on clean synthetic pairs (n_theta=720, n_rho=512):
  **rotation max error 0.013°, scale max error 0.12%**, usable scale range
  **0.7×–2.0×** (below ~0.65× the estimate collapses toward 1.0).

### UI option: **Robust: try all presets**

Off → only the `sharp` preset runs. On (default) → all three `PRESETS` run and
the best-**scoring** one is kept, where "best" is judged by the **final
alignment quality** (`t.stats.peak`, the translation peak height *after*
undoing that preset's candidate rotation/scale) — never by an intermediate
confidence number from the log-polar stage itself. This "score by the
outcome" design is deliberate: an intermediate metric can be misleadingly high
on a preset that actually produced the wrong angle.

| preset | `r_frac` (fraction of spectrum radius used) | `presmooth` (Gaussian blur, px) | `beta` | intent |
|---|---|---|---|---|
| `sharp` | 1.0 (full spectrum) | 0.0 | 1.00 | cleanest, most accurate on low-noise images |
| `medium` | 0.8 | 1.0 | 0.85 | drops the noisiest outer ring, a little whitening back-off |
| `robust` | 0.6 | 1.5 | 0.70 | most noise-tolerant, least resolution |

`r_frac < 1.0` deliberately **discards the outermost (highest-frequency)
ring** of the magnitude spectrum before log-polar resampling — that ring is
usually the noisiest part of a real photo's spectrum, so trading it away buys
robustness at the cost of some available scale range. Lower `beta` backs off
whitening exactly as on Page 1, for exactly the same noise-robustness reason.
Verified: the 3-preset ladder passes 10/11 stress cases (including 180° flips
and rotation+scale at noise σ = 0.10) that no single preset manages alone.

### UI option: **angular bins (`n_theta`) / log-radius bins (`n_rho`)**

These set the resolution of the log-polar grid, i.e. the resolution of the
phase-correlation peak measured on that grid — which directly sets the
*angular* and *scale* resolution of the whole estimate:

- `n_theta` bins cover `[0°, 180°)`, so **resolution ≈ 180° / n_theta** per bin
  before sub-pixel refinement (e.g. 720 bins → 0.25°/bin coarse resolution;
  the sub-pixel refiner then reads finer than one bin).
- `n_rho` bins are spaced **logarithmically** in radius, so more bins means a
  finer log-radius step (`log_step = ln(r_max/r_min)/n_rho`), i.e. finer scale
  resolution.

More bins = better resolution but a larger log-polar image to correlate = more
compute. The UI exposes discrete steps (180/360/720/1080 for θ,
128/256/512/768 for ρ) so you can *demonstrate* the resolution/cost trade-off
live.

### UI option: **working size (longest side, px)**

Downscales the uploaded photos before anything else (never crops). Two
effects: faster FFTs (cost scales with `H·W·log(H·W)`), and — because both
images are downscaled by the same factor — the recovered scale ratio is
unaffected, only absolute pixel-shift precision is traded for speed.
~700 px is stated as "plenty for sub-degree accuracy" for this dataset.

### UI option: **Reducer/Overlay controls** — shared with Page 1

The `anaglyph`/`checkerboard`/`blend`/etc. overlay dropdown here is the exact
same `OVERLAYS` registry described in
[01-translation.md](01-translation.md#ui-option-overlay-anaglyph-checkerboard-blend-difference-split).

## L3 — The mathematics

### Rotation and scale of the magnitude spectrum

If `f(x,y)` is rotated by `θ` and scaled by `s`, the Fourier transform obeys:

```
f(x,y) rotated by θ and scaled by s   <=>   |F(u,v)| rotated by the SAME θ and scaled by 1/s
```

(scale is *inverted* — zooming into the image spreads its spatial detail out,
which *compresses* the corresponding spectrum; this is the ordinary Fourier
scaling property `f(sx) ↔ (1/|s|)F(u/s)` applied radially.) Translation
contributes only a phase term and, per the shift theorem, is invisible in
`|F|` — so this property is completely independent of any translation between
the two photos, exactly as claimed in L2.

### Log-polar coordinates turn both into shifts

Define polar coordinates `x = ρ·cosθ, y = ρ·sinθ` on the (centred) magnitude
spectrum, then substitute `ρ = e^ℓ` (i.e. `ℓ = ln ρ`). A rotation of the image
by `Δθ` maps `θ → θ+Δθ` — a pure **additive shift along the θ axis**. A scale
of the image by `s` maps the spectrum's radius by `1/s`, i.e.
`ρ → ρ/s`, i.e. `ℓ → ℓ − ln s` — a pure **additive shift along the log-radius
axis `ℓ`**. Two independent, decoupled 1-D shift problems, exactly the
structure `phase_correlation` already solves (as a joint 2-D shift, here on
the `(ℓ, θ)` plane instead of `(y, x)`).

### Reading the shift back out (sign conventions, empirically calibrated and tested)

```
angle_deg =  d_theta * (180 / n_theta)                    # DIRECT sign
scale     =  exp( - d_rho * log_step )                     # INVERTED sign
```

The angle sign is direct: a real +12° rotation produces a +12° raw estimate.
The scale sign is inverted because (as above) magnifying the image by `s`
*shrinks* its spectrum by `1/s`, so a genuine scale of `1.20` first shows up as
a log-polar column shift equivalent to a raw factor of `0.83` (`= 1/1.20`)
before the `exp(-...)` inversion corrects it back to `1.20`.

### Only known modulo 180°

The magnitude spectrum of any real-valued image is **centrosymmetric**:
`|F(u,v)| = |F(-u,-v)|`, because a real image's full (complex) spectrum obeys
Hermitian symmetry (`F(-u,-v) = conj(F(u,v))`), and taking the magnitude
erases the conjugation. A rotation by `θ` and by `θ+180°` therefore produce
**indistinguishable** magnitude spectra — the log-polar stage genuinely cannot
tell a picture turned 30° from the same picture turned 210°. `register_pair`
resolves this the only honest way available: it tries **both** candidate
angles, applies each with `apply_registration`, runs the real translation
phase-correlation on each candidate, and keeps whichever produces the
stronger, more confident alignment.

### Applying the recovered transform

Order matters and is fixed project-wide (`apply_registration`):
**1) un-rotate/un-scale about the centre, 2) then translate.** The rotation/
scale stage is measured with the images effectively centred on their own
optical centre; translation is measured *after* undoing rotation/scale, so it
is expressed in the un-rotated frame — applying it before un-rotating would
shift along the wrong (rotated) axes.

`warp_similarity`/`unwarp_similarity` implement this with **inverse mapping**:
for every *output* pixel, compute where it came from in the *input* and
bilinearly sample there (`bilinear_sample`) — the only way to produce a warped
image with no holes. `unwarp_similarity(img, θ, s) = warp_similarity(img, −θ,
1/s)`, making it the exact algebraic inverse of the forward warp used to build
synthetic test cases, so a synthetic round-trip is exact up to interpolation
error.

### Complexity / limits

- Cost: one 2-D FFT per image, plus one bilinear log-polar resample
  (`O(n_theta · n_rho)` samples), plus one more `phase_correlation` — still
  `O(N² log N)`-dominated, i.e. no asymptotic cost over Page 1's method, only
  a constant-factor increase for the extra passes.
- Scale range: roughly **0.7×–2.0×** reliably; outside that the log-polar
  sampling runs out of usable spectrum overlap.
- A pure rotation/scale/translation ("similarity") model cannot express
  **perspective** change, which real hand-held photos always contain a little
  of — this is *why* the "AFTER" overlay on real photo pairs is close but
  never pixel-perfect, and is worth saying proactively.

## Judges will probably ask

- **"Why the magnitude spectrum and not the raw image?"** — Because `|F|` is
  translation-invariant (shift theorem) and transforms predictably (same
  rotation, inverse scale) under rotation/scale of the original image — so
  translation is solved for free and doesn't contaminate the rotation/scale
  estimate.
- **"Why log-polar and not plain polar?"** — Plain polar turns rotation into a
  shift but leaves scale as a *multiplicative* stretch of the radius axis
  (still needs a search). Taking the **log** of the radius turns that
  multiplicative stretch into an *additive* shift too — the same kind of
  problem phase correlation already solves, on both axes at once.
- **"Why is the angle ambiguous by 180°, and how do you fix it?"** — Because
  the magnitude spectrum of any real image is centrosymmetric (Hermitian
  symmetry of the full transform, minus the conjugate phase). Fixed by trying
  both candidates and keeping whichever gives the stronger translation-peak
  after alignment.
- **"How do you choose between the three presets, and isn't that cheating /
  overfitting to the test?"** — No: they're scored by the *outcome* (final
  alignment peak on real data, not by comparison to a known answer), so the
  selection generalises to genuinely unknown inputs; that's precisely why it's
  10/11 robust across a spread of stress cases rather than tuned to one.
