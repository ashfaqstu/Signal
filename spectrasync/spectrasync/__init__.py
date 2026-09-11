"""SpectraSync -- spatial alignment of images in the frequency domain.

Core (the two functions named in the spec)
------------------------------------------
    func_translation        phase correlation      -> (dy, dx)
    func_rotation_and_scale Fourier-Mellin         -> (angle, scale)
    register_pair           both, composed         -> a full similarity fit

Applied features (one engine, three uses)
-----------------------------------------
    stack                   multi-frame stacking for noise reduction
    remove_moving_objects   moving-object removal from video
    highlight               highlight the moving object

Everything is a plain function on plain numpy arrays, re-exported flat, so any
piece can be reused on its own:

    import spectrasync as ss

    r = ss.phase_correlation(a, b)          ; r.dy, r.dx, r.stats.ratio
    q = ss.register_pair(a, b, mode="auto") ; q.angle_deg, q.scale, q.aligned
    s = ss.stack(frames, reducer="median")  ; s.output
    d = ss.highlight(frame, s.output)       ; d.overlay, d.boxes

Extension points -- every one is a `Registry`, so adding an option is one
decorated function and nothing else changes:

    ss.WINDOWS    ss.SUBPIXEL   ss.FILTERS
    ss.REDUCERS   ss.DETECTORS  ss.OVERLAYS   ss.STEPS

Conventions, fixed project-wide and covered by tests:
    mov[y, x] = ref[y - dy, x - dx]      +dy = down, +dx = right
    arrays are float64 in [0, 1], indexed [row, col] = [y, x]
    alignment order is: un-rotate/un-scale about the centre, THEN shift
"""

__version__ = "1.0.0"

from .registry import Registry
from .types import (DetectionResult, PeakStats, RegistrationResult,
                    RotationScaleResult, StackResult, TranslationResult)

from .core import *          # noqa: F401,F403
from .core import (FILTERS, PRESETS, SUBPIXEL, WINDOWS, func_rotation_and_scale,
                   func_translation)
from .features import *      # noqa: F401,F403
from .features import DETECTORS, REDUCERS, STEPS, Pipeline, PRESET_PIPELINES
from .io import *            # noqa: F401,F403
from .viz import *           # noqa: F401,F403
from .viz import OVERLAYS, PALETTE


def registries():
    """Every extension point, by name. `ss.registries()['reducer'].names()`."""
    return {"window": WINDOWS, "subpixel": SUBPIXEL, "filter": FILTERS,
            "reducer": REDUCERS, "detector": DETECTORS, "overlay": OVERLAYS,
            "step": STEPS}


def catalogue():
    """A printable list of every pluggable option. Handy in a live demo when
    you are asked "what else can it do?"."""
    lines = [f"SpectraSync {__version__}"]
    for kind, reg in registries().items():
        lines.append(f"\n{kind}s:")
        for name, doc in reg.describe():
            lines.append(f"  {name:<16} {doc}")
    return "\n".join(lines)
