# 04 — Bonus 2: Video Stabiliser

**The task.** Take shaky handheld video, remove the shake, keep the intentional
camera movement, output smooth video.

---

## Verdict: yes — and this is the strongest of the three deliverables

Of everything in this project, the stabiliser is the one that best fits the
*Signals and Systems* syllabus, because it uses **both halves** of it:

- **Frequency-domain image analysis** (your core project) to measure motion, and
- **1D LTI filtering** to separate wanted motion from unwanted motion.

The second half is the insight that makes it a signals project rather than a
video-editing exercise, so state it explicitly and early:

> Accumulate the frame-to-frame shifts into a camera **trajectory**. That
> trajectory is a 1D signal sampled at the frame rate. Intentional camera
> movement — a pan, a tilt, a slow follow — is the **low-frequency** part.
> Hand shake is the **high-frequency** part, typically 2 to 10 Hz.
> Stabilising is therefore just **low-pass filtering the trajectory** and
> steering each frame back onto the smoothed path.
>
> `correction[n] = LPF(trajectory)[n] - trajectory[n]`
>
> which is exactly `-HPF(trajectory)[n]`. **The correction you apply is the
> high-frequency component you are removing.** That single equation is the whole
> feature.

Everything below was built and measured on a synthetic shaky sequence (300
frames, 30 fps, 256x256, containing a real pan, a real tilt, 4.3 Hz and 5.7 Hz
shake, plus white jitter) before this document was written. The numbers are
measurements.

### Headline results

| Metric | Before | After | |
|---|---|---|---|
| Inter-frame jitter, std | 3.53 / 3.39 px | **0.16 / 0.05 px** | ~20x reduction |
| ITF (mean consecutive-frame PSNR) | 25.58 dB | **33.73 dB** | +8.15 dB |
| Crop needed | — | 7.4 px per side | 2.9% of the frame |
| Trajectory error vs ground truth | — | max 0.002 px | over 150 frames |

---

## How much of the core project gets reused? Almost all of it.

| Stabiliser stage | Core component |
|---|---|
| Measure motion between frame n-1 and n | `phase_correlation`, unchanged |
| Decide whether to trust that measurement | `peak_metrics`, unchanged |
| Apply the correction with sub-pixel accuracy | `fourier_shift`, unchanged |
| Analyse the shake spectrum | `np.fft.rfft` on the trajectory — the same transform, in 1D |

The only genuinely new code is the trajectory filter and the video I/O.

---

## The pipeline

```
 video ──▶ frames[0..N-1]
              │
              ▼
   [1] for n in 1..N-1:  (dy,dx)[n] = phase_correlation(frame[n-1], frame[n])
              │            + confidence gate  (reject cuts / bad locks)
              ▼
   [2] trajectory[n] = cumulative sum of (dy,dx)      <- a 1D signal, fs = fps
              │
              ▼
   [3] smooth[n] = LPF(trajectory[n])                 <- zero-phase FIR
              │
              ▼
   [4] correction[n] = smooth[n] - trajectory[n]      <- this IS the HPF residual
              │
              ▼
   [5] out[n] = fourier_shift(frame[n], correction[n])
              │
              ▼
   [6] crop by max|correction|, rescale, write video
```

---

## Step 1 — Video in, video out

This is the one place where a third-party library is legitimate: decoding H.264
is not a signals task. Say so in your report and nobody will object.

```python
import imageio.v3 as iio
import numpy as np

def read_frames(path, max_frames=None, scale=1.0):
    frames = []
    for i, f in enumerate(iio.imiter(path)):
        if max_frames and i >= max_frames:
            break
        a = np.asarray(f, dtype=np.float64) / 255.0
        frames.append(a)
    return frames

def write_frames(path, frames, fps=30):
    out = [np.clip(f, 0, 1) for f in frames]
    iio.imwrite(path, [(f * 255).astype(np.uint8) for f in out], fps=fps)
```

`pip install imageio imageio-ffmpeg`. If ffmpeg refuses to install, fall back to
exporting a GIF with `PillowWriter`, or to reading a folder of PNG frames — the
algorithm does not care where the pixels came from.

**Work at reduced resolution while developing.** Estimate the shifts on
half-size or quarter-size grayscale frames, then multiply the resulting shift by
the scale factor and apply it to the full-resolution colour frames. Motion
estimation does not need the detail, and your iteration time drops by 4x or 16x.

---

## Step 2 — Pairwise shifts and the trajectory

```python
from core.phase_correlation import phase_correlation
from core.metrics import peak_metrics

def estimate_trajectory(gray_frames, min_ratio=2.0):
    N = len(gray_frames)
    d = np.zeros((N, 2))          # per-frame delta, d[0] = (0, 0)
    conf = np.ones(N)
    for n in range(1, N):
        dy, dx, corr = phase_correlation(gray_frames[n-1], gray_frames[n])
        _, _, ratio = peak_metrics(corr)
        conf[n] = ratio
        if ratio < min_ratio:     # scene cut or lost lock -> assume no motion
            dy = dx = 0.0
        d[n] = (dy, dx)
    return np.cumsum(d, axis=0), d, conf
```

`trajectory[n]` is where the frame content has drifted to by frame `n`, relative
to frame 0. It is your 1D signal. **Plot it immediately** — before any filtering,
before any warping. You should see a smooth curve (the real camera move) with
fuzz on top (the shake). That plot alone explains the entire feature to an
examiner in three seconds.

### Accuracy and drift, measured

Cumulative summation is the obvious worry: does the error accumulate? Measured
over **300 frames** against ground truth, with increasing amounts of per-frame
sensor noise added:

| frame noise sigma | final drift, y | final drift, x | worst error over the run |
|---|---|---|---|
| 0.00 | +0.001 px | -0.002 px | 0.002 px |
| 0.02 | -0.090 px | -0.010 px | 0.093 px |
| 0.05 | +0.001 px | -0.310 px | 0.319 px |
| 0.10 | -0.209 px | +0.594 px | 0.926 px |

Drift is well under a pixel even at heavy noise. This is a genuinely good result
and worth reporting: because each estimate is unbiased, the errors random-walk
rather than accumulate systematically.

Two extra safeguards for long or difficult clips:

- **Keyframe re-anchoring.** Every ~100 frames, also correlate against a stored
  keyframe and blend that absolute measurement into the trajectory.
- **The low-pass filter itself absorbs slow drift**, because drift is by
  definition low-frequency — the smoothed path follows it instead of fighting it.

### Confidence gating catches scene cuts for free

Measured peak ratios on the same clip:

| Situation | peak ratio |
|---|---|
| Normal consecutive frames | median 32.6, minimum 24.7 |
| Across an artificial hard cut | **1.14** |

An enormous, unambiguous gap. A threshold anywhere between 3 and 15 separates
them perfectly. Plot `conf[n]` underneath the trajectory: the dips mark exactly
the frames your estimator did not trust, and being able to say *why* your system
knows when it is wrong is worth a lot.

---

## Step 3 — Filter design (the part that is pure Signals and Systems)

```python
def smooth_trajectory(traj, radius, kind="gauss"):
    """Zero-phase FIR low-pass. Symmetric kernel + 'edge' padding + 'valid'
    convolution => output length equals input length, and there is NO delay."""
    if kind == "box":
        k = np.ones(2 * radius + 1)
    else:
        u = np.arange(-radius, radius + 1)
        sigma = radius / 2.0
        k = np.exp(-0.5 * (u / sigma) ** 2)
    k = k / k.sum()                                     # unity DC gain
    padded = np.pad(traj, radius, mode="edge")          # avoid end transients
    return np.convolve(padded, k, mode="valid")
```

Four design decisions in nine lines, and you should be able to defend each one:

1. **Symmetric kernel ⇒ linear phase ⇒ zero phase after centring.** A causal
   filter would delay the trajectory, so your "correction" would lag the shake
   and make the video worse. This is offline processing, so we are allowed to use
   the future — use it.
2. **`k / k.sum()` ⇒ `H(0) = 1`.** Unity gain at DC means a static shot stays put
   instead of slowly sliding.
3. **`mode="edge"` padding** stops the filter from dragging the first and last
   frames toward zero.
4. **Gaussian rather than box.** A box filter's response is a Dirichlet kernel
   with sidelobes at -13 dB, so shake near a sidelobe leaks straight through. The
   Gaussian has no sidelobes.

Measured, radius 16, same clip:

| kernel | residual motion std (y, x) | max correction |
|---|---|---|
| box | 0.156 / 0.126 px | 5.6 px |
| gaussian | **0.124 / 0.058 px** | 5.6 px |

Same crop cost, visibly better result. Plot both frequency responses next to
each other and the sidelobes explain the table:

```python
k = gaussian_kernel(radius)
Hf = np.abs(np.fft.rfft(k, 4096))
f  = np.fft.rfftfreq(4096, d=1.0 / fps)      # in Hz
plt.semilogy(f, Hf)
```

### Choosing the cutoff

For a Gaussian of standard deviation `sigma` frames, continuous theory gives
`H(f) = exp(-2 pi^2 sigma^2 f^2)`, so the -3 dB point sits at
`f = 0.1325 / sigma` cycles per frame. We measured the *actual* truncated,
normalised kernel (radius = 2 sigma) and got consistently about 10% higher:

| sigma | measured f(-3dB) | 0.1325/sigma | ratio |
|---|---|---|---|
| 5 | 0.02905 | 0.02650 | 1.10 |
| 10 | 0.01465 | 0.01325 | 1.11 |
| 20 | 0.00732 | 0.00663 | 1.10 |

Truncating the kernel at 2 sigma widens the passband slightly. So use the
**empirical** constant:

```
f_cutoff (Hz)  ~=  0.1465 * fps / sigma          sigma = radius / 2
sigma (frames) ~=  0.1465 * fps / f_cutoff
```

At 30 fps, a 0.5 Hz cutoff needs `sigma ~= 8.8`, so `radius ~= 18`. Deriving
that number rather than guessing it is exactly the kind of thing that separates
a good project from a working one.

### Radius sweep, measured

| radius | sigma | cutoff | jitter std after (y, x) | max crop |
|---|---|---|---|---|
| 5 | 2.5 | 1.76 Hz | 0.20 / 0.20 px | 6.6 px |
| 10 | 5.0 | 0.88 Hz | 0.17 / 0.07 px | 6.9 px |
| 16 | 8.0 | 0.55 Hz | 0.16 / 0.05 px | 7.4 px |
| 24 | 12.0 | 0.37 Hz | 0.15 / 0.03 px | 7.7 px |
| 40 | 20.0 | 0.22 Hz | 0.12 / 0.03 px | 7.6 px |

Raw jitter was 3.53 / 3.39 px. The trade-off is visible: a longer filter is
smoother but demands more crop and fights harder against intentional motion.
**Radius 16 is the sweet spot here** — most of the benefit, modest crop.

### The figure to put on the slide

Plot the trajectory spectrum: `np.abs(np.fft.rfft(traj_x - traj_x.mean()))`
against frequency in Hz. You will see energy concentrated near DC (the pan) and
a distinct bump in the 4 to 10 Hz region (the shake). Draw your cutoff as a
vertical line. **That one plot proves the entire premise of the feature** — that
wanted and unwanted motion are separable in frequency.

---

## Step 4 — Two stabilisation modes, one line apart

```python
if mode == "smooth":                    # keep intentional motion (default)
    target = smooth_trajectory(traj, radius)
elif mode == "lock":                    # remove ALL motion, tripod look
    target = np.zeros_like(traj)
correction = target - traj
```

- **Smooth-follow.** Subtracts only the high-frequency residual. Pans and tilts
  survive. Small crop. Use this for real footage.
- **Full lock.** Forces the trajectory to zero, i.e. every frame is registered to
  frame 0. Looks like a tripod, but any real camera movement becomes a huge
  correction and eats the frame. Only sensible for near-static shots — where it
  is spectacular, e.g. locking a time-lapse.

Offer both in the UI as a single toggle. It demonstrates that you understand the
filter is doing the choosing, not some special algorithm.

---

## Step 5 — Warping and the crop

```python
from core.transform import fourier_shift

stabilised = [fourier_shift(frames[n], correction[n, 0], correction[n, 1])
              for n in range(N)]
```

Sub-pixel, no interpolation library, straight from the shift theorem.

Every corrected frame has an invalid border where content wrapped around. Crop it
away, equally on all sides, then scale back up:

```python
my = int(np.ceil(np.abs(correction[:, 0]).max())) + 2
mx = int(np.ceil(np.abs(correction[:, 1]).max())) + 2
cropped = [f[my:-my, mx:-mx] for f in stabilised]
```

Measured on our clip: 7.4 px of correction on a 256 px frame, so a **2.9% crop**
per side. Report the crop factor — it is the honest price of stabilisation, and
every commercial stabiliser pays it too.

Alternatives if you want to avoid cropping: mirror-pad before shifting, or fill
the missing border from a neighbouring frame (which usually *does* contain those
pixels — that is the same hole-filling trick as
[Bonus 1 step 5](03-BONUS-1-MOVING-OBJECT.md)).

---

## Step 6 — Prove it worked, numerically

Do not rely on "it looks smoother". Two metrics, both cheap:

```python
def itf(frames, margin=40):
    """Inter-frame transformation fidelity: mean PSNR between consecutive
    frames. Higher = consecutive frames are more similar = steadier."""
    vals = []
    for a, b in zip(frames[:-1], frames[1:]):
        e = np.sqrt(((a[margin:-margin, margin:-margin]
                      - b[margin:-margin, margin:-margin]) ** 2).mean())
        vals.append(99.0 if e == 0 else 20 * np.log10(1.0 / e))
    return float(np.mean(vals))

def jitter_std(traj):
    """Std of frame-to-frame displacement. Lower = smoother."""
    return float(np.diff(traj, axis=0).std(axis=0).mean())
```

Our measurements: ITF **25.58 dB → 33.73 dB (+8.15 dB)**, jitter std **3.5 px →
0.16 px**. Put the before/after numbers in a table and the two trajectory curves
(raw and smoothed) on one axis. That is your results section, done.

---

## Step 7 — Robustness, when you have time

**A large moving object in frame.** From
[Bonus 1](03-BONUS-1-MOVING-OBJECT.md), once a moving subject exceeds roughly
26% of the frame, phase correlation locks onto the subject instead of the
background. Two fixes:

- **Block voting.** Split the frame into a 3x3 grid, run `phase_correlation` on
  each block independently, take the **median** of the nine estimates. A subject
  occupying up to four blocks is outvoted. Costs 9 small FFT pairs, which are
  together cheaper than one big one.
- **Centre-weighted or edge-weighted windowing.** Subjects tend to be centred;
  background dominates the periphery. Weight accordingly.

**Rotation.** Real handheld shake includes roll. Pure translation cannot fix it,
and past about 2 degrees the estimate degrades measurably
([02 step 9](02-CORE-IMPLEMENTATION.md)). Either state the limitation, or
implement the log-polar extension from
[01 section 14](01-THEORY.md#14-stretch-goal-rotation-and-scale-fourier-mellin)
and stabilise rotation the same way.

**Rolling shutter.** CMOS sensors expose row by row, so fast pans skew the image
non-rigidly. No global translation can fix that. Name it as out of scope.

**Speed.** Measured cost of one `phase_correlation` call: 9.3 ms at 256x256,
39.4 ms at 512x512, 273 ms at 1024x1024. So a 1000-frame clip at 512x512 costs
about 40 s of estimation. Optimisations, in order of value:

1. Estimate on downsampled grayscale, apply to full-resolution colour.
2. Cache each frame's FFT — consecutive pairs share one, halving the transforms.
3. Precompute the Hann window once instead of per call.
4. `np.fft.rfft2` instead of `fft2` for the forward transforms of real input.

---

## Build order and acceptance tests

| # | Step | Acceptance test |
|---|---|---|
| B2.1 | Synthetic shaky-clip generator (crop a moving window out of one big image, known pan + known shake) | Ground truth trajectory is known exactly |
| B2.2 | Frame reader / writer | Round-trip a clip unchanged |
| B2.3 | Pairwise estimation + trajectory | Recovered trajectory matches ground truth to < 0.01 px |
| B2.4 | Drift check over 300 frames | Final drift under 1 px, even with noise |
| B2.5 | Smoothing filter | Kernel sums to 1; output length equals input length; a constant input comes out constant |
| B2.6 | Frequency response plot | -3 dB point matches `0.1465 * fps / sigma` |
| B2.7 | Warp + crop | Stabilised clip has no wrapped border visible |
| B2.8 | Metrics | ITF improves by several dB; jitter std drops by 10x or more |
| B2.9 | Confidence gating | An artificial cut is detected (peak ratio collapses to ~1) |
| B2.10 | Real handheld footage | Visibly steadier, no wobble artefacts |

**Build B2.1 first.** A synthetic clip with a trajectory you injected yourself is
the only way to know whether your estimator or your filter is at fault when the
output looks wrong. Take one large photo, crop a 256x256 window out of it whose
position follows `pan + shake`, and you have a perfect test clip in ten lines.

---

## Honest limitations to state in the report

1. **Translation only** — no rotation, no zoom, no rolling-shutter correction.
2. **A dominant moving subject breaks the global estimate** past about 26% of
   frame area; block voting extends this but does not remove it.
3. **Cropping is unavoidable**; we measured 2.9% per side, and it grows with the
   filter radius.
4. **Offline, not real time.** Zero-phase filtering needs future frames.
5. **Parallax.** If the camera translates in 3D, near and far objects move by
   different amounts and no single global shift is correct. Block voting picks
   whichever depth dominates.
6. **Fourier warping is circular** and rings slightly at strong edges; the crop
   removes the visible part.

---

## Suggested demo script for the presentation

1. Show the shaky input clip. Everyone recognises the problem instantly.
2. Show the **trajectory plot** — smooth curve plus fuzz. "This is our signal."
3. Show the **trajectory spectrum** with the shake bump and your cutoff line.
   "Wanted motion here, unwanted motion there. They are separable."
4. Show raw and smoothed trajectories overlaid. "We low-pass filtered it."
5. Show the stabilised clip side by side with the original.
6. Show the numbers: ITF +8 dB, jitter 3.5 px to 0.16 px, crop 2.9%.
7. Drag the cutoff slider live from 2 Hz down to 0.2 Hz and let them watch the
   trade-off between smoothness and crop.

Step 7 is what they will remember.

Next: **[05-UI-PROMPT.md](05-UI-PROMPT.md)**
