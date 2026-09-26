# 8. Viva cheat sheet — fast recall

Read this in the last few minutes before presenting. Everything here is
expanded, with derivations, in files 01–07.

## The one-sentence pitch

"Every feature here is one trick, applied three ways, plus one engine,
applied three ways. The trick: a geometric transform of an image becomes,
in the frequency domain, something you can find by locating one peak —
directly for translation, and via a log-polar coordinate change for rotation
and scale. The engine: register a sequence of frames onto each other, then
collapse each pixel's values across frames with a chosen statistic — mean
for denoising, a robust statistic for removing what moved."

## Formula card

| concept | formula |
|---|---|
| Continuous Fourier transform | `F(u,v) = ∫∫ f(x,y) e^{-j2π(ux+vy)} dx dy` |
| Shift theorem | `f(x-x0,y-y0) <=> F(u,v)·e^{-j2π(u·x0+v·y0)}` |
| Magnitude invariance under shift | `\|F2\| = \|F1\|` |
| Cross-power spectrum | `R = F2·conj(F1) / \|F2·conj(F1)\|^beta` |
| Ideal R (beta=1) | `R = e^{-j2π(u·dy+v·dx)}` |
| Correlation surface | `r = IFFT(R)` → delta at `(dy, dx) mod (H, W)` |
| Sub-pixel (parabolic) | `delta = (y(-1)-y(+1)) / (2·(y(-1)+y(+1)-2·y(0)))` |
| Rendering a shift (forward) | `g = IFFT( FFT(f) · e^{-j2π(k_y·dy + k_x·dx)} )` |
| Rotation/scale of `\|F\|` | image rotated θ, scaled s ⇒ `\|F\|` rotated θ, scaled `1/s` |
| Log-polar rotation → shift | `θ → θ + Δθ` (additive, direct sign) |
| Log-polar scale → shift | `ln ρ → ln ρ − ln s` (additive, inverted sign) |
| Angle read-out | `angle = d_theta · (180/n_theta)` |
| Scale read-out | `scale = exp(-d_rho · log_step)` |
| Peak-to-sidelobe ratio | `PSR = (peak − mean_sidelobe) / std_sidelobe` |
| Peak ratio (the trust metric) | `peak / second_peak` — accept if ≳ 2–4 |
| PSNR | `20·log10(peak_value / RMSE)` |
| NCC | `Σ(a-ā)(b-b̄) / (‖a-ā‖·‖b-b̄‖)` |
| Mean-stack theoretical gain | `+10·log10(N)` dB |
| Median-stack theoretical gain | `+10·log10(N) − 10·log10(π/2)` dB (≈1.96 dB worse) |
| Fourier differentiation property | `d/dx f <=> j2πu·F(u,v)` — used for the outline |
| Brute-force translation search cost | `O(N⁴)` |
| Phase-correlation cost | `O(N² log N)` |

## Per-page, in one paragraph each

**1. Translation.** Two FFTs, one normalized elementwise complex division
(cross-power spectrum), one inverse FFT, one `argmax`. Works because a shift
in space is *only* a linear phase ramp in frequency — magnitude carries no
shift information at all, so dividing it out leaves nothing but the ramp,
whose inverse transform is an impulse exactly at the shift. `beta` slides
continuously between this (`1.0`, sharp/noise-sensitive) and plain
cross-correlation (`0.0`, broad/noise-robust). A parabolic fit around the
integer peak recovers sub-pixel accuracy (~0.08 px mean error). Confidence is
judged by *peak ratio*, not peak height, because only the ratio separates "no
real match" from "featureless but real."

**2. Rotation & scale.** Same phase-correlation primitive, reused three
times. Take `|FFT|` first (translation-invariant by the shift theorem, for
free), resample onto a log-polar grid where rotation and scale each become a
plain axis shift, correlate that, then undo the recovered rotation/scale and
run phase correlation once more for translation. The angle is only known
modulo 180° (a real image's magnitude spectrum is centrosymmetric); both
candidates are tried and scored by final alignment quality, not by an
intermediate confidence number. Three presets trade spectrum coverage for
noise robustness, chosen the same outcome-scored way.

**3. Stacking.** `align (Page 1/2's engine) → reduce (pixelwise statistic
across the frame axis)`. Mean is the statistically optimal (minimum-variance)
estimator for i.i.d. Gaussian sensor noise, giving `+10·log10(N)` dB;
median/shorth/sigma-clip trade some of that gain for robustness to outliers.

**4. Object removal.** The *identical* align+reduce engine as Page 3, default
reducer switched to `shorth` (robust to a minority-outlier moving object) and
alignment able to auto-upgrade to Fourier-Mellin for hand-held shots. No
linear (LTI) filter — including a temporal blur — can ever fully reject an
outlier; only a nonlinear, order-statistic-based reducer can give it exactly
zero weight. `shorth` improves on plain median by fixing median's even-N
"average the two middle values" blending gap.

**5. Highlight.** Runs Page 4 to get a background plate, then everything
after that is one filter after another, entirely as multiplications in the
frequency domain: band-pass the per-photo difference (rejects noise above and
lighting drift below, keeps object-sized structure), adaptive-threshold it
(`mean + k·σ`), clean the resulting mask by blurring-and-re-thresholding
(morphological open/close as filtering), then outline it with
`|gradient|` computed exactly via the differentiation property
(`j2πu`/`j2πv`) — never a contour-tracing algorithm.

## Sharpest likely questions, with the one-line answer ready

- **Why the frequency domain at all?** O(N² log N) vs. O(N⁴) brute force; the
  factor-of-~10⁵ speedup on a 1024² image is the whole engineering case.
- **Why divide out the magnitude — doesn't that lose information?** No: the
  shift theorem proves the shift was never *in* the magnitude to begin with;
  only phase carries it.
- **Why does a "shift" theorem also solve rotation and scale?** Because
  taking `|FFT|` first and remapping to log-polar coordinates turns *those*
  transforms into shifts too — same peak-finding primitive, different
  coordinate system.
- **Why is the rotation angle ambiguous by 180°?** The magnitude spectrum of
  any real image is centrosymmetric (Hermitian symmetry minus phase); resolved
  by trying both candidates and keeping the one with the stronger post-align
  translation peak.
- **How do you know a registration is trustworthy?** Peak ratio (top peak ÷
  runner-up outside an exclusion box) — the only one of peak/PSR/ratio that
  cleanly separates a real lock from noise.
- **Why not just average the frames to remove a moving object?** Averaging is
  linear — it can only *attenuate* an outlier proportional to its weight,
  never zero it out; only an order-statistic (median/shorth) can give it
  exactly zero weight.
- **Why `shorth` over plain `median`?** With an even frame count, `median` is
  the *mean of the two middle* order statistics — if the object occupies
  close to half the frames at a pixel, that averaging blends object and
  background and leaves a ghost. `shorth` picks the tightest majority-run
  instead of always trusting the middle two, so the odd sample gets outvoted.
- **Why band-pass instead of just thresholding the difference?** Sensor noise
  (high frequency), lighting drift (low frequency) and real object edges
  (mid frequency) overlap in *value* but not in *spatial frequency* — a
  band-pass separates them in one multiplication; the `raw` detector option
  exists to show this failing live.
- **Why is the outline "the differentiation property" and not an edge
  detector?** Because it's computed by the *exact* closed-form identity
  `d/dx f ⟺ j2πu·F`, applied as one multiplication in frequency, not a
  finite-difference kernel or a contour walker.
- **Why does windowing sometimes hurt in your own tests?** The DFT assumes
  the image tiles periodically; a window fixes the resulting edge-discontinuity
  artefact for *real* photographs, but for a synthetic `np.roll` test pair
  (genuinely, exactly circular) the un-windowed answer is already exact and
  windowing only adds error — both facts are true, they're about different
  experiments.
- **How is the code organized to make all this testable/extensible?**
  `spectrasync/` has zero UI dependency (numpy + matplotlib only); every
  swappable algorithm (window, sub-pixel method, reducer, detector, filter)
  is one `Registry` entry, so the UI dropdowns and the algorithm options can
  never drift apart; correctness is proven once against synthetic ground
  truth in `spectrasync`-level tests, independent of either UI.
- **What are the known limitations?** Translation: shift capped near
  30–40% of image dimension (DFT-modulo ambiguity). Rotation/scale: usable
  range ~0.7×–2.0×, needs a similarity (not perspective) motion model — real
  hand-held photos have a little perspective the model can't express, so
  alignment is close but never pixel-perfect. Stacking/removal: needs enough
  frames, and a genuinely persistent background pixel to recover (if an
  object never leaves a pixel across the whole sequence, there's no
  background sample there to find).
