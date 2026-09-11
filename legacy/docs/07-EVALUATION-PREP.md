# 07 — Preparing for the Live Evaluation Task

Your examiner will hand you a small thing to implement, modify, or explain, with
them watching. This document is the preparation: what they are likely to ask,
where each answer lives, and the exact change to make.

Everything in [Part 3](#part-3--the-what-if-table-verified-answers) and
[Part 4](#part-4--manipulation-tricks-the-knobs-that-visibly-reflect) was run and
measured before being written down. **Learn the numbers.** Being able to say
"that will still work, and the peak will drop to about 0.12" *before* pressing
Enter is the single most impressive thing you can do in that room.

**Contents**

- [Part 0 — The first 60 seconds](#part-0--the-first-60-seconds)
- [Part 1 — What they can actually ask](#part-1--what-they-can-actually-ask)
- [Part 2 — The playbook](#part-2--the-playbook)
- [Part 3 — The "what if" table (verified)](#part-3--the-what-if-table-verified-answers)
- [Part 4 — Manipulation tricks: the visible knobs](#part-4--manipulation-tricks-the-knobs-that-visibly-reflect)
- [Part 5 — Rehearsal drills](#part-5--rehearsal-drills)
- [Part 6 — When you get stuck](#part-6--when-you-get-stuck)

---

## Part 0 — The first 60 seconds

Do these four things, in order, every time. It costs a minute and it prevents
every bad outcome.

**1. Repeat the task back in your own words.** "So you want the shift reported in
millimetres instead of pixels, given a known scale factor — is that right?" Half
of all failures are solving the wrong problem. This also buys thinking time.

**2. Classify it out loud** using [Part 1](#part-1--what-they-can-actually-ask).
"That's a display change, so it's in `ui/panels.py`, not in the core." Saying
where it lives *before* opening a file demonstrates ownership of the codebase.

**3. State the plan in one sentence before typing.** "I'll add a number input for
pixels-per-millimetre in the sidebar and multiply in the result block — two
lines." Now if the plan is wrong, they correct you before you have wasted five
minutes.

**4. Say what you expect to see.** "The estimate should stay identical and only
the label changes." Then run it. A prediction that comes true is worth more than
a correct answer that surprises you.

### Three rules for the whole session

- **Never edit `core/phase_correlation.py` for a display request.** If the answer
  can live in the UI or in a wrapper, put it there. Say why: "the core is tested,
  I don't want to touch it for a formatting change."
- **Run the test suite after any core change.** Out loud: "let me re-run the 200
  circular-shift test to confirm I didn't break the convention." That sentence
  alone signals engineering maturity.
- **If asked to break something correct, push back once, politely, with
  evidence.** "The sign convention is fixed and covered by a test — here it is
  passing. I can add an inverted display if you prefer, but I'd rather not flip
  the core." Then do whatever they say.

---

## Part 1 — What they can actually ask

Six categories. The likelihood column is a judgement call, but the *structure* is
what matters — classify fast, then jump to the right section of Part 2.

| # | Category | Likelihood | Where it lives | Typical size |
|---|---|---|---|---|
| A | **Tweak a parameter / add a control** | very high | `apps/ui.py` | 1–3 lines |
| B | **Add a small algorithm variant** | high | `core/*.py` + one control | 5–20 lines |
| C | **Signals-theory demonstration** | high | a new panel, or the console | 5–15 lines |
| D | **Probe a failure mode** ("what if I do this to the image?") | high | nothing to write — you *predict*, then run | 0 lines |
| E | **A new small feature** | medium | new function + one screen entry | 20–40 lines |
| F | **Explain / derive / defend** | certain | your head | 0 lines |

Category D is the one students lose marks on, because it looks like a trick.
It is not a trick — it is checking whether you know the boundary of your model.
[Part 3](#part-3--the-what-if-table-verified-answers) is your answer key.

---

## Part 2 — The playbook

### Category A — parameter tweaks and new controls

| They say | You change | Lines |
|---|---|---|
| "Make the normalisation adjustable" | already a `beta` slider — **demo it instead of coding** | 0 |
| "Use a Hamming window instead of Hann" | `np.hanning` to `np.hamming` in `phase_correlation` | 1 |
| "Let the user pick the window" | selectbox → dict `{"Hann": np.hanning, "Hamming": np.hamming, "Blackman": np.blackman, "None": None}` | 4 |
| "Add a control for X" | `st.slider` after `# --- ADD NEW CONTROLS HERE ---`, pass into the call | 2 |
| "Report the shift in mm" | `st.number_input("px per mm")`, divide in the result block | 2 |
| "Report magnitude and direction instead" | `np.hypot(dy,dx)`, `np.degrees(np.arctan2(dy,dx))` | 2 |
| "Show the result to 4 decimals" | change the f-string | 1 |
| "Save the results to a file" | build a dict, `st.download_button(json.dumps(d), "result.json")` | 3 |

The window selector, written out, because it is the most likely one:

```python
WINDOWS = {"Hann": np.hanning, "Hamming": np.hamming,
           "Blackman": np.blackman, "None": None}
name = st.sidebar.selectbox("Window", list(WINDOWS), index=0)
# in phase_correlation, replace the window block with:
if win_fn is not None:
    w = np.outer(win_fn(H), win_fn(W))
    a, b = a * w, b * w
```

While typing, say: *"Hamming has a higher first sidelobe but doesn't reach zero
at the edges, so the periodic extension still has a small step — I'd expect
slightly worse leakage suppression and basically the same answer."* Then run it
and show the answer is the same.

### Category B — small algorithm variants

**"Add a different sub-pixel method."** Centroid, ~8 lines, sits beside
`_parabolic`:

```python
def _centroid(corr, py, px, r=2):
    H, W = corr.shape
    ys = [(py + i) % H for i in range(-r, r + 1)]
    xs = [(px + j) % W for j in range(-r, r + 1)]
    patch = np.clip(corr[np.ix_(ys, xs)], 0, None)
    if patch.sum() <= 0:
        return 0.0, 0.0
    u = np.arange(-r, r + 1)
    return (float((patch.sum(1) * u).sum() / patch.sum()),
            float((patch.sum(0) * u).sum() / patch.sum()))
```

Then compare both against a `fourier_shift` ground truth and quote your measured
parabolic error (mean 0.08 px, worst 0.12 px) as the benchmark.

**"Handle images of different sizes."** Two valid answers; know both.
Zero-pad to a common size (verified: 256x256 against a 200x220 crop still
returned exactly (17.00, -23.00)), or crop both to the overlap with
`match_shapes`. Padding preserves absolute position; cropping is simpler.

```python
def pad_to(a, shape):
    out = np.zeros(shape)
    out[:a.shape[0], :a.shape[1]] = a - a.mean()
    return out
```

**"Make it work for a shift larger than half the image."** Coarse-to-fine. We
measured `downsample2` recovering dy = 40, 90 and 120 px correctly on a 256 px
frame, agreeing with full resolution to 0.02 px:

```python
cy, cx, _ = phase_correlation(downsample2(ref), downsample2(mov))
guess = (2 * cy, 2 * cx)
fy, fx, _ = phase_correlation(ref, fourier_shift(mov, -guess[0], -guess[1]))
dy, dx = guess[0] + fy, guess[1] + fx
```

**"Add a low-pass mask on the cross-power spectrum."** ~4 lines, and it makes a
good talking point about noise versus localisation — see
[Part 4](#part-4--manipulation-tricks-the-knobs-that-visibly-reflect), knob 12.

```python
ky = np.fft.fftfreq(H).reshape(-1, 1); kx = np.fft.fftfreq(W).reshape(1, -1)
rad = np.hypot(ky, kx)
R = R * np.exp(-0.5 * (rad / cutoff) ** 2)      # cutoff in cycles/pixel
```

**"Align three or more images."** The core is already pairwise; loop it.

```python
shifts = [(0.0, 0.0)]
for m in movs:
    dy, dx, _ = phase_correlation(ref, m)
    shifts.append((dy, dx))
aligned = [ref] + [fourier_shift(m, -dy, -dx) for m, (dy, dx) in zip(movs, shifts[1:])]
```

**"Estimate the shift in only part of the image."** Crop both to the ROI, run the
core, done — this is exactly Bonus 1 step 4. Say so: *"this is the same local
correlation I use to track the moving object."*

### Category C — signals-theory demonstrations

These are the most likely *interesting* requests in a Signals course, because
they test the syllabus rather than your Python.

**"Prove your FFT is being used correctly."** Parseval, one line, and we measured
the ratio at **1.000000000**:

```python
a = ref - ref.mean(); A = np.fft.fft2(a)
print((a**2).sum(), (np.abs(A)**2).sum() / a.size)      # equal
```

**"Show the convolution theorem."** You already use it — `fft_blur` in
[Bonus 1](03-BONUS-1-MOVING-OBJECT.md) is a convolution done as a multiplication.
Show a blur computed both ways and the difference at machine precision.

**"Show it in 1D."** The whole method collapses to about six lines, and running
it convinces an examiner faster than any image:

```python
N = 512
x = np.zeros(N); x[100:140] = 1.0; x += 0.05*np.random.randn(N)
y = np.roll(x, 37)
A, B = np.fft.fft(x), np.fft.fft(y)
R = (B * np.conj(A)) / (np.abs(B * np.conj(A)) + 1e-12)
print(np.argmax(np.real(np.fft.ifft(R))))               # 37
```

**"Demonstrate that magnitude carries no shift information."** The
magnitude/phase swap from [01 section 5](01-THEORY.md#5-magnitude-is-boring-phase-is-everything).
Ten lines, unforgettable visual.

**"Show the effect of sampling / aliasing."** Downsample both images by 2 and
compare: the estimate halves exactly (verified — `downsample2` gave 40.00, 89.99
and 119.99 for true 40, 90 and 120 at full resolution). Then downsample by 8 and
show fine texture aliasing into nonsense.

**"Show linearity."** `fft2(a + b) == fft2(a) + fft2(b)` to machine precision.
One line, and it is the property that makes
[Bonus 1's two-peak trick](03-BONUS-1-MOVING-OBJECT.md) work — link the two.

**"Count the fringes."** The best demo in the whole project. For an exact
circular pair, the number of fringes in `angle(R)` across the spectrum width
**equals the shift in pixels.** Verified exactly:

| true shift | fringes counted |
|---|---|
| 1 px | 1.0 |
| 3 px | 3.0 |
| 7 px | 7.0 |
| 16 px | 16.0 |
| 40 px | 40.0 |

```python
mov = np.roll(img, dx, axis=1)
R = ...                                    # cross-power spectrum
row = np.angle(np.fft.fftshift(R))[H//2, :]
cycles = (np.unwrap(row)[-1] - np.unwrap(row)[0]) / (2*np.pi)     # = dx
```

Say: *"the shift isn't hidden in there — you can literally count it off the phase
plot."* Caveat, and volunteer it: on real non-circular photo pairs the phase is
noisy and naive unwrapping under-counts, which is exactly why we take the
`argmax` of the inverse transform instead of reading the slope directly.

### Category E — small new features

**"Make it tell me whether these two images are even the same scene."** You
already have it: peak ratio ≥ 2.0 locked, ≤ 1.2 no lock. Measured 80 on a clean
pair, 1.06 on unrelated noise. This is a 1-line answer plus a confident
explanation of *why* the metric works.

**"Average several noisy shots into one clean image."** Registration as
denoising, ~10 lines, and the result is dramatic. Measured against theory:

| frames | single frame | after align + average | theory |
|---|---|---|---|
| 2 | 13.95 dB | 16.93 dB | +3.0 dB |
| 4 | 13.98 dB | 20.02 dB | +6.0 dB |
| 8 | 14.01 dB | 23.03 dB | +9.0 dB |
| 16 | 13.96 dB | 26.00 dB | +12.0 dB |

Exactly `10*log10(N)`, every time. *"Averaging N independent noise realisations
divides the noise power by N — but only if you align first, which is what this
project does."*

**"Show me the motion field, not one number."** Block-wise correlation, ~10 lines,
plot as a `quiver`. Verified on a uniform shift with 4x4 blocks: median
(9.00, -13.00) against a true (9, -13), spread 0.00. Then say the important part:
*"the median makes it robust, and the spread is a built-in outlier detector — this
is how I'd stop a large moving subject from hijacking the stabiliser."*

```python
def block_field(a, b, nb=4):
    H, W = a.shape; bh, bw = H//nb, W//nb
    out = []
    for i in range(nb):
        for j in range(nb):
            pa = a[i*bh:(i+1)*bh, j*bw:(j+1)*bw]
            pb = b[i*bh:(i+1)*bh, j*bw:(j+1)*bw]
            dy, dx, _ = phase_correlation(pa, pb)
            out.append((i*bh + bh//2, j*bw + bw//2, dy, dx))
    return out
```

---

## Part 3 — The "what if" table (verified answers)

The examiner does something to one image and asks what your system will do.
**Predict first, then run.** All rows measured on a 256x256 crop pair with a true
shift of **(17, -23)**; the clean baseline is **peak 0.843, ratio 79.98**.

| What they do to the moved image | Estimate | peak | ratio | Verdict |
|---|---|---|---|---|
| nothing (baseline) | (17.00, -23.00) | 0.843 | 80.0 | — |
| same image twice | (0.00, 0.00) | 1.000 | huge | exact |
| a completely unrelated image | garbage | 0.023 | 1.06 | **correctly rejected** |
| brightness + contrast change | (17.00, -23.00) | — | — | **unaffected** |
| gamma 0.5 | (17.00, -23.00) | 0.824 | 75.8 | unaffected |
| gamma 1.5 | (17.00, -23.00) | 0.829 | 80.9 | unaffected |
| gamma 2.2 | (17.00, -23.00) | 0.784 | 64.7 | unaffected |
| Gaussian blur, sigma 1 | (17.00, -23.00) | 0.842 | 79.7 | unaffected |
| Gaussian blur, sigma 2 | (16.99, -22.99) | 0.585 | 42.5 | fine |
| Gaussian blur, sigma 4 | (16.98, -22.92) | 0.121 | 5.2 | still right, peak weak |
| Gaussian blur, sigma 8 | wrong | 0.028 | 1.06 | fails, **and says so** |
| noise sigma 0.05 | (17.00, -23.00) | 0.384 | 15.6 | exact |
| noise sigma 0.15 | (17.01, -23.02) | 0.133 | 6.0 | exact |
| noise sigma 0.30 | (17.01, -22.97) | 0.066 | 2.7 | exact |
| noise sigma 0.60 | (17.06, -23.03) | 0.030 | 1.3 | **still exact** |
| black box over 5% | (17.00, -23.00) | 0.832 | 79.3 | exact |
| black box over 15% | (17.00, -23.00) | 0.748 | 59.4 | exact |
| black box over 30% | (17.00, -23.00) | 0.519 | 24.6 | exact |
| black box over 50% | (17.00, -23.00) | 0.239 | 9.7 | **still exact** |
| contrast inverted (1 − img) | wrong via `argmax` | 0.011 | 1.08 | **see below** |
| rotated 0.5 deg | (0.08, -0.08) | 0.626 | 44.8 | fine |
| rotated 2 deg | (0.45, -0.80) | 0.071 | 3.1 | degraded |
| rotated 5 deg | wrong | 0.024 | 1.05 | fails, and says so |
| scaled 1.02x | (20.30, -20.19) | 0.181 | **7.96** | **wrong, and does NOT say so** |
| scaled 1.05x | wrong | 0.041 | 1.69 | fails |
| scaled 1.10x | wrong | 0.024 | 1.07 | fails |
| different image size | exact after zero-padding | — | — | fine |
| shift of 40 / 90 / 120 px | exact via coarse-to-fine | — | — | fine |

### The four rows to memorise

**1. Noise and occlusion barely matter.** Correct to 0.06 px at noise sigma 0.60,
and *exact* with half the image blacked out. Say why: the shift information is
spread across every frequency bin, so destroying any subset of them leaves the
phase ramp intact. This usually surprises examiners.

**2. Blur does not break the answer, it breaks the confidence.** A Gaussian
kernel is real and symmetric, so it is **zero-phase** — it attenuates magnitudes
without touching phase, and the shift lives in the phase. What dies is the peak
height, because whitening a spectrum that has no high-frequency energy left just
amplifies noise. Exact answer at sigma 4, with peak down from 0.84 to 0.12.
This is one of the strongest "I understand my system" answers available.

**3. Contrast inversion flips the peak negative.** If `mov = 1 - shifted(ref)`
then `F2 = -F1 e^{...}` (away from DC), so `R = -e^{...}` and the inverse
transform is a **negative** delta. `argmax` returns noise; `corr.min()` sits at
exactly (17, -23) with value −0.843. The fix is one line, and it upgrades the
system:

```python
py, px = np.unravel_index(np.argmax(np.abs(corr)), corr.shape)   # not argmax(corr)
polarity = np.sign(corr[py, px])       # -1 => the images have inverted contrast
```

Verified: normal pair → peak +0.704 at (17, −23); inverted pair → peak **−0.704**
at (17, −23). You now detect polarity inversion *for free* and can report it.

**4. Scale is the dangerous one.** A 2% zoom produced (20.30, −20.19) instead of
(17, −23) — wrong by 3 px — while the peak ratio stayed at **7.96**, comfortably
above your "trustworthy" threshold. This is the one failure your confidence
metric does **not** catch. Volunteer it before they find it:

> *"Rotation and pure noise fail loudly — the ratio collapses to about 1. Small
> scale changes fail quietly, and that's the weakness of a peak-ratio confidence
> metric. To catch it I'd need the log-polar extension, which measures scale
> directly."*

Admitting a limitation you measured and can explain is worth more than any
feature.

---

## Part 4 — Manipulation tricks: the knobs that visibly reflect

You asked for the tricks where you change one thing and **see** the result. Each
of these is one to three lines, produces a dramatic visible change, and proves a
specific piece of theory. Build them as sliders and toggles; they turn your
measured tables into live demonstrations.

Rank them by demo value: **1, 3, 6, 2, 12** are the five that make people lean
forward.

### The catalogue

| # | Knob | Change | What you SEE | What it proves |
|---|---|---|---|---|
| 1 | **beta slider** | `beta` 1.0 → 0.0 | a razor needle melts into a broad mushy hill | whitening is what localises the peak |
| 2 | **window toggle** | `window=False` | a bright cross appears along both spectrum axes | spectral leakage from the periodic extension |
| 3 | **shift slider** | change the synthetic shift | fringes in `angle(R)` tighten; **count = the shift** (1→1, 7→7, 40→40) | a shift *is* a linear phase ramp |
| 4 | **noise slider** | add `N(0, s)` to one image | peak sinks 0.84 → 0.03, ratio 80 → 1.3, **answer stays right** | information is spread across all bins |
| 5 | **blur slider** | blur one image only | answer holds to sigma 4, peak collapses 0.84 → 0.12 | a symmetric kernel is zero-phase |
| 6 | **invert toggle** | `mov = 1 - mov` | the peak flips to a **downward** spike; `argmax` breaks | contrast inversion negates R |
| 7 | **rotation slider** | rotate the moved image | the needle dissolves into a smear between 0.5 and 5 degrees | translation-only model boundary |
| 8 | **scale slider** | zoom the moved image | wrong answer at just 2%, ratio still 8 | the quiet failure; confidence can lie |
| 9 | **occlusion slider** | black box over N% | peak shrinks smoothly, position never moves | over-determination |
| 10 | **gamma slider** | `mov ** g` | literally nothing changes | phase survives monotonic intensity maps |
| 11 | **overlap slider** | shrink the shared region | peak fades, then the answer jumps | needs sufficient common content |
| 12 | **spectral mask** | low-pass R before the inverse FFT | the needle broadens into a blob; too aggressive → wrong | **localisation lives in high frequencies** |
| 13 | **high-pass mask** | remove the low-frequency bins of R | almost no change (ratio 3.83 vs 3.93) | low frequencies contribute little to localisation |
| 14 | **stack size** | align and average N noisy frames | image visibly cleans up, +3 dB per doubling | registration as denoising |
| 15 | **block grid** | 1x1 → 4x4 → 8x8 blocks | a quiver field of arrows appears | local versus global motion |
| 16 | **the second peak** | mask the main peak, `argmax` again | a second needle appears at the object's motion | linearity: one peak per motion |

### The five worth wiring up first

**Knob 1 — the beta slider.** The single best demonstration in the project.
Put the surface in 3D and drag beta from 1.0 to 0.0 while narrating: *"at 1.0
every frequency contributes equally, so we're correlating against a flat spectrum
and the autocorrelation of flat is an impulse. As beta drops, the strong low
frequencies start to dominate and the impulse spreads into the hill you'd get
from ordinary cross-correlation."* Also show your measured optimum at **0.8, not
1.0**, on a noisy pair.

**Knob 3 — the fringe counter.** Show `angle(R)` next to a shift slider. At
shift 1 there is one fringe; at 7, seven; at 40, forty. Verified exactly. Then:
*"the answer is visible before we compute anything — the inverse FFT just reads
the slope off for us."*

**Knob 6 — the invert toggle.** Break your own system on purpose, then fix it
live with `np.argmax(np.abs(corr))` and show the peak sign becoming a
polarity detector. Deliberately breaking and repairing something is memorable,
and it demonstrates you understand the sign of R, not just its magnitude.

**Knob 12 — the spectral mask.** Slide a low-pass cutoff on R and watch the
needle broaden into a blob. Our measurement: at cutoff 0.25 cycles/px the answer
is still (17, −23); at 0.10 it breaks to (8, −14). *"High frequencies are what
localise the peak — same reason a wideband radar pulse gives better range
resolution than a narrowband one."*

**Knob 14 — stack averaging.** Visually the most satisfying: a grainy image
becomes clean. Numbers already measured, exactly `10*log10(N)` every time.

### Two-line implementations for the awkward ones

```python
# rotation, for knob 7 (scipy is fine here -- it is test-data generation, not the method)
from scipy.ndimage import rotate
mov_r = rotate(mov, angle_deg, reshape=False, order=1)

# spectral mask, knob 12
ky = np.fft.fftfreq(H).reshape(-1,1); kx = np.fft.fftfreq(W).reshape(1,-1)
R = R * (np.hypot(ky, kx) <= cutoff)

# the second peak, knob 16
c = np.fft.fftshift(corr).copy()
cy, cx = H//2, W//2
c[cy-8:cy+9, cx-8:cx+9] = -np.inf
py, px = np.unravel_index(np.argmax(c), c.shape)
second = (py - cy, px - cx)
```

### One rule for all of them

**Always show the confidence number alongside.** A knob that changes the picture
is a demo; a knob that changes the picture *and* moves a number you predicted in
advance is evidence.

---

## Part 5 — Rehearsal drills

Set a timer. Do these with the app running, on a laptop, with someone watching —
the pressure is the point. Target: **under 5 minutes each, narrating throughout.**

**Week before, once each:**

1. Add a "Blackman" option to the window selector, run the test suite, report.
2. Report the shift as magnitude and angle instead of dy/dx.
3. Add a noise slider and show the peak collapsing while the answer holds.
4. Add the second-peak readout to the result block.
5. Given an unknown image pair, decide out loud whether to trust the result and
   justify it from the confidence numbers.
6. Break the sign convention on purpose, watch the test fail, fix it.
7. Implement the centroid sub-pixel method and compare it against parabolic.
8. Align three images to a common reference and show all three overlaid.

**Night before, all of them, fast:**

- Type the 1D six-line demo from memory. It is your safety net if anything
  else breaks.
- Recite the four memorised rows of [Part 3](#part-3--the-what-if-table-verified-answers):
  noise/occlusion survive, blur keeps the answer but kills the peak, inversion
  flips the sign, scale fails quietly.
- Say the [Part 0](#part-0--the-first-60-seconds) four steps out loud.

**Division of labour, if you are a team.** Agree in advance: one person drives
the keyboard, one narrates the theory, one runs the tests and reads out numbers.
Swap for each task so nobody looks like a passenger. Agree on it *before* you
walk in.

---

## Part 6 — When you get stuck

It will happen. Have a script.

**If the code will not work:**

1. **Say what you expected and what you got.** "I expected the estimate to be
   unchanged; it returned (0, 0), which usually means the two images are
   identical or the DC is dominating."
2. **Reach for the diagnostic, not the debugger.** Print the correlation surface
   stats, print the array shapes and dtypes, print the confidence numbers. Nearly
   every failure in this project is one of: wrong shape, `uint8` instead of
   float, images identical, or a forgotten unwrap.
3. **Fall back to the known-good test.** `np.roll` by (7, −11) with
   `window=False`, expect exactly (7, −11). If that passes, the core is fine and
   the bug is in your new code — say that out loud, it narrows the search in
   front of them.
4. **Time-box it at 3 minutes**, then: "I'd need a few more minutes for this;
   can I explain the approach and show you the piece that does work?" Almost
   every examiner says yes, and a clear explanation recovers most of the marks.

**If you do not know the answer to a question:**

Say so in one sentence, then say what you *do* know and how you would find out.
"I haven't measured that — but based on the blur result, where phase survived and
only the magnitude died, I'd expect the answer to hold and the peak to drop.
We could test it right now with the noise slider." Reasoning from a measurement
you *did* take is a strong answer. Bluffing is the only losing move.

**If they say your project is limited:**

Agree, immediately and specifically. "Yes — translation only. Measured, it
tolerates about 0.5 degrees of rotation and fails by 5, and small scale changes
fail quietly with a misleadingly high confidence. Log-polar would fix both, and
it reuses this same function three times." An examiner who hears a precise,
measured limitation stops probing for weaknesses, because you have just
demonstrated you already found them.

---

## The one-page card

Print this. It is everything above, compressed.

```
FIRST 60s   repeat it back -> classify + name the file -> state the plan
            -> predict the outcome -> then type

FILES       core/phase_correlation.py   the maths (don't touch for display work)
            core/transform.py           fourier_shift, valid_mask
            core/metrics.py             peak_metrics, psnr, ncc
            ui/panels.py                figures
            apps/ui.py                  config block, sidebar, screens list

SAFETY NET  np.roll(img,(7,-11)) with window=False must give exactly (7,-11)

CONFIDENCE  ratio >= 2.0 locked | 1.2-2.0 marginal | <= 1.2 no lock

SURVIVES    noise to sigma 0.6 | 50% occlusion | gamma | brightness | blur to s=4
BREAKS      rotation > 2 deg (loudly) | scale > 2% (QUIETLY) | shift > ~40% frame
FLIPS       contrast inversion -> negative peak -> use argmax(|corr|)

BEST DEMOS  beta 1->0 (needle to hill) | fringe count = shift | invert-and-fix
            | spectral mask | align-and-average (+3 dB per doubling)

STUCK       expected vs got -> diagnostics -> run the roll test -> time-box 3 min
```

Back to: **[README](../README.md)** ·
**[02 Core](02-CORE-IMPLEMENTATION.md)** ·
**[06 Viva](06-TROUBLESHOOTING-AND-VIVA.md)**
