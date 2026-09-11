# 06 — Troubleshooting, and the Questions You Will Be Asked

For the *live* evaluation task — the small thing the examiner asks you to build
or modify on the spot — see **[07-EVALUATION-PREP.md](07-EVALUATION-PREP.md)**.
This document covers debugging and the spoken viva.

---

## Part A — Symptom, cause, fix

### The peak is always at (0, 0)

| Likely cause | Check | Fix |
|---|---|---|
| The two images really are identical | `np.array_equal(ref, mov)` | use a genuinely shifted pair |
| DC dominates | `corr.max()` is huge, surface has a spike only at the origin | subtract the mean before the FFT |
| Edge discontinuity (spectral leakage) | the surface has a bright cross along the axes | apply the Hann window |
| One image is constant / blank | `mov.std()` near 0 | check your loader; you probably read an alpha channel |
| Shift is genuinely sub-pixel | peak at 0 but `corr` neighbours are asymmetric | enable the parabolic fit |

### The sign is flipped

You are almost certainly computing `F1 * conj(F2)` instead of `F2 * conj(F1)`,
or you swapped the arguments. **Do not fix this by negating the output.** Run
the circular test:

```python
mov = np.roll(base, (7, -11), axis=(0, 1))
print(phase_correlation(base, mov, window=False, subpixel=False)[:2])   # must print (7.0, -11.0)
```

Fix the convention at the source, then re-run the whole test suite.

### The estimate is off by exactly H or W

You forgot the unwrapping step. Indices above `H//2` represent negative shifts.
See [01 section 8b](01-THEORY.md#8-from-the-delta-to-a-pixel-argmax-wraparound-signs).

### Works perfectly on synthetic pairs, garbage on real photos

In order of likelihood:

1. **The camera rotated.** Measured: 0.5 deg is fine, 2 deg degrades, 5 deg is
   hopeless. Reshoot by sliding the camera, not turning it.
2. **The shift is too large.** Beyond ~40% of the frame there is too little
   overlap. Downsample and search coarse-to-fine.
3. **The scene changed** — people moved, leaves blew, the sun went behind a
   cloud. Check the peak ratio; if it is near 1, the estimator is telling you it
   found nothing.
4. **You did not window.** Try `window=True`.
5. **Different resolutions.** Phase correlation requires identical array shapes,
   and it cannot see scale changes. Crop both to a common size.

### The answer changes every run

You are seeding a random generator inside a loop, or reading a JPEG twice with
different decoders. The algorithm itself is fully deterministic.

### Sub-pixel refinement makes the result worse

- The peak sits at index 0 or `H-1` and your neighbour lookup wrapped
  incorrectly. Use modulo indexing, as in the reference `_parabolic`.
- The peak is flat-topped (denominator near zero). The guard clause should
  return 0 in that case.
- You applied the fit *after* unwrapping instead of before. Fit first, unwrap
  second.

### The aligned image has a smeared or wrapped border

Expected — `fourier_shift` is circular. Use `valid_mask` and blank the border, or
crop, before displaying or computing metrics.

### Colour images crash or return nonsense

Estimate on grayscale, `shape == (H, W)`. Apply the shift per channel. `load_gray`
versus `load_rgb` exists precisely to keep these apart.

### Everything is black, or washed out, when displayed

`uint8` versus `float` confusion. matplotlib expects float images in [0, 1] and
integer images in [0, 255]. Keep everything float in [0, 1] internally and
convert once at save time.

### It is unbearably slow

Measured baseline: 9.3 ms at 256x256, 39.4 ms at 512x512, 273 ms at 1024x1024.
If you are far above that, you are almost certainly re-computing an FFT inside a
loop, or your dimensions are large primes. Pad to a size with small prime factors,
cache transforms, and estimate on downsampled frames.

---

## Part B — Viva questions, with answers

Rehearse these out loud. The short answer is what you say; the follow-up is what
you say when they push.

**Q1. Why the Fourier domain at all? Cross-correlation in the spatial domain
would also work.**
It would, at `O(N^4)` for an `N x N` image — about `10^12` operations at
1024x1024. The FFT route is `O(N^2 log N)`, about `2x10^7`, which we measured at
273 ms. The frequency domain also makes the shift *explicit*: it becomes a linear
phase ramp rather than an implicit maximum you have to search for.

**Q2. Derive the cross-power spectrum.**
Board work. `f2(x,y) = f1(x-x0, y-y0)`, so by the shift theorem
`F2 = F1 * exp(-j2pi(u*x0+v*y0))`. Then
`F2 * conj(F1) = |F1|^2 * exp(-j2pi(u*x0+v*y0))`, and dividing by the magnitude
leaves `exp(-j2pi(u*x0+v*y0))`, whose inverse transform is `delta(x-x0, y-y0)`.

**Q3. Why divide by the magnitude? What is lost?**
Nothing that matters. By the shift theorem the magnitude spectrum is unchanged by
translation, so it contains zero shift information — it carries only scene content
and illumination. Dividing it out whitens the spectrum, which turns a broad
correlation hill into an impulse and makes the method invariant to gain and bias.
The cost is noise amplification in low-energy frequency bins, which is why we
expose the `beta` exponent.

**Q4. What is `beta`?**
`R = F2 conj(F1) / |F2 conj(F1)|^beta`. At `beta = 1` it is pure phase
correlation; at `beta = 0` it is plain cross-correlation. We measured peak
isolation on a noisy pair and found the optimum at **0.8, not 1.0** — full
whitening also amplifies noise-only bins.

**Q5. Why does the answer wrap around?**
The DFT is the Fourier series of the *periodic extension* of the image, so the
only shift it can represent is a circular one. An index above `H/2` is how a
negative shift is represented.

**Q6. Why window the images?**
The periodic extension has a step discontinuity where the right edge meets the
left. A step is broadband, and that energy lands on the spectrum axes and can
outweigh the real content. A Hann window tapers the borders to zero, making the
extension continuous. Honest addendum: on our own synthetic sweeps windowing made
no measurable difference; it is insurance for images with violent edge contrast.

**Q7. Why does windowing hurt on a `np.roll` test pair?**
Because the window is fixed in the frame and does not move with the content. For
a truly circular shift the unwindowed model is already exact, so the window can
only introduce a mismatch. For real translations the situation reverses.

**Q8. How do you get sub-pixel accuracy from an integer array?**
For a fractional shift the correlation surface is a Dirichlet kernel rather than
a single spike, so the samples adjacent to the peak encode the fraction. We fit a
parabola through the three samples on each axis:
`delta = (y(-1) - y(+1)) / (2*(y(-1) + y(+1) - 2*y(0)))`. Measured mean error
0.08 px, worst case 0.12 px.

**Q9. How do you know the answer is right when there is no ground truth?**
Three ways. (a) Confidence metrics — peak height, PSR, and especially the
peak-to-runner-up ratio, which measured 92 on a clean pair and 1.04 on unrelated
images. (b) PSNR and NCC before versus after alignment. (c) The visual overlays:
the difference image collapses towards black and the anaglyph fringes vanish.

**Q10. What are the limits of your method?**
Pure translation only. Measured: 0.5 deg of rotation is harmless, 2 deg degrades
the peak ratio to 3.1, 5 deg produces a wrong answer with ratio 1.05 — and the
confidence metric correctly flags it. Shifts beyond about 40% of the frame become
ambiguous, and scale changes are not handled at all. Log-polar / Fourier-Mellin
is the standard extension, and it reuses the same core function three times.

**Q11. What happens when two things in the scene move differently?**
You get one correlation peak per coherent motion, with heights roughly
proportional to area — a direct consequence of the linearity of the transform. We
exploit this in Bonus 1: the second peak *is* the moving object displacement,
recovered exactly for objects occupying up to 26% of the frame.

**Q12. In the stabiliser, why low-pass the trajectory instead of cancelling all
motion?**
Because not all motion is unwanted. Deliberate pans and tilts are low-frequency;
hand shake is high-frequency, roughly 2 to 10 Hz. Cancelling everything (our
"lock" mode) also cancels the pan and demands a huge crop. Low-pass filtering
keeps what the operator intended and removes only the residual, which is exactly
`correction = LPF(traj) - traj = -HPF(traj)`.

**Q13. Why a zero-phase filter?**
A causal filter delays the trajectory, so the correction would lag the shake and
could make the video worse. Our kernel is symmetric, giving linear phase, and
convolving it centred gives exactly zero phase. We are allowed to do this because
the process is offline and future frames are available.

**Q14. Why Gaussian and not a moving average?**
The moving average has a Dirichlet frequency response with sidelobes around
-13 dB, so shake near a sidelobe leaks through. The Gaussian has no sidelobes.
Measured at radius 16: residual jitter 0.156/0.126 px for the box kernel versus
0.124/0.058 px for the Gaussian, at identical crop cost.

**Q15. Does the cumulative sum drift?**
Measured over 300 frames with per-frame noise up to sigma 0.10: final drift under
1 px. The per-frame estimates are unbiased, so the errors random-walk rather than
accumulate. Keyframe re-anchoring is the standard extra safeguard, and the
low-pass filter absorbs slow drift anyway, because drift is low-frequency by
definition.

**Q16. Why is there a black border, and why did you crop?**
Steering each frame back onto the smoothed path moves content, exposing area
outside the original frame. Cropping is the honest price; we measured 7.4 px on a
256 px frame, i.e. 2.9% per side. Every commercial stabiliser pays the same cost.

**Q17. You used Pillow and imageio. Is that allowed?**
They only decode files. Every mathematical operation — the transforms, the
cross-power spectrum, the peak search, the sub-pixel fit, the warping, the
trajectory filter — is numpy code we wrote. Decoding H.264 is not a signals task.

**Q18. What would you do with more time?**
Fourier-Mellin for rotation and scale; upsampled-DFT refinement to 1/100 px;
block-wise correlation with median voting for scenes containing large moving
subjects; and a real-time causal variant using a Kalman filter on the trajectory
instead of an offline zero-phase FIR.

---

## Part C — Report and presentation checklist

Figures, in the order they should appear:

- [ ] The two input images
- [ ] Their log-magnitude spectra side by side — visually identical, which proves
      the shift invariance of magnitude
- [ ] The magnitude/phase swap experiment, proving structure lives in the phase
- [ ] `angle(R)` — the straight, evenly spaced phase fringes
- [ ] The correlation surface in 3D: one needle
- [ ] The same surface at `beta = 0`: a broad hill. This is the comparison slide
- [ ] Difference image, before and after alignment
- [ ] Anaglyph overlay, before and after
- [ ] Error table: true shift versus estimated, over many synthetic trials
- [ ] `beta` sweep table
- [ ] Rotation-tolerance table
- [ ] Timing versus image size
- [ ] Bonus 1: the two photos, the change mask, the two blobs, the background
      plate, and three or four frames of the animation
- [ ] Bonus 2: raw versus smoothed trajectory; trajectory spectrum with the
      cutoff line; the filter frequency response; before/after ITF
- [ ] Confidence metrics table, including the deliberate failure cases

Sentences worth memorising:

- "A translation in space is a linear phase ramp in frequency. We measure its
  slope."
- "Magnitude tells you which frequencies are present; phase tells you where
  things are. We threw the magnitude away on purpose."
- "The same equation that measures the motion also renders it."
- "Hand shake and intentional panning are separable because they live in
  different parts of the frequency spectrum."
