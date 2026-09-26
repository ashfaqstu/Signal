# 1. Translation — `phase_correlation` (`func_translation`)

Code: [`spectrasync/core/correlation.py`](../../spectrasync/core/correlation.py),
[`spectrasync/core/windows.py`](../../spectrasync/core/windows.py),
[`spectrasync/core/subpixel.py`](../../spectrasync/core/subpixel.py) ·
UI: [`app/pages/p1_translation.py`](../../app/pages/p1_translation.py)

## L1 — High-level algorithm

**Question:** given a reference image and a second image that is the reference
shifted by some unknown (dy, dx), find that shift.

**Algorithm family:** this is **phase correlation**, a frequency-domain method
built on the **Fourier shift theorem**. It is neither a spatial-domain
convolution/correlation nor a search: it is one forward FFT of each image, one
elementwise complex division (normalisation), one inverse FFT, and an
`argmax`.

Why the frequency domain at all: brute-force template matching (try every
candidate shift, score the overlap) costs O(N⁴) for an N×N image — for
1024×1024 that's ~10¹² operations. Doing it as one pair of FFTs costs
**O(N² log N)** — about 10⁷. That complexity gap is the entire engineering
justification for the method, independent of any accuracy argument.

**The core fact making it work:** shifting an image only changes the *phase*
of its Fourier transform, never the *magnitude*. So:

1. Take both images to the frequency domain (`np.fft.fft2`).
2. Form the **cross-power spectrum**: multiply one transform by the complex
   conjugate of the other, then divide by its own magnitude. This is a
   *normalisation*, not a filter — it deliberately throws away all magnitude
   (content/contrast) information and keeps only the phase difference.
3. What's left is, ideally, a pure complex exponential whose phase is a
   plane linear in frequency. The **slope of that plane is the shift**.
4. Inverse-FFT it. A pure complex exponential's inverse transform is a Dirac
   delta — in the discrete image, one bright pixel — sitting exactly at
   (dy, dx) (mod H, W, because the DFT only knows circular shifts).
5. `argmax` finds that pixel; a small local fit around it recovers the
   sub-pixel fraction.

This is not a convolution (no kernel, no correlation with a shifted copy in
the spatial-domain sense) — it *replaces* the O(N⁴) spatial cross-correlation
that convolution theorem would otherwise still leave you doing pixel-by-pixel;
the whole point of phase correlation is that dividing out the magnitude turns
the correlation surface into an impulse, so you never search, you just read
off one coordinate.

## L2 — The pipeline and every UI option

### Pipeline, in code order (`phase_correlation`)

```
a, b            = ref - mean(ref), mov - mean(mov)     # kill the DC bin
a, b            = a * w, b * w                          # optional window
F1, F2          = fft2(a), fft2(b)
Rc              = F2 * conj(F1)                          # moved image FIRST — sign convention
R               = Rc / (|Rc|^beta + eps)                 # magnitude normalisation
corr            = real(ifft2(R))                          # the correlation surface
(py, px)        = argmax(|corr|)                          # integer peak (uses |corr| so a
                                                            #   contrast-inverted pair still locates)
(sy, sx)        = subpixel_refiner(corr, py, px)           # fractional correction
(dy, dx)        = unwrap(py+sy, px+sx)  mod (H, W)         # fold upper half to negative
```

Sign convention (fixed project-wide, tested): `mov[y,x] = ref[y-dy, x-dx]`,
`Rc = F2·conj(F1)` — the **moved** image goes first. `+dy` means content moved
down, `+dx` means content moved right. Flip the conjugate order and every sign
flips; the project picked one and never deviates.

To *apply* a correction the negative of the estimate is used
(`apply_registration`), via the same shift theorem run forward
(`fourier_shift`) — so estimating and rendering a shift are the same
mathematical operation used in two directions.

### UI option: **Window** (`hann`, `hamming`, `blackman`, `bartlett`, `tukey`, `none`)

*What it's for:* the DFT treats the image as one period of an infinitely
tiled signal. The real right edge does not continue smoothly into the real
left edge, so that seam is a hard step — and a step is broadband energy that
leaks along the `u=0`/`v=0` axes of the spectrum, sometimes strong enough to
fake a peak at the origin. A window that tapers to (near) zero at the border
makes the tiled/periodic version of the image continuous, removing that
artificial edge.

*Mathematical significance:* windowing multiplies the image by `w(y)·w(x)`
in the spatial domain, which by the convolution theorem **convolves** the true
spectrum with the window's own spectrum (a narrow sinc-like kernel). This
slightly *broadens* the correlation peak — trading a little sharpness for
robustness to edge leakage.

*Comparing the options:*
| window | shape | edge value | trade-off |
|---|---|---|---|
| `none` | rectangular | 1.0 | no leakage suppression; exact on a circularly-shifted (`np.roll`) test pair — the only case where the periodic assumption is literally true |
| `hann` (default) | raised cosine | 0.0 | the standard general-purpose choice; smooth first derivative at the edge → good sidelobe suppression |
| `hamming` | raised cosine, offset | ≈0.08 | doesn't fully reach zero, trades a touch of edge leakage for a narrower main lobe than Hann |
| `blackman` | wider cosine sum | 0.0 | much lower sidelobes, wider main lobe (blurrier peak) — best on very "busy"/high-contrast borders |
| `bartlett` | triangular | 0.0 | cheapest window, least sophisticated taper |
| `tukey` (α=0.5) | flat centre + cosine skirts | 0.0 at edge, 1.0 in the middle | only tapers the outer half; keeps more of the image untouched than Hann |

*The gotcha (a genuinely strong answer if asked):* the window is **fixed to
the frame**, it does not travel with image content. So for a synthetic test
pair made by `np.roll` (a truly circular shift, where the un-windowed answer
is mathematically exact), windowing *introduces* error rather than removing
it — you must test with `window="none"` there and expect an exact integer
result. For real photographs (two crops of a bigger scene) the periodic
assumption is false regardless, and there windowing usually helps. Both
statements are true simultaneously and are not a contradiction — they are
answers to two different experiments.

### UI option: **Sub-pixel refiner** (`none`, `parabolic`, `centroid`, `gaussian`)

*Why one is needed at all:* a real shift is essentially never an exact
integer number of pixels. When it isn't, the "ideal delta" of the theory
becomes a **Dirichlet kernel** (a discrete, periodic sinc) centred at the true
non-integer position — so the energy spreads across several pixels around the
integer peak, and that spread pixel-by-pixel encodes the fractional part.

*Options:*
- **`none`** — take the integer argmax and stop. Ground truth for testing;
  error can be up to ±0.5 px.
- **`parabolic`** (default) — fit a quadratic through the 3 samples straddling
  the peak on each axis independently and take the fitted vertex. Cheap (10
  lines), and empirically the best general-purpose choice here: **mean error
  0.08 px, worst case 0.12 px** over 50 random fractional shifts.
- **`centroid`** — amplitude-weighted centre of mass over a 5×5 neighbourhood
  (clipped to non-negative values first). More robust to a noisy, flat-topped
  peak; slightly biased toward the patch centre because it uses more than 3
  points and the tails are noisier.
- **`gaussian`** — log-parabolic fit (fits a Gaussian instead of a parabola by
  working in log-space). *Correct in theory* for a genuinely Gaussian-shaped
  peak, but a phase-correlation peak sits on a near-zero floor with **negative**
  sidelobes (measured: peak 0.739, neighbours 0.315 and −0.172) — a negative
  sample makes `log()` undefined, so this refiner silently falls back to the
  integer answer here (measured median error 0.412 px, no better than `none`).
  It is the right tool for a surface that actually is positive everywhere by
  construction — plain cross-correlation (`beta=0`) or the log-polar magnitude
  correlation used on Page 2 — but not for phase correlation itself. This is a
  deliberately-kept "trap" option in the UI to demonstrate exactly this point.

### UI option: **beta (magnitude normalisation exponent)**

`R = F2·conj(F1) / |F2·conj(F1)|^beta`. This one slider *is* the whole
spectrum between two classical methods:

- **beta = 1.0** — textbook phase correlation. Every frequency bin is
  normalised to unit magnitude ("whitened"), so every frequency contributes
  equally to the inverse transform regardless of how much real image energy
  was there. The autocorrelation of a flat (white) spectrum is a perfect
  impulse, hence the needle-sharp peak. Downside: bins that are almost pure
  noise (very little real signal) get amplified exactly as much as bins that
  are pure signal — a small amount of noise is boosted as much as the
  original signal that was buried there.
- **beta = 0.0** — no normalisation at all: `R = F2·conj(F1)`, which after
  the inverse transform is exactly **plain (ordinary) cross-correlation**. Its
  surface is a broad, smooth hill, shaped by however much energy the image
  actually had at each frequency, and it is far more robust to noise because
  low-SNR bins are naturally down-weighted by their small magnitude instead of
  being boosted to unit strength.
- **Intermediate values** interpolate the trade-off continuously; measured
  optimum on a noisy synthetic pair here is around **beta ≈ 0.8**, not 1.0.

| | beta = 0 (plain cross-corr) | beta = 1 (phase correlation) |
|---|---|---|
| Peak shape | broad hill, several local maxima | one sharp needle |
| Localisation on smooth/repetitive texture | ambiguous | pixel-exact |
| Robust to brightness/contrast change | peak shifts and weakens | unaffected — magnitude is normalised away entirely |
| Strong periodic interference | dominates the surface | one bin among many, suppressed |
| Broadband sensor noise | naturally averaged down | amplified (dividing a small magnitude boosts noise-only bins) |

### UI option: **low-pass the cross-power spectrum**

An optional Gaussian low-pass mask (see `core.filters.lowpass`) multiplied
onto `R` before the inverse FFT. Slide it up and the correlation needle
visibly **broadens** into a blob. This is a deliberate, live demonstration
that **pixel-level localisation lives in the high-frequency content** of the
cross-power spectrum — a low-pass throws that fine structure away and only
the coarse trend of the phase ramp survives, so the peak can no longer be
pinned to one pixel.

### UI option: **Overlay** (`anaglyph`, `checkerboard`, `blend`, `difference`, `split`)

Purely a display choice, not part of the estimation math — but each answers a
different visual question, worth knowing:

| overlay | formula | reads as |
|---|---|---|
| `anaglyph` | `dstack(ref, mov, mov)` — ref→red, mov→cyan | grey = aligned; red/cyan fringe = misalignment direction |
| `checkerboard` | alternating `tile×tile` blocks from ref/mov | straight lines across tile boundaries = aligned; broken/offset lines = misaligned |
| `blend` | `(1-α)·ref + α·mov` | ghosting proportional to residual shift |
| `difference` | `\|ref − mov\|` | collapses toward black when aligned |
| `split` | left `frac` from ref, right from mov | a hard visual seam if misaligned |

## L3 — The mathematics

### Continuous shift theorem (1D warm-up)

Fourier transform convention used throughout:
`F(u) = ∫ f(x)·e^(−j2πux) dx`.

For `g(x) = f(x − x₀)`, substitute `t = x − x₀`:

```
G(u) = ∫ f(x - x0) e^{-j2πux} dx = e^{-j2πux0} ∫ f(t) e^{-j2πut} dt
G(u) = F(u) · e^{-j2π u x0}
```

Two consequences — the whole method:
- `|G(u)| = |F(u)|` (magnitude is shift-invariant).
- `angle(G(u)) = angle(F(u)) − 2πu·x₀` (the shift is a phase term **linear**
  in frequency `u`; its slope *is* the shift).

### 2D discrete version (what's actually coded)

```
f2[m,n] = f1[m - dy, n - dx]  (mod H, W)
   <==>
F2[k,l] = F1[k,l] · exp(-j2π(k·dy/H + l·dx/W))
```

The `mod` is mandatory in the discrete case: a digital image's DFT is exactly
the Fourier series of the image's **periodic extension** (tiled infinitely in
both directions, like wallpaper) — the DFT can only represent *circular*
shifts. A real photographic shift is not circular (new content enters one
edge, old content exits the other); windowing (§11) and border-masking exist
specifically to manage that mismatch.

### Cross-power spectrum

```
R(u,v) = F2·conj(F1) / |F2·conj(F1)|
       = F1·e^{-j2π(u dy + v dx)}·conj(F1) / |F1|²·1        (substitute the shift theorem)
       = |F1|² e^{-j2π(u dy+v dx)} / |F1|²
       = e^{-j2π(u dy + v dx)}
```

Every trace of image *content* has cancelled; what remains is a
unit-magnitude complex exponential — the same plane found in the theorem
above, now content-free. (Implementation detail: `eps = 1e-12` is added to
the denominator to avoid 0/0 where both spectra are exactly zero at some
frequency; and `|Rc|^beta` instead of `|Rc|` generalises this to the beta
slider described above.)

### From the ideal ramp to a discrete delta

For one axis, `R[k] = e^{-j2πkd/N}`, the inverse DFT is

```
r[n] = (1/N) Σ_k e^{-j2πkd/N} e^{j2πkn/N} = (1/N) Σ_k e^{j2πk(n-d)/N}
```

That geometric sum is `N` when `n = d (mod N)` and `0` otherwise — an exact
Kronecker delta at the shift. For **non-integer** `d` the terms no longer
cancel to exactly zero elsewhere; you get a **Dirichlet kernel** (discrete,
periodic sinc) centred at `d`, sampled only at the integers. The parabolic /
centroid / gaussian refiners exist precisely to read the fractional part back
out of the shape of that kernel.

### Sub-pixel formula (parabolic, the default)

Fit `p(t) = a t² + b t + c` through 3 samples `y(−1), y(0), y(+1)` straddling
the integer peak along one axis. With
`b = (y(+1) − y(−1))/2` and `a = (y(+1) + y(−1))/2 − y(0)`, the vertex
`t* = −b/(2a)` gives, per axis, independently:

```
delta = ( y(-1) - y(+1) ) / ( 2 · ( y(-1) + y(+1) - 2·y(0) ) )
```

clamped to `[−0.5, +0.5]` (a larger fitted value means the fit failed; the
integer answer is kept instead).

### Applying the correction

Rendering a shift uses the *same* theorem run forward:

```
out = real( ifft2( fft2(img) · exp(-j2π(ky·dy + kx·dx)) ) )     # ky, kx = fftfreq grids
```

This shift is inherently **circular** — content wraps at the border — so any
display/metric after applying it should be restricted with
`alignment_valid_mask` (see
[06-confidence-and-metrics.md](06-confidence-and-metrics.md)) to the region
that is not wrapped-around filler.

### Range limit

The estimate is only known modulo (H, W): a true shift of `+5` and `+5−H` are
indistinguishable to the DFT. In practice, shifts up to roughly 30–40% of the
image dimension are reliably recoverable; a `phase_correlation_pyramid`
coarse-to-fine variant exists in the codebase for larger shifts (halve the
image, estimate coarsely, refine at full resolution).

## Judges will probably ask

- **"Why not just cross-correlate in the spatial domain?"** — O(N⁴) vs. this
  method's O(N² log N); for a 1024² image that's ~10¹² vs ~10⁷ operations.
- **"Why does the magnitude get thrown away — doesn't that lose information?"**
  — No: the shift was never encoded in the magnitude to begin with (shift
  theorem, §L3); the magnitude only encodes brightness/contrast/texture
  energy, which is exactly the nuisance information you want to be invariant
  to.
- **"What if the two images have inverted contrast (e.g. a negative)?"** — The
  correlation peak becomes **negative** instead of positive. The code searches
  `argmax(|corr|)`, so the location is still found correctly; `stats.polarity`
  reports the sign so the UI can flag it explicitly.
- **"What breaks this method?"** — Anything that isn't a pure translation:
  camera rotation/zoom (peak smears, confidence collapses — that's what Page 2
  is for), too little frame overlap, or a shift beyond ~40% of the image.
- **"How do you know when to trust the answer?"** — `peak ratio` (top peak ÷
  second-highest sidelobe peak); see
  [06-confidence-and-metrics.md](06-confidence-and-metrics.md).
