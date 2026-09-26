# 3. Stacking — multi-frame noise reduction (Applied feature 1)

Code: [`spectrasync/features/stacking.py`](../../spectrasync/features/stacking.py),
[`spectrasync/features/temporal.py`](../../spectrasync/features/temporal.py) ·
UI: [`app/pages/p3_stacking.py`](../../app/pages/p3_stacking.py)

## L1 — High-level algorithm

**Question:** given several noisy photos of (nominally) the same static
scene, produce one cleaner image.

**Algorithm family:** **align + reduce**. This is the first of three pages
built on one shared engine (`features/stacking.py::stack`):

1. **Align** every frame onto one reference frame using Page 1's
   `phase_correlation` (or Page 2's Fourier-Mellin, if requested) — this is
   the "translation" work already covered.
2. Stack the aligned frames into a 3-D array `(N, H, W[, C])` and **reduce**
   along the frame axis at every pixel independently, with a chosen
   statistic.

The key reframing: after alignment, **each pixel location holds an N-sample
1-D signal in time** — the same static scene value corrupted by independent
per-frame noise. Reducing that 1-D signal to a single number is a classical
statistical-estimation problem, and the reducer chosen is the *entire*
difference between "denoise" (Page 3), "remove moving things" (Page 4) and
"detect moving things" (Page 5) — same engine, different question.

This page's reducer of choice is **mean**: for i.i.d. zero-mean sensor noise,
averaging N independent samples of the same true value is the
minimum-variance unbiased estimator (Gauss-Markov), and it is exactly what
the theoretical +10·log10(N) dB gain formula assumes.

## L2 — The pipeline and every UI option

### Pipeline, in code order (`stack`)

```
aligned, results = register_many(frames, reference=0, mode)     # Page 1/2's engine, N times
out               = reduce(aligned, reducer)                     # pixelwise statistic across frames
m                 = AND of each frame's alignment_valid_mask      # pixels valid in EVERY frame
out               = where(m, out, reduce(un-aligned frames, reducer))  # fallback at the border
```

The border fallback matters: outside the common-valid region, at least one
frame's alignment shift would have wrapped content in circularly — mixing
that into the reduction would create visible ring/ghost artefacts at the
edges, so that thin strip instead falls back to reducing the *raw, unaligned*
frames (better than showing wrapped garbage, though of course unaligned
there too — which is why the UI additionally reports/crops to `valid_box`,
the largest common rectangle, for the "headline" view).

### UI option: **Source — Photo set vs. Synthetic**

- **Photo set** — your own uploaded noisy burst; optionally also upload a
  clean reference shot (own exposure/frame) purely to *measure* PSNR gain —
  it is registered onto the stack's own output first
  (`align_reference_to_output`) because it was captured independently and is
  not in the same pixel frame as the stack.
- **Synthetic** — one clean image, N noisy+shifted copies generated
  on-the-fly (`SyntheticSource`) with a *known* Gaussian noise σ and a known
  max shift, so the measured PSNR gain can be checked directly against the
  **theoretical** gain formula (see L3) — this is the accuracy-verification
  mode.

### UI option: **Reducer** (`REDUCERS` registry — this is the important control)

| reducer | what it computes per pixel | when it wins | cost of that choice |
|---|---|---|---|
| `mean` | arithmetic mean of the N samples | **Gaussian/white sensor noise, no outliers** — the statistically optimal estimator; gain = **+10·log10(N) dB** | zero outlier rejection: one bad/misaligned/occluded frame corrupts the result |
| `median` | middle order statistic (mean of the two middle values if N even) | any outlier-contaminated signal (e.g. a person walked through one frame) | about **1.96 dB worse** than mean on pure Gaussian noise, because `var(median) → (π/2)·var(mean)` as N grows |
| `mode` | the most frequent value, via quantising to `levels` bins and averaging the raw samples inside the winning bin | scenes where one value is genuinely far more common than any other and you want the literal statistical mode rather than the middle value | needs enough samples per bin to be meaningful; a discretisation choice (`levels`, default 256 ≈ 8-bit) |
| `sigma_clip` | iterated mean with samples beyond `sigma·σ` of the running mean excluded, 3 passes by default | wants most of `mean`'s Gaussian-noise performance *and* some outlier rejection | a compromise — not as sharp against outliers as `median`/`shorth`, not as optimal as `mean` on pure noise |
| `shorth` | average of the tightest majority-sized (`N/2+1`) contiguous run of sorted values (Rousseeuw's "shortest half") | see [04-object-removal.md](04-object-removal.md) — this is that page's default, included here for comparison | slightly more compute than `median` (a small sliding-window search over sorted values) |
| `trimmed_mean` | mean after dropping the top/bottom `trim/2` fraction of samples | middle ground between mean and median, tunable | needs enough frames for trimming to leave anything |
| `min` / `max` | pixelwise minimum / maximum across frames | removing bright transients (`min`) or dark ones (`max`, e.g. star-trail style stacking) | extremely sensitive to any single outlier in the *other* direction |
| `weighted_mean` | mean weighted per frame (e.g. by alignment confidence) | frames of unequal trustworthiness | needs a sensible weight source |
| `fourier_snr` | **frequency-domain** Wiener-style combination: per-bin SNR gain `signal/(signal+noise)` applied to the mean spectrum, noise floor estimated from the high-frequency tail | showcases that stacking need not happen in the spatial domain at all | more expensive (extra FFTs); a genuinely different *mechanism*, not just a different order statistic |

The `compare all reducers` panel runs several of these side by side against
the *same* aligned stack and (when a clean reference is known) reports
measured PSNR gain next to the theoretical prediction — this is the
figure that most directly demonstrates "mean is optimal for pure noise,
median/shorth trade some of that for robustness."

### UI option: **Align before reducing**

Turning this off skips step 1 entirely and reduces the raw, unregistered
frames. Even a handheld camera's natural micro-shake is enough to smear detail
when reduced without alignment — this toggle exists specifically so you can
show a judge *why* alignment is a precondition for stacking to work at all,
not an optional nicety.

### UI option: **Colour**

Registration always runs on **luma** (`to_gray`) even for colour frames — a
single scalar per pixel is what phase correlation needs — and the *same*
recovered shift is then applied identically to R, G and B, so channels stay
perfectly co-registered (no colour fringing at edges).

### UI option: **working size (longest side, px)**

Downscaling before stacking has a side effect worth knowing: downscaling
itself *also* averages several sensor pixels into one output pixel, which
reduces noise on its own (independent of the multi-frame stacking gain). The
UI explicitly warns about this — keep working size close to the frames' own
resolution if you want the demonstrated gain to be attributable to *stacking*
specifically, not to downscaling.

## L3 — The mathematics

### Why mean is optimal for Gaussian noise

Model: `x_i = μ + n_i`, `n_i ~ N(0, σ²)` i.i.d. across `i = 1..N` frames, `μ`
the true (static) pixel value. The sample mean
`x̄ = (1/N)Σx_i` is unbiased (`E[x̄] = μ`) with variance

```
Var(x̄) = σ²/N
```

By the Gauss–Markov theorem this is the minimum-variance unbiased linear
estimator, and (Cramér–Rao, under Gaussianity) the minimum-variance estimator
full stop. In decibels, since power ∝ variance and PSNR is a log ratio,

```
gain = 10·log10( σ²_single / σ²_stack ) = 10·log10( σ²/(σ²/N) ) = 10·log10(N)
```

— exactly the `theoretical_gain_db` formula used on the page.

### Why median costs ~1.96 dB

For i.i.d. Gaussian samples, as `N → ∞` the asymptotic variance of the sample
median is `Var(median) → (π/2)·(σ²/N)`, i.e. `π/2 ≈ 1.5708×` the mean's
variance. In dB:

```
10·log10(π/2) ≈ 1.96 dB
```

so `theoretical_gain_db(N, "median") = 10·log10(N) − 10·log10(π/2)`. This is
the "price" paid for gaining outlier robustness — worth stating explicitly:
the trade is not free, it's precisely quantifiable.

### Why no *linear* (LTI) filter can reject an outlier

Any linear time-invariant combination `Σ w_i x_i` of the N samples (mean
included) necessarily gives the outlier frame some nonzero weight `w_i`, so
its contribution is only ever *attenuated*, never *removed* — it always
leaves a residual "ghost" proportional to that weight. Only a **nonlinear**
statistic — an order statistic like median, or `shorth`'s tightest-run
selection — can produce a weight of *exactly zero* for a sample identified as
an outlier. This is the formal justification for why Page 4 must switch away
from `mean`.

### Noise estimation without a clean reference

When no clean reference is uploaded, per-image noise σ is estimated by
Immerkaer's method (`core.metrics.estimate_noise`): convolve with the 3×3
kernel `[[1,-2,1],[-2,4,-2],[1,-2,1]]` (a discrete Laplacian-of-Laplacian),
which cancels smooth image structure and leaves mostly noise energy, then

```
sigma = sqrt(pi/2) * mean(|I * kernel|) / 6
```

Real texture always leaks through this a little, so even a clean photo reads
a small positive floor rather than exactly zero — worth knowing so a
"why isn't σ_out = 0 on a clean image" question doesn't catch you off guard.

### `fourier_snr` (the one non-order-statistic reducer)

Rather than combining *pixel values*, this reducer combines *frequency
content*, per the matched-filter / Wiener-filter argument:

```
power(u,v)  = mean_i |F_i(u,v)|^2                    # average power spectrum across frames
noise       = mean(power) over the high-frequency tail (>= noise_band cyc/px)
signal(u,v) = max(power(u,v) - noise, 0)
gain(u,v)   = signal / (signal + noise)                # Wiener gain, per bin
out         = real( ifft2( mean_i(F_i) * gain ) )
```

The assumption: a natural image has almost no true signal energy at very high
spatial frequencies, so that tail is a good proxy for the noise floor at
*every* frequency; bins where the estimated signal is weak relative to that
floor are attenuated before the inverse transform. This is literally the same
family of idea as phase correlation's `beta` — weighting frequency
contributions by confidence — applied to combining frames instead of finding
a shift.

## Judges will probably ask

- **"Why does alignment come before reducing, and what happens if you skip
  it?"** — Any unregistered micro-shift between frames means a given output
  pixel is combining different scene points across frames, which blurs detail
  regardless of which reducer is used; the "align before reducing" toggle
  demonstrates this directly.
- **"Why is mean the theoretically 'right' answer, but the project defaults
  to shorth/median elsewhere?"** — Because "right" depends on the noise
  model: mean is optimal for the additive-Gaussian, no-outlier case (this
  page); once a moving object injects large, non-Gaussian outliers into a
  fraction of the frames (Pages 4–5), the optimality argument for mean no
  longer holds and a robust/order statistic wins instead.
- **"How much gain did you actually measure vs. the formula predicts?"** —
  Have your own number ready from a synthetic run at a specific N and σ;
  the page reports both side by side for exactly this comparison.
