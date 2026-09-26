# SpectraSync — Q&A / viva preparation set

This folder is written for **you**, the presenter, not for the codebase. It exists
so that whatever a judge points at on screen, you have a rehearsed three-level
answer ready: what it does, how the UI options change it, and the exact maths
under the hood.

Read [08-viva-cheat-sheet.md](08-viva-cheat-sheet.md) the night before / morning
of. Use the rest as reference when you want to go deeper on one topic.

## How each feature file is organised

Every `0N-*.md` file for a feature follows the same three-pass structure,
because that is how a judge's question usually escalates:

1. **L1 — High-level algorithm.** What is this, in one paragraph? Which
   transform, which theorem, is it convolution or multiplication, what is the
   algorithmic complexity, why the frequency domain at all.
2. **L2 — The pipeline and the UI options.** A step-by-step walk through the
   actual code path, and then, option by option, every control in the
   sidebar: what it changes mathematically, what happens at each extreme, and
   why the default is the default.
3. **L3 — The mathematics.** Full derivation from first principles: the
   continuous theorem, the discrete version, the exact formula implemented,
   and the edge cases / assumptions it depends on.

Each file ends with a short **"judges will probably ask"** list with crisp,
one-breath answers.

## The files

| file | covers |
|---|---|
| [01-translation.md](01-translation.md) | Phase correlation — `func_translation`, Page 1 |
| [02-rotation-scale.md](02-rotation-scale.md) | Fourier-Mellin — `func_rotation_and_scale`, Page 2 |
| [03-stacking.md](03-stacking.md) | Applied feature 1 — multi-frame noise reduction, Page 3 |
| [04-object-removal.md](04-object-removal.md) | Applied feature 2 — moving-object removal, Page 4 |
| [05-highlight.md](05-highlight.md) | Applied feature 3 — change detection & outlining, Page 5 |
| [06-confidence-and-metrics.md](06-confidence-and-metrics.md) | Shared: PSR/peak-ratio confidence, PSNR, NCC, noise estimation, the valid-region masks |
| [07-architecture-and-engineering.md](07-architecture-and-engineering.md) | Why the code is shaped this way: `core`/`features`/`io`/`viz`/`app`, the `Registry` plugin mechanism, Streamlit app vs. FastAPI+React web app, testing |
| [08-viva-cheat-sheet.md](08-viva-cheat-sheet.md) | The fast-recall summary: one formula card, one paragraph per feature, the sharpest likely questions |

## The one idea that ties everything together

Every feature in this project is **one trick, applied three ways**, plus **one
engine, applied three ways**:

- **The trick** (Pages 1–2): a geometric transform of an image — translation,
  or rotation+scale — becomes, in the frequency domain, either a *linear phase
  ramp* (translation) or a *coordinate shift* after a log-polar remap
  (rotation/scale). Either way it collapses to "find where a signal peaks",
  solved once by `phase_correlation` and reused three times (translation
  directly; rotation via a `theta`-shift; scale via a `log rho`-shift).
- **The engine** (Pages 3–5): `align (register onto a reference) → reduce
  (collapse the time axis at every pixel with a chosen statistic)`. Stacking,
  object removal and highlighting are the *same two-line function*,
  `spectrasync/features/stacking.py::stack`, called with a different reducer
  and a different question asked of the result:
  - Stacking asks "what is the best estimate of the true pixel value?" → `mean`.
  - Object removal asks "what is the persistent value, ignoring transients?" → `median` / `shorth`.
  - Highlighting re-uses object removal's answer as ground truth, then asks
    "where does each frame disagree with that answer?" → band-pass filter +
    threshold + Fourier-domain gradient for the outline.

If you say only one sentence to a judge, say that one.
