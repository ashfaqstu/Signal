# 01 — The Theory, Derived From Scratch

Everything here is material you must **understand**, not just run. By the end you
should be able to derive the whole method on a whiteboard with no notes.

**Contents**

1. [The problem, stated as maths](#1-the-problem-stated-as-maths)
2. [1D warm-up: the shift theorem](#2-1d-warm-up-the-shift-theorem)
3. [From the CFT to the DFT](#3-from-the-cft-to-the-dft-why-we-may-use-the-fft)
4. [The 2D shift theorem](#4-the-2d-shift-theorem)
5. [Magnitude is boring, phase is everything](#5-magnitude-is-boring-phase-is-everything)
6. [The cross-power spectrum](#6-the-cross-power-spectrum)
7. [Inverse transform to a Dirac delta](#7-inverse-transform-to-a-dirac-delta)
8. [From the delta to a pixel](#8-from-the-delta-to-a-pixel-argmax-wraparound-signs)
9. [Why phase correlation beats plain cross-correlation](#9-why-phase-correlation-beats-plain-cross-correlation)
10. [What breaks in the real world](#10-what-breaks-in-the-real-world)
11. [Windowing and spectral leakage](#11-windowing-and-spectral-leakage)
12. [Sub-pixel accuracy](#12-sub-pixel-accuracy)
13. [Confidence metrics](#13-confidence-how-much-do-we-trust-this-peak)
14. [Stretch goal: rotation and scale](#14-stretch-goal-rotation-and-scale-fourier-mellin)
15. [Formula card](#15-formula-card)

---

## 1. The problem, stated as maths

We are given two images, and we *assume* the second is a pure translation of the
first:

    f2(x, y) = f1(x - x0, y - y0)

Find (x0, y0). That is the entire problem.

Notice it is a **parameter estimation** problem with exactly two unknowns over an
input of H x W numbers. Massively over-determined, which is why the answer can be
extremely accurate.

The naive approach is to try every candidate shift and score it (brute-force
cross-correlation): O(N^2) candidate shifts x O(N^2) pixels = O(N^4). For a
1024x1024 image that is about 10^12 operations. The Fourier approach does it in
O(N^2 log N), roughly 2x10^7. **This is the practical reason the frequency domain
exists in engineering.**

---

## 2. 1D warm-up: the shift theorem

Continuous Fourier transform (CFT), the convention we use throughout:

    F(u) = integral over x of  f(x) * exp(-j*2*pi*u*x) dx

Now transform a shifted copy g(x) = f(x - x0):

    G(u) = integral  f(x - x0) * exp(-j*2*pi*u*x) dx

Substitute t = x - x0, so x = t + x0 and dx = dt:

    G(u) = integral  f(t) * exp(-j*2*pi*u*(t + x0)) dt
         = exp(-j*2*pi*u*x0) * integral f(t) * exp(-j*2*pi*u*t) dt

    ==>  G(u) = F(u) * exp(-j*2*pi*u*x0)        <-- THE SHIFT THEOREM

Two consequences, and they are the *whole project*:

- `|G(u)| = |F(u)|` — shifting changes **nothing** about the magnitude spectrum.
- `angle(G(u)) = angle(F(u)) - 2*pi*u*x0` — the shift lives **entirely in the
  phase**, as a term linear in frequency u.

A shift is a *linear phase ramp*, and the slope of that ramp is the shift.
If you remember one sentence from this document, remember that one.

---

## 3. From the CFT to the DFT (why we may use the FFT)

The brief says "2D CFT". The CFT is the *theory*; a computer cannot evaluate an
integral over all of R^2 for a function it only knows at pixel centres. The
bridge has three steps:

1. **Sampling.** A digital image is f(x,y) sampled on a grid. Sampling in space
   causes periodic replication in frequency. As long as the optics band-limited
   the scene below Nyquist, no information is lost.
2. **Truncation.** We only have a finite H x W patch. Truncation is multiplication
   by a rectangular window, which is convolution with a sinc in frequency. This is
   *spectral leakage*, and it is the whole reason for section 11.
3. **Discretisation of frequency.** The DFT evaluates the spectrum at H x W
   discrete frequencies. Equivalently: **the DFT is the exact Fourier series of
   the periodic extension of your image.**

That third point is the one that bites students. The DFT does not see your
photograph. It sees your photograph tiled infinitely in both directions, like
wallpaper. Everything strange that happens later — wraparound shifts, edge
artefacts — traces back to this one fact.

The 2D DFT in numpy's convention (`np.fft.fft2`):

    F[k,l] = sum_m sum_n  f[m,n] * exp(-j*2*pi*(k*m/H + l*n/W))

and the inverse carries the 1/(H*W) factor. The FFT computes this in
O(H*W*log(H*W)) by divide-and-conquer on the factorisation of H*W — which is why
image sizes with small prime factors (powers of 2, or products of 2/3/5) run
noticeably faster than sizes like 1021 x 1019.

---

## 4. The 2D shift theorem

Identical derivation, one substitution per axis:

    f2(x,y) = f1(x - x0, y - y0)
        <==>
    F2(u,v) = F1(u,v) * exp(-j*2*pi*(u*x0 + v*y0))

Discrete version, which is what we actually code:

    f2[m,n] = f1[m - dy, n - dx]   (mod H, W)
        <==>
    F2[k,l] = F1[k,l] * exp(-j*2*pi*(k*dy/H + l*dx/W))

The `(mod H, W)` is not optional in the discrete case — remember the wallpaper.
The DFT can only represent **circular** shifts. A real photographic shift is not
circular (new content enters on one side, old content leaves the other), and
managing that mismatch is what sections 10 and 11 are about.

---

## 5. Magnitude is boring, phase is everything

Run this experiment on day one. It takes ten lines, it is unforgettable, and it
belongs in your presentation.

```python
import numpy as np

A = np.fft.fft2(img_a)      # e.g. a photo of a face
B = np.fft.fft2(img_b)      # e.g. a photo of a building

mix1 = np.abs(A) * np.exp(1j * np.angle(B))   # magnitude of A, phase of B
mix2 = np.abs(B) * np.exp(1j * np.angle(A))   # magnitude of B, phase of A

rec1 = np.real(np.fft.ifft2(mix1))            # you will SEE the building
rec2 = np.real(np.fft.ifft2(mix2))            # you will SEE the face
```

The reconstruction always looks like whichever image donated the **phase**.
Magnitude carries "how much energy sits at each spatial frequency"; phase carries
"where the edges are". **Structure is phase.**

This is the intuitive justification for throwing the magnitude away in section 6.
We are not discarding shift information — the shift was never in the magnitude
(section 2). We are discarding exactly the part that varies with lighting,
exposure and texture contrast: all the nuisance variables.

---

## 6. The cross-power spectrum

Take the two transforms and form

    R(u,v) = ( F2(u,v) * conj(F1(u,v)) ) / | F2(u,v) * conj(F1(u,v)) |

Substitute the shift theorem, F2 = F1 * exp(-j*2*pi*(u*x0 + v*y0)):

    F2 * conj(F1) = F1 * exp(-j*2*pi*(u*x0+v*y0)) * conj(F1)
                  = |F1|^2 * exp(-j*2*pi*(u*x0+v*y0))

The magnitude of that is |F1|^2, a real non-negative number, so dividing it out:

    ==>  R(u,v) = exp(-j*2*pi*(u*x0 + v*y0))

Every trace of the image content is gone. What survives is a **unit-magnitude
complex exponential whose slope in frequency space encodes the shift.** Hence the
name: we are correlating *phase only*.

Practical notes for the code:

- Divide by `np.abs(...) + eps` with `eps = 1e-12`. Where both images have no
  energy at a frequency, the ratio is 0/0.
- A useful generalisation is `R = F2*conj(F1) / |F2*conj(F1)|**beta` with
  `beta` in [0,1]. `beta = 1` is textbook phase correlation (sharpest peak, most
  noise-sensitive); `beta = 0` is ordinary cross-correlation (broadest peak, most
  noise-robust). Expose `beta` as a slider in the UI — it is a beautiful live
  demonstration of the trade-off, and costs you three characters of code.

---

## 7. Inverse transform to a Dirac delta

In the continuous world, the inverse transform of a unit complex exponential is a
shifted delta:

    inverse_FT{ exp(-j*2*pi*(u*x0 + v*y0)) } = delta(x - x0, y - y0)

In the discrete world, work it out explicitly for one axis. With
`R[k] = exp(-j*2*pi*k*d/N)`:

    r[n] = (1/N) * sum_k  exp(-j*2*pi*k*d/N) * exp(+j*2*pi*k*n/N)
         = (1/N) * sum_k  exp( j*2*pi*k*(n-d)/N )

That geometric sum equals N when `n = d (mod N)` and 0 otherwise:

    ==>  r[n] = delta[(n - d) mod N]

So the correlation surface is, ideally, **all zeros except one pixel of value 1,
sitting exactly at the shift.**

For non-integer d the terms no longer cancel perfectly and you get a *Dirichlet
kernel* (a periodic sinc) centred at d. That is not a bug — section 12 reads the
fractional part straight out of the shape of that kernel.

---

## 8. From the delta to a pixel: argmax, wraparound, signs

### 8a. The recipe, in the fixed convention

```python
F1 = np.fft.fft2(ref)
F2 = np.fft.fft2(mov)
Rc = F2 * np.conj(F1)                  # NOTE THE ORDER: moved image first
R  = Rc / (np.abs(Rc) + 1e-12)
corr = np.real(np.fft.ifft2(R))
py, px = np.unravel_index(np.argmax(corr), corr.shape)
```

With `Rc = F2 * conj(F1)` and the model `mov[y,x] = ref[y-dy, x-dx]`, the
derivation of section 7 puts the peak at `(py, px) = (dy mod H, dx mod W)`.

**Positive peak index means the content moved down / right.**

If you write `Rc = F1 * conj(F2)` instead, every sign flips. Neither is wrong,
but pick one and never change it. Ours is: **moved image first.**

### 8b. Unwrapping

`argmax` returns an index in [0, H). A shift of -3 appears at index H-3. Fold the
upper half back to negatives:

```python
dy = py - H if py > H // 2 else py
dx = px - W if px > W // 2 else px
```

Equivalent, and prettier for plotting: `np.fft.fftshift(corr)` puts zero shift at
the array centre, and then `dy = py - H//2`.

**Hard limit:** the estimate is inherently modulo H and W. A shift of +5 and a
shift of +5-H are indistinguishable to the DFT. In practice you can reliably
recover shifts up to roughly 30-40% of the image dimension; beyond that the
overlap between the two images is too small to produce a dominant peak anyway.

### 8c. Applying the correction

To bring `mov` into alignment with `ref`, shift it by the **negative** of the
estimate: `aligned = shift(mov, -dy, -dx)`.

Do that shift in the Fourier domain as well. It is the same theorem run
backwards, it handles fractional pixels exactly, and it keeps the entire project
inside one mathematical framework:

```python
ky = np.fft.fftfreq(H).reshape(-1, 1)    # k/H, in cycles per pixel
kx = np.fft.fftfreq(W).reshape(1, -1)
ramp = np.exp(-2j * np.pi * (ky * dy + kx * dx))
out  = np.real(np.fft.ifft2(np.fft.fft2(img) * ramp))   # content moves by (+dy, +dx)
```

Caveat: this shift is *circular* (content wraps around the edges) and can ring
slightly near sharp edges (Gibbs phenomenon). For display, blank out the wrapped
border strip — see [02-CORE-IMPLEMENTATION.md](02-CORE-IMPLEMENTATION.md).

---

## 9. Why phase correlation beats plain cross-correlation

Ordinary cross-correlation also peaks in the right place. Compute both and put
them side by side in your report — the difference is dramatic and it is one of
the best slides you can make.

| | Plain cross-correlation | Phase correlation |
|---|---|---|
| Surface shape | broad smooth hill, many local maxima | one needle, near-zero elsewhere |
| Localisation | ambiguous on smooth or repetitive texture | pixel-exact |
| Brightness / contrast change | peak shifts and weakens | unaffected: magnitude is divided out |
| Strong periodic interference | dominates the result | suppressed: it is one bin among many |
| Broadband noise | averaged down | amplified, because dividing by a small magnitude boosts junk bins |

The mechanism: dividing by `|F2*conj(F1)|` **whitens** the signal. Every frequency
then contributes with equal weight, so you are correlating against a flat
spectrum — and the autocorrelation of a flat spectrum is an impulse. It is the
same idea as a matched filter or inverse filter in 1D systems theory.

The last row is the honest cost. In heavy noise, or on very low-texture images
(clear sky, blank wall), full whitening amplifies bins that contain only noise.
Mitigations: the `beta` exponent from section 6, or multiplying R by a gentle
low-pass mask before the inverse transform.

---

## 10. What breaks in the real world

| Assumption | Reality | Symptom | Fix |
|---|---|---|---|
| Image is periodic | It is not; edges are a discontinuity | Bright cross along the spectrum axes; spurious peak at (0,0) | Window (section 11) |
| Motion is pure translation | Camera also rotated or zoomed | Peak smears into a blob, confidence collapses | Fourier-Mellin (section 14), or state the limitation |
| | *measured:* 0.5 deg still exact; 2 deg degraded (ratio 3.1); 5 deg wrong (ratio 1.05) | | |
| Same content in both frames | New content enters at the edge; objects move independently | Peak weakens; competing peaks appear | More overlap; window; reject on low confidence |
| Same illumination | Exposure / white balance changed | **No problem** — this is the method's superpower | none needed |
| Shift below half the image | Huge displacement | Wrong answer, modulo N | Downsample-and-refine pyramid |
| Scene is flat, or camera only translated in 2D | 3D parallax between near and far objects | No single global shift exists | Block-wise correlation, see [04](04-BONUS-2-VIDEO-STABILIZER.md) |

---

## 11. Windowing and spectral leakage

The DFT assumes your image tiles seamlessly. The right edge does not continue
into the left edge, so the periodic extension contains a hard step there — and a
step is broadband. That energy lands along the `u = 0` and `v = 0` axes of the
spectrum and can easily outweigh the real image content, producing a false peak
(classically at or near the origin).

Fix: multiply both images by a separable window that decays to zero at the
border, so the periodic extension becomes continuous.

```python
w = np.outer(np.hanning(H), np.hanning(W))   # 2D Hann / raised-cosine window
a = (ref - ref.mean()) * w
b = (mov - mov.mean()) * w
```

Subtract the mean first as well: the DC bin is usually orders of magnitude larger
than everything else and contributes nothing at all to the shift estimate.

### The gotcha that will confuse you for an hour

The window is **fixed in the frame**; it does not move with the image content.
So for a test pair produced by `np.roll` — a genuinely circular shift, where the
un-windowed answer is mathematically exact — windowing *introduces* error.

Therefore, and both of these are true at the same time:

- **Circular test pairs (`np.roll`): test with `window=False` and expect an
  exact integer answer.** This is your correctness unit test.
- **Real translations (two crops of a larger scene, real photos): use
  `window=True`.** Here the window removes far more error than it adds.

Understanding why both statements hold is a genuinely strong viva answer.

**Honesty note.** In our own sweeps on synthetic scenes — strong luminance
gradients, only 39% overlap, repetitive brick-like texture — windowed and
unwindowed runs were *equally exact*. Phase correlation is more robust than the
textbook warnings suggest. Windowing is insurance that pays off when the periodic
extension has a violent discontinuity (bright sky meeting dark ground at the
frame edge, a vignette, a scanned border, a very small image). Keep it as a
flag, A/B it on your own photographs, and report what you actually measured.

---

## 12. Sub-pixel accuracy

The true shift is rarely an integer. When d is fractional, the sum in section 7
does not collapse to a single spike; it becomes a Dirichlet kernel centred on the
true d and sampled at integer positions. The samples *around* the peak therefore
carry the fractional part. Three ways to read it out:

### Method A — parabolic (quadratic) fit. Use this one.

Fit `p(t) = a*t^2 + b*t + c` through the three samples `y(-1), y(0), y(+1)`
around the peak along one axis. From `b = (y(+1) - y(-1))/2` and
`a = (y(+1) + y(-1))/2 - y(0)`, the vertex `t* = -b/(2a)` gives

    delta = ( y(-1) - y(+1) ) / ( 2 * ( y(-1) + y(+1) - 2*y(0) ) )

Do it independently for the row axis and the column axis, add each delta to the
integer peak, and clamp to [-0.5, +0.5] (anything larger means the fit failed and
you should keep the integer answer). Measured accuracy over 50 random fractional
shifts: **mean error 0.08 px, worst case 0.12 px** — for about ten lines of code.
Sanity check the sign: if `y(-1) > y(+1)` the true peak leans toward -1, and the
formula does return a negative delta.

### Method B — centroid of a small neighbourhood

Amplitude-weighted centre of mass over a 5x5 patch around the peak. More robust
on noisy, flat-topped peaks; slightly biased toward the patch centre.

### Method C — upsampled DFT (Guizar-Sicairos et al.)

Find the coarse peak, then evaluate the inverse DFT only on a tiny 1.5 x 1.5 px
neighbourhood, sampled 100x finer, using a direct matrix-multiply DFT. Accuracy
around 1/100 px at negligible cost, because you never materialise a large
upsampled array. Implement only if you want an extra-credit section; Method A is
more than enough for the core project.

### How to test sub-pixel code honestly

You cannot produce a fractional shift with `np.roll`. Generate ground truth with
the Fourier phase ramp of section 8c:

```python
mov = fourier_shift(ref, 3.7, -2.3)
dy, dx = phase_correlation(ref, mov)        # expect ~3.7 and ~-2.3
assert abs(dy - 3.7) < 0.05 and abs(dx + 2.3) < 0.05
```

---

## 13. Confidence: how much do we trust this peak?

Never return a shift without a quality number. Three cheap ones:

- **Peak height.** With `beta = 1` normalisation, a perfect match approaches 1.
- **Peak-to-sidelobe ratio (PSR).** Mask an 11x11 box around the peak, compute
  the mean `mu` and standard deviation `sigma` of everything outside it, then
  `PSR = (peak - mu) / sigma`. Roll the peak to the array centre first so the
  mask cannot wrap.
- **Peak ratio.** Highest peak divided by the second-highest peak outside the
  exclusion box. This turns out to be the best single discriminator.

Values we measured on 256x256 crops (yours will differ with content — build the
same table for your own images):

| Case | peak | PSR | peak ratio |
|---|---|---|---|
| Clean overlapping crops | 0.87 | 460 | 92 |
| Same pair + noise (sigma 0.15) | 0.09 | 24 | 4.2 |
| Featureless target (flat grey) | 0.024 | 6.2 | 1.08 |
| Two unrelated images | 0.020 | 5.1 | 1.04 |

Note how little separation `peak` and `PSR` give between "featureless" and
"unrelated", and how cleanly `peak ratio` splits a real lock (>= 2) from no lock
(<= 1.2). Use the ratio for the accept/reject decision.

These are not decoration. Bonus 2 uses them to detect scene cuts, and the UI uses
them to drive a green / amber / red lock indicator.

---

## 14. Stretch goal: rotation and scale (Fourier-Mellin)

Attempt only after everything else is finished and tested.

From section 2, the **magnitude** spectrum is shift-invariant. It is not
rotation- or scale-invariant, though: it rotates with the image, and scales
inversely.

    f(x,y) rotated by theta and scaled by s
        ==>  |F| rotated by theta and scaled by 1/s

So: take `|F1|` and `|F2|` and resample both onto a **log-polar grid**
`(log rho, theta)`. In those coordinates, a rotation becomes a pure shift along
the theta axis and a scale becomes a pure shift along the log-rho axis. Run *the
same phase correlation function you already wrote* on the two log-polar images to
read off (theta, s). Undo the rotation and scale, then run phase correlation a
third time for the translation.

It reuses your core function three times, which is exactly the kind of structure
that impresses an examiner. It also needs bilinear resampling and careful
handling of the spectrum's conjugate symmetry. Budget a full day.

---

## 15. Formula card

Print this. Tape it to the monitor.

| Concept | Formula |
|---|---|
| CFT | `F(u,v) = int int f(x,y) exp(-j2pi(ux+vy)) dx dy` |
| Shift theorem | `f(x-x0, y-y0)  <->  F(u,v) exp(-j2pi(u*x0 + v*y0))` |
| Magnitude invariance | `|F2| = |F1|` |
| Cross-power spectrum | `R = F2 conj(F1) / |F2 conj(F1)|` |
| Ideal R | `R = exp(-j2pi(u*x0 + v*y0))` |
| Correlation surface | `r = IFFT(R) = delta(x-x0, y-y0)` |
| Estimate | `(dy, dx) = argmax(r)`, unwrapped mod (H, W) |
| Sub-pixel | `delta = (y(-1) - y(+1)) / (2*(y(-1) + y(+1) - 2*y(0)))` |
| Fourier shift | `g = IFFT( F * exp(-j2pi(k*dy/H + l*dx/W)) )` |
| PSR | `(peak - mu_sidelobe) / sigma_sidelobe` |
| Cost | `O(HW log HW)` versus `O(H^2 W^2)` brute force |

Next: **[02-CORE-IMPLEMENTATION.md](02-CORE-IMPLEMENTATION.md)** — build it.
