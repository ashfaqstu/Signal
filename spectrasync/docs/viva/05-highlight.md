# 5. Highlight — change detection & outlining (Applied feature 3)

Code: [`spectrasync/features/highlight.py`](../../spectrasync/features/highlight.py),
[`spectrasync/core/filters.py`](../../spectrasync/core/filters.py) ·
UI: [`app/pages/p5_highlight.py`](../../app/pages/p5_highlight.py)

## L1 — High-level algorithm

**Question:** given the same kind of photo set as Page 4, don't just remove
the moving objects — mark *where* each one is, in every photo.

**Algorithm family:** this page runs **Page 4's entire pipeline first** to
get a clean background plate, then treats the problem as classical
**frequency-domain change detection**: every step from here on is a
*multiplication in the FFT domain* (a filter), which is exactly the
convolution theorem's "convolution in space = multiplication in frequency"
idea, deliberately kept inside that one syllabus concept rather than
reaching for ad-hoc spatial-domain image processing (contour tracing,
morphology libraries, edge detectors from a CV library):

```
background = remove_moving_objects(frames)          # Page 4's engine, reused wholesale
score      = band-pass( |frame - background| )       # convolution theorem: filtering by multiplication
mask       = adaptive_threshold(score)                # mean + k*sigma
mask       = low-pass(mask) > level                   # "clean" the mask — filtering again
outline    = |gradient(mask)|                          # DIFFERENTIATION PROPERTY of the FT
boxes      = connected components of mask              # BFS flood fill, for the bounding boxes only
```

So the "new" algorithmic content on this page is two textbook Fourier-domain
operations applied to a change map: **band-pass filtering** to isolate the
right spatial-frequency band of "object-sized" change, and **spectral
differentiation** to extract an edge/outline without any contour-tracing
algorithm at all.

## L2 — The pipeline and every UI option

### Pipeline, in code order (`highlight`)

```
diff   = to_gray(frame) - to_gray(background)          # LUMA only, even for colour input
score  = DETECTORS[detector](diff, **kw)                 # bandpass / lowpass / raw
score  = score * valid                                    # never detect in the wrapped border
thr    = mean(score[valid]) + k * std(score[valid])       # adaptive threshold
mask   = gaussian_blur(score > thr, smooth) > 0.5          # "clean" the binary mask
line   = (|gradient(mask)| / max) > width                  # outline via differentiation
overlay= tint(line, colour, base=frame)                    # colourised line drawn over the ORIGINAL photo
boxes  = bounding_boxes(mask, min_area)                    # BFS flood fill, sorted by area
```

Two design points worth stating proactively:
- **Detection always runs on luma**, even for a colour photo — colour carries
  no extra information for "did this pixel change," and mixing 3 channels
  through a 2-D FFT-based filter would need per-channel handling for no
  benefit; only the *overlay drawing* is done in colour, over the original
  frame.
- The background plate is **Page 4's `remove_moving_objects` output**,
  computed once and shared across every frame's comparison — so every photo
  in the set is judged against the *same* fixed reference, not against its
  own neighbours.

### UI option: **Change detector** (`DETECTORS` registry)

| detector | transfer function | what survives |
|---|---|---|
| `raw` | none — `score = \|diff\|` | everything: real object edges *and* sensor noise *and* slow lighting drift, all mixed together — included specifically to show why filtering is necessary |
| `lowpass` | Gaussian low-pass (`exp(-0.5·(f/cutoff)²)`) on `\|diff\|` | smooths out high-frequency sensor noise, but does **not** reject slow lighting/exposure drift (which is itself low-frequency) — a simple baseline |
| `bandpass` (default) | difference of two Gaussian low-passes, `lowpass(high) − lowpass(low)` | keeps only the mid-band spatial frequencies characteristic of an object-sized blob; **rejects both** noise (above `high`) and drift (below `low`) in one multiplication |

*Why band-pass is the right shape, not just "a nicer low-pass":* an object's
edge, at a given size, has most of its energy in a bounded range of spatial
frequencies — too fine (pixel-level) is sensor noise, too coarse
(whole-frame-level, near-DC) is gradual lighting/exposure change rather than
a discrete object. A difference-of-Gaussians band-pass isolates exactly that
middle range with a single elementwise multiplication in the frequency
domain, rather than needing two separate filtering passes and a subtraction
in the spatial domain (though by the convolution theorem those are
equivalent operations — the FFT route is the efficient one here because the
same FFT of `diff` is reused for both Gaussians).

### UI option: **band low / band high (cyc/px)** — only shown for `bandpass`

Directly the two Gaussian cutoffs (`lowpass(shape, high) - lowpass(shape,
low)`), in cycles-per-pixel:
- **`low`** (default 0.02) — anything *below* this (very coarse, near-DC
  spatial variation — e.g. a cloud passing, a slow exposure shift) is
  subtracted away.
- **`high`** (default 0.20) — anything *above* this (fine, pixel-scale
  texture — sensor noise, compression artefacts) is attenuated.
- Narrowing the band tightens detection to a specific object size; widening
  it lets both drift and noise back in — a live, tunable demonstration of the
  band-pass trade-off.

### UI option: **threshold k (mean + k·sigma)**

`adaptive_threshold`: `threshold = mean(score) + k·std(score)`, computed only
over the `valid` region. This is a classical statistical outlier threshold —
assume the band-passed score is approximately noise-like away from real
objects, and flag anything more than `k` standard deviations above that
noise floor. **Smaller `k`** → more sensitive (more false positives from
residual noise); **larger `k`** → stricter (may miss faint/small objects).
Scene-independent by construction (it's relative to the scene's own measured
statistics, not an absolute pixel-value cutoff), which is why it's exposed as
the primary detection knob rather than a fixed number.

### UI option: **mask smoothing**

`clean_mask`: blur the *binary* mask with a Gaussian (`gaussian_blur`) and
re-threshold at `0.5`. This is exactly **morphological closing/opening
expressed as frequency-domain filtering** — no structuring-element library,
no explicit dilate/erode loop: blurring a 0/1 mask and re-cutting at the
midpoint fills small gaps (closing) and removes small speckle (opening) as a
side effect of low-pass smoothing acting on a step function. Higher values
merge nearby blobs and fill larger holes; `0` disables cleanup entirely.

### UI option: **min blob area (px)**

Passed straight to `bounding_boxes`: after flood-filling connected regions of
the mask (4-connected BFS, no scipy), any blob smaller than this pixel-area
threshold is discarded before boxes are drawn/counted. Pure post-processing
noise rejection at the "one detected object" level, separate from
`k`/`smooth`'s pixel-level rejection.

### The outline panel — worth walking through explicitly

The note on this page is one of the most quotable lines in the whole project:
*"The outline is not a contour-tracing algorithm: it is the gradient
magnitude of the mask, computed by multiplying by j2πu and j2πv in the
Fourier domain — the differentiation property of the transform."* See L3 for
the exact formula; in the UI, comparing `raw` vs `bandpass` detectors on the
same photo set is the clearest single before/after to show a judge.

## L3 — The mathematics

### Band-pass as a transfer function

```
lowpass(shape, cutoff)  = exp( -0.5 * (radial_freq / cutoff)^2 )     # Gaussian, in cycles/px
bandpass(shape,lo,hi)   = lowpass(shape, hi) - lowpass(shape, lo)
```

where `radial_freq[u,v] = hypot(fftfreq_H[u], fftfreq_W[v])` — the Euclidean
radial spatial frequency at each FFT bin, in the *unshifted* `np.fft` layout
so it multiplies a raw `fft2` result directly. Applying any filter is:

```
apply_filter(img, mask) = real( ifft2( fft2(img) * mask ) )
```

— i.e. filtering is literally elementwise multiplication in the frequency
domain, which by the **convolution theorem** is mathematically equivalent to
(but computationally far cheaper than) convolving `img` with the filter's
spatial-domain kernel: `f * h ⟺ F · H`.

### Gaussian blur = zero-phase filter (why a real Gaussian kernel is used for
mask-cleanup and not, say, a box filter)

`gaussian_blur` builds `exp(-2π²σ²(ky²+kx²))` directly in the frequency
domain. This transfer function is **real and symmetric** — it has zero
imaginary part everywhere — so applying it changes only the *magnitude* of
each frequency component, never its *phase*. This matters beyond mask
cleanup: it's the same reasoning used elsewhere in the project to explain why
blurring one image of a phase-correlation pair barely shifts the estimated
peak location (phase, where the shift information lives, is untouched) even
though it collapses the peak's sharpness (magnitude, which the beta
normalisation on Page 1 throws away anyway).

### The differentiation property (the outline's actual mechanism)

For a 1-D signal, differentiating in space corresponds to multiplying by
`j2πu` in frequency (direct consequence of differentiating the Fourier
integral `f(x) = ∫F(u)e^{j2πux}du` under the integral sign):

```
d/dx f(x)  <=>  j2πu · F(u)
```

Extended separably to 2D and implemented exactly as written:

```
gy = real( ifft2( F * (j2π·ky) ) )      # d/dy
gx = real( ifft2( F * (j2π·kx) ) )      # d/dx
|grad| = hypot(gy, gx)
```

applied to the (lightly pre-smoothed, to tame ringing on a hard binary edge)
mask. The result is exactly the gradient-magnitude image classical edge
detectors (Sobel, Prewitt, Canny's first stage) approximate with small
spatial kernels — computed here as an *exact*, closed-form multiplication
identity instead of a finite-difference approximation. Thresholding
`|grad(mask)|` at a fraction of its own maximum then gives the binary outline
— the object's boundary as a byproduct of one Fourier-domain multiplication,
never a pixel-walking contour tracer.

### Why pre-smoothing before differentiating

A hard 0/1 step edge is broadband (same argument as spectral leakage from
Page 1's windowing discussion) — its derivative computed exactly would ring
(Gibbs phenomenon) because a step's Fourier series has slowly-decaying
high-frequency terms. A small Gaussian pre-blur (`gradient_magnitude(...,
smooth=...)`) rolls off those high frequencies first, so the resulting
outline is a clean ridge rather than a fringed one.

## Judges will probably ask

- **"Why band-pass and not just threshold the raw difference?"** — Raw
  difference mixes three unrelated things at very different spatial
  frequencies: pixel-level sensor noise, whole-frame lighting drift, and the
  actual object edges you want. A single threshold can't separate them
  because they overlap in *value*; they don't overlap in *spatial frequency*,
  which is exactly what band-passing exploits. The `raw` detector option
  exists specifically so you can show this failure live.
- **"Isn't the outline just an edge detector — why call it a Fourier
  property?"** — Because it literally *is* the differentiation property,
  computed exactly by one multiplication (`j2πu`, `j2πv`) rather than
  approximated by a small spatial kernel — worth being precise that this is
  the *exact* continuous-domain identity, discretized only by the DFT itself,
  not a Sobel-style finite-difference approximation.
- **"Why run detection on luma even for a colour photo?"** — Change detection
  doesn't need colour information (a moving object typically changes
  intensity, not just hue, and using luma keeps the FFT-based filters 2-D
  instead of needing to define them per-channel or on a 3-D volume); colour
  is only reintroduced when drawing the final overlay, purely for
  presentation.
- **"What's the actual failure mode of `k` being too low/high?"** — Too low:
  residual noise/texture crosses threshold, giving speckled false-positive
  blobs (usually filtered out afterward by `min_area`, but visibly noisier
  masks). Too high: a genuinely present but low-contrast/small object fails
  to cross threshold and is missed entirely — have this trade-off ready with
  a live slider demo.
