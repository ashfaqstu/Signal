# 03 — Bonus 1: Animating a Moving Object From Two Photographs

**The task.** Two photographs of the same scene. Between them, one object moved.
Produce an animation of that object gliding smoothly from where it was to where
it ended up.

---

## Verdict: yes, absolutely possible — and it is genuinely the *same* project

This was the important question, so it gets answered first and precisely.

Not only is it possible, it uses your core phase-correlation function **three
separate times**, and one of the steps is a direct, visible consequence of the
theory in [01-THEORY.md](01-THEORY.md). This is not a bolt-on. Done this way it
is the strongest possible argument that you understood the core.

We built and ran the full pipeline on synthetic data before writing this
document. Every number quoted below is measured, not assumed.

### Where the core project gets used

| Stage | Core function used | What it gives you |
|---|---|---|
| 1. Remove accidental camera movement between the two shots | `phase_correlation` on the full frame | global shift (dy, dx) |
| 2. Find the object displacement | `phase_correlation` again — either the **second peak** of the same surface, or a local run on two crops | object motion (ody, odx) |
| 3. Render every intermediate frame | `fourier_shift` — the shift theorem run forwards | smooth sub-pixel motion, no interpolation library |

### The elegant bit (put this on a slide)

When a scene contains two regions moving differently, the phase correlation
surface does not produce one peak — **it produces one peak per motion, with
heights roughly proportional to how much of the frame each region occupies.**
That falls straight out of linearity: the cross-power spectrum of a sum is the
sum of the cross-power spectra, so each coherent motion contributes its own
delta.

Our measurement: same scene, background stationary, one disc moved by exactly
(-20, +220) px. A *single* global `phase_correlation` call, reading the largest
peak and then the largest peak outside a 21x21 box around it.

| object radius | area of frame | background peak | object peak | object peak location |
|---|---|---|---|---|
| 20 px | 0.7% | 0.596 | 0.250 | (-20, 220) correct |
| 40 px | 2.9% | 0.453 | 0.281 | (-20, 220) correct |
| 60 px | 6.5% | 0.326 | 0.230 | (-20, 220) correct |
| 80 px | 11.6% | 0.235 | 0.179 | (-20, 220) correct |
| 100 px | 18.2% | 0.139 | 0.114 | (-20, 220) correct |
| 120 px | 26.2% | 0.055 | **0.069** | (-20, 220) correct |
| 140 px | 35.6% | 0.023 | 0.035 | (-20, -58) WRONG |

Three findings worth reporting sit in that table:

1. The object displacement is recovered **exactly**, from one FFT pair, for every
   object size up to 26% of the frame.
2. At 26% the object peak **overtakes** the background peak. Past that point,
   "which peak is the camera" stops being answerable by height alone.
3. Beyond about 35% the method fails outright. State this limit, do not hide it.

### The matching limit on stage 1

The same effect decides when a moving object corrupts the *global* estimate.
Measured, with a true camera shift of (4, -6):

| object area | global estimate | |
|---|---|---|
| 0.9% | (4.00, -6.00) | correct |
| 3.7% | (4.00, -6.00) | correct |
| 8.9% | (4.00, -6.00) | correct |
| 18.2% | (4.00, -5.99) | correct |
| 30.7% | (-16.00, 213.99) | **locked onto the object instead** |

So: **as long as the moving object occupies less than about 20% of the frame,
plain global phase correlation finds the camera motion and ignores the object
completely.** That is a strong, quotable robustness result, and it is why the
pipeline below needs no special masking in the common case.

---

## Shooting the input photographs

The method is only as good as the data. Give yourself:

- **Tripod, or at least the same spot.** Small camera movement is fine — stage 1
  removes it. Rotation is not, because rotation is outside the model.
- **Same lighting.** Not for the alignment (phase correlation does not care) but
  for the *change detection* in stage 2, which is a plain difference.
- **Object well under 20% of the frame.** A mug on a table, a toy car, a person
  at middle distance. Not a close-up filling the frame.
- **Static background.** No trees in wind, no other people walking, no moving
  shadows.
- **Manual exposure and manual focus** if your camera allows it. Auto-exposure
  re-meters when the object moves and shifts the whole frame brightness, which
  floods your difference mask.

---

## The pipeline

```
 img1 ----+
          +--> [1] global phase correlation --> (dy,dx) --> shift img2 --> img2_aligned
 img2 ----+
                                |
        +-----------------------+
        v
 [2] |img2_aligned - img1| --> threshold --> [3] connected components --> blobs A and B
        |
        v
 [4] local phase correlation on crops around A and B  -->  object motion (ody, odx)
        |
        v
 [5] background plate: fill hole A from img2_aligned, hole B from img1
        |
        v
 [6] sprite = object pixels from img1 + feathered alpha
        |
        v
 [7] for t in 0..1:  fourier_shift(sprite, t*ody, t*odx) composited onto plate
        |
        v
 [8] matplotlib FuncAnimation --> GIF / MP4
```

---

## Step 1 — Global alignment

Straight reuse of the core, no modification:

```python
from core.phase_correlation import phase_correlation
from core.transform import fourier_shift

dy, dx, corr = phase_correlation(g1, g2)          # grayscale versions
img2_al = fourier_shift(rgb2, -dy, -dx)           # works on colour too
```

Measured on our test scene, with a true camera shift of (4, -6) and a moving disc
present: estimate **(4.00, -6.00)**. Exact.

---

## Step 2 — Change mask

```python
d = np.abs(g2_al - g1)
d[:12, :] = d[-12:, :] = 0                 # kill Fourier-shift border ringing
d[:, :12] = d[:, -12:] = 0
thr = d.mean() + 3.0 * d.std()             # simple, adaptive, works
mask = d > thr
```

On our scene this selected 1.76% of pixels: the two disc positions and almost
nothing else. Tune the `3.0` interactively — it is a natural UI slider.

If the mask comes out speckly, smooth `d` before thresholding. Do it with an FFT
convolution, to stay on theme:

```python
def fft_blur(a, sigma):
    H, W = a.shape
    ky = np.fft.fftfreq(H).reshape(-1, 1)
    kx = np.fft.fftfreq(W).reshape(1, -1)
    G = np.exp(-2 * (np.pi * sigma) ** 2 * (ky ** 2 + kx ** 2))   # Gaussian LPF
    return np.real(np.fft.ifft2(np.fft.fft2(a) * G))
```

That is a low-pass filter applied as a multiplication in the frequency domain —
the convolution theorem, which is the other half of your syllabus. Use it, and
say so in the report.

---

## Step 3 — Connected components, in pure Python

No scipy needed. Breadth-first flood fill, about 25 lines:

```python
from collections import deque

def label_components(mask, min_size=50):
    H, W = mask.shape
    lab = np.zeros((H, W), np.int32)
    comps, nxt = [], 0
    for sy in range(H):
        for sx in range(W):
            if mask[sy, sx] and lab[sy, sx] == 0:
                nxt += 1
                lab[sy, sx] = nxt
                q, pix = deque([(sy, sx)]), []
                while q:
                    y, x = q.popleft()
                    pix.append((y, x))
                    for ny, nx in ((y-1, x), (y+1, x), (y, x-1), (y, x+1)):
                        if 0 <= ny < H and 0 <= nx < W and mask[ny, nx] and lab[ny, nx] == 0:
                            lab[ny, nx] = nxt
                            q.append((ny, nx))
                p = np.array(pix)
                if len(pix) >= min_size:
                    comps.append(dict(label=nxt, size=len(pix),
                                      cy=p[:, 0].mean(), cx=p[:, 1].mean(),
                                      y0=p[:, 0].min(), y1=p[:, 0].max(),
                                      x0=p[:, 1].min(), x1=p[:, 1].max()))
                else:
                    lab[p[:, 0], p[:, 1]] = 0          # discard speckle
    comps.sort(key=lambda c: -c["size"])
    return lab, comps
```

Keep the two largest components. Measured on our scene: exactly 2 components,
1517 px each, centroids **(170.0, 110.0)** and **(150.0, 330.0)** — the true disc
centres, to the pixel.

**Which blob is "before" and which is "after"?** Compare the two images inside
each bounding box. The blob where the object *is* looks like the object; the blob
where it *was* looks like background. If the object is darker than the
background, the "before" blob is the one that is darker in `img1`. A more general
test that assumes nothing about brightness: whichever blob region in `img1`
correlates better with the *other* blob region in `img2_aligned`.

---

## Step 4 — Object displacement, three independent ways

**Way A — centroid difference.** `(cyB - cyA, cxB - cxA)`. Measured: exactly
(-20.00, 220.00). Simple, good to about a pixel when the blobs are clean.

**Way B — local phase correlation.** Do this one; it is the point of the project.
Crop a patch around each blob, run the core function on the pair, then add back
the difference of the crop origins:

```python
P = 96
pa, ay, ax = patch(g1,    cA["cy"], cA["cx"], P)     # object at A, from img1
pb, by, bx = patch(g2_al, cB["cy"], cB["cx"], P)     # object at B, from img2
rdy, rdx, _ = phase_correlation(pa, pb)
ody = rdy + (by - ay)
odx = rdx + (bx - ax)
```

Measured: **(-20.00, 220.00)** — agreeing with the centroid to two decimals, now
sub-pixel accurate and insensitive to the exact threshold chosen in step 2.

**Way C — free, no extra work.** Read the second peak of the *global* correlation
surface from step 1, exactly as in the table at the top of this document.

Report all three and show they agree. Three independent estimates converging is
the kind of validation that earns marks.

---

## Step 5 — The background plate

You need a clean background with no object in it. You already have everything
required: wherever the object sits in `img1`, `img2_aligned` shows clean
background, and the other way round.

```python
holeA = dilate(lab == cA["label"], 6)       # widen a little to swallow the halo
plate = img1.copy()
plate[holeA] = img2_al[holeA]
```

with a dependency-free dilation:

```python
def dilate(m, r=4):
    out = m.copy()
    for k in range(1, r + 1):
        out |= np.roll(m, k, 0) | np.roll(m, -k, 0) | np.roll(m, k, 1) | np.roll(m, -k, 1)
    return out
```

Measured against the true background: **mean absolute error 0.0000, maximum
0.0002** over the image interior. The plate is essentially perfect.

Two practical notes:

- **Dilate generously.** The soft edge of the object, and its shadow, extend past
  the thresholded blob. Under-dilating leaves a faint ghost outline, which is the
  most common visible defect in this feature.
- If the two blobs overlap (the object barely moved) this trick fails — there is
  no frame in which that patch is clean. Detect the overlap and either inpaint by
  edge extension or, more sensibly, reshoot with a larger movement.

---

## Step 6 — The sprite and its alpha

```python
y0, y1, x0, x1 = cA["y0"], cA["y1"], cA["x0"], cA["x1"]
pad = 8
sprite = img1[y0-pad:y1+pad, x0-pad:x1+pad]                  # RGB
alpha  = (lab == cA["label"])[y0-pad:y1+pad, x0-pad:x1+pad].astype(float)
alpha  = np.clip(fft_blur(alpha, sigma=1.5), 0, 1)           # feather the edge
```

Feathering matters enormously. A hard binary alpha gives a cut-out-paper look
with visible jaggies; two pixels of Gaussian feather makes it read as a real
object. Reuse `fft_blur` from step 2 — again, low-pass filtering as
multiplication in frequency.

---

## Step 7 — Render the in-between frames

```python
def compose(plate, sprite, alpha, oy, ox, dy, dx):
    """Place the sprite on the plate at its original corner (oy, ox)
    plus a possibly fractional offset (dy, dx)."""
    H, W = plate.shape[:2]
    sh, sw = alpha.shape
    canvas = np.zeros((H, W))
    layer  = np.zeros((H, W, 3))
    canvas[oy:oy+sh, ox:ox+sw] = alpha
    layer[oy:oy+sh, ox:ox+sw]  = sprite
    canvas = fourier_shift(canvas, dy, dx)          # sub-pixel, from the core
    layer  = fourier_shift(layer,  dy, dx)
    canvas = np.clip(canvas, 0, 1)[..., None]
    return plate * (1 - canvas) + layer * canvas

frames, N = [], 60
for i in range(N):
    t = i / (N - 1)
    t = t * t * (3 - 2 * t)                         # smoothstep easing
    frames.append(compose(plate, sprite, alpha, y0-pad, x0-pad, t*ody, t*odx))
```

Notice what step 7 actually is: **the shift theorem, used as a renderer.** The
same equation that measured the motion now produces it. Say that sentence out
loud during the demo — it is the cleanest possible statement of what a Fourier
project is for.

### Polish, cheap to add and very visible

- **Easing.** Linear motion looks robotic. `smoothstep` above, or ease-in-out
  cubic, looks intentional.
- **Motion blur.** Average 3 to 5 sub-steps per output frame. Physically
  motivated — it is what a real shutter does — and it hides sub-pixel seams.
- **Onion-skin trail.** Composite the sprite at `t`, `t-0.1`, `t-0.2` with
  decreasing alpha.
- **Path overlay.** Draw the trajectory line and an arrow annotated with the
  measured `(ody, odx)`, tying the animation back to the measurement.
- **Ping-pong loop.** `frames + frames[::-1]` gives a seamless GIF.

---

## Step 8 — Export

```python
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter

fig, ax = plt.subplots(figsize=(8, 6))
ax.axis("off")
im = ax.imshow(frames[0])
anim = FuncAnimation(fig, lambda i: (im.set_data(frames[i]),),
                     frames=len(frames), interval=33, blit=True)
anim.save("outputs/object_motion.gif", writer=PillowWriter(fps=30))
```

`PillowWriter` needs no ffmpeg, so the GIF always works. For MP4, install
`imageio-ffmpeg` and use `FFMpegWriter`.

---

## Build order and acceptance tests

| # | Step | Acceptance test |
|---|---|---|
| B1.1 | Synthetic two-frame generator (background + pasted disc, known motion) | You know the true answer before you start |
| B1.2 | Global alignment | Recovers the camera shift you injected |
| B1.3 | Difference mask | Exactly two blobs, no speckle |
| B1.4 | Connected components | Centroids match the true disc centres within 1 px |
| B1.5 | Object displacement | Centroid, local correlation and second-peak methods agree |
| B1.6 | Background plate | Error against the true background under 0.001 |
| B1.7 | Sprite composite at t=0 and t=1 | Reproduces `img1` and `img2_aligned` |
| B1.8 | Animation export | GIF plays, motion smooth, no ghost outline |

B1.7 is the one that matters most: **at `t=0` your composite must reproduce the
original first photograph, and at `t=1` the aligned second photograph.** If those
two endpoints are not right, nothing in between will be either.

---

## Honest limitations to state in the report

1. **Translation only.** If the object also rotated — a walking person's limbs, a
   rolling ball — you are animating a rigid slide of a non-rigid thing. It will
   look slightly wrong, and you should say why: the model in
   [01-THEORY.md](01-THEORY.md) has exactly two parameters.
2. **Object must occupy under about 20 to 26% of the frame** (measured above).
3. **Static background and stable lighting** are required for change detection.
4. **Shadows travel with the object.** Usually helpful — they get included in the
   sprite and move along — but they will not re-project correctly.
5. **The object must move far enough** that the two blobs do not overlap.
6. **No occlusion handling.** If the object should pass behind something, it will
   glide over the top instead.

Every one of these follows from a stated assumption rather than from a bug.
Presenting them as an "assumption to consequence" table is far stronger than
presenting them as excuses.

Next: **[04-BONUS-2-VIDEO-STABILIZER.md](04-BONUS-2-VIDEO-STABILIZER.md)**
