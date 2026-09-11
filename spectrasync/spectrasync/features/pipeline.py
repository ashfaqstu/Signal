"""Composable pipelines -- the "reuse anything for any task" mechanism.

Every core and feature function is already a plain callable, so you can always
just call them. This adds a way to CHAIN them, keep every intermediate, and
inspect what happened -- which is what you want when handed an unfamiliar task.

    from spectrasync import Pipeline, STEPS

    p = (Pipeline("denoise")
         .then("align", mode="translation")
         .then("reduce", method="sigma_clip")
         .then("sharpen", cutoff=0.25))
    out = p.run(frames)
    out.value          # the final image
    out["align"]       # what the align step produced
    p.describe()       # a printable trace, for the report
"""

from __future__ import annotations

import time

import numpy as np

from ..registry import Registry

STEPS = Registry("pipeline step")


@STEPS.register("align", doc="Register frames onto a reference.")
def step_align(data, reference=0, mode="translation", **kw):
    from .stacking import align_frames
    aligned, results = align_frames(list(data), reference=reference, mode=mode, **kw)
    return aligned


@STEPS.register("reduce", doc="Collapse frames to one image with a temporal reducer.")
def step_reduce(data, method="median", **kw):
    from .temporal import reduce
    return reduce(list(data), method, **kw)


@STEPS.register("subtract", doc="Subtract a reference image from each frame.")
def step_subtract(data, background=None, **kw):
    if background is None:
        from .temporal import reduce
        background = reduce(list(data), "median")
    return [np.asarray(f, dtype=np.float64) - background for f in data]


@STEPS.register("filter", doc="Apply a named frequency-domain filter.")
def step_filter(data, name="lowpass", **kw):
    from ..core.filters import FILTERS, apply_filter
    one = np.ndim(data) == 2
    frames = [data] if one else list(data)
    mask = FILTERS[name](frames[0].shape, **kw)
    out = [apply_filter(f, mask) for f in frames]
    return out[0] if one else out


@STEPS.register("sharpen", doc="Unsharp mask, done as a frequency-domain filter.")
def step_sharpen(data, cutoff=0.25, amount=0.6, **kw):
    from ..core.filters import lowpass, apply_filter
    a = np.asarray(data, dtype=np.float64)
    return a + amount * (a - apply_filter(a, lowpass(a.shape, cutoff)))


@STEPS.register("detect", doc="Change score + mask + outline against a background.")
def step_detect(data, background=None, **kw):
    from .highlight import highlight
    from .temporal import reduce
    frames = list(data) if np.ndim(data) != 2 else [data]
    bg = background if background is not None else reduce(frames, "median")
    out = [highlight(f, bg, **kw) for f in frames]
    return out[0] if len(out) == 1 else out


@STEPS.register("normalise", doc="Rescale to [0, 1] for display.")
def step_normalise(data, **kw):
    from ..core.preprocess import to_unit
    return to_unit(data) if np.ndim(data) == 2 else [to_unit(f) for f in data]


class PipelineResult:
    """The final value plus every intermediate, keyed by step name."""

    def __init__(self, value, trace):
        self.value = value
        self.trace = trace          # [(name, kwargs, output, seconds), ...]

    def __getitem__(self, name):
        for n, _, out, _ in self.trace:
            if n == name:
                return out
        raise KeyError(f"no step named {name!r}; ran {[t[0] for t in self.trace]}")

    def steps(self):
        return [t[0] for t in self.trace]

    def timings(self):
        return {n: round(s, 4) for n, _, _, s in self.trace}


class Pipeline:
    """An ordered list of named steps. Immutable-ish: `.then` returns self so it
    chains, but you can also build one from a list of (name, kwargs) tuples."""

    def __init__(self, name="pipeline", steps=None):
        self.name = name
        self._steps = list(steps or [])

    def then(self, step, **kwargs):
        if step not in STEPS and not callable(step):
            raise KeyError(f"unknown step {step!r}; available: {STEPS.names()}")
        self._steps.append((step, kwargs))
        return self

    def run(self, data, verbose=False):
        trace = []
        value = data
        for step, kwargs in self._steps:
            fn = step if callable(step) else STEPS[step]
            label = getattr(fn, "__name__", str(step)) if callable(step) else step
            t0 = time.perf_counter()
            value = fn(value, **kwargs)
            dt = time.perf_counter() - t0
            trace.append((label, kwargs, value, dt))
            if verbose:
                print(f"  {label:<12} {dt*1000:7.1f} ms")
        return PipelineResult(value, trace)

    def describe(self):
        lines = [f"Pipeline({self.name!r})"]
        for i, (step, kwargs) in enumerate(self._steps, 1):
            label = step if isinstance(step, str) else getattr(step, "__name__", "custom")
            args = ", ".join(f"{k}={v!r}" for k, v in kwargs.items())
            doc = STEPS.doc(label) if label in STEPS else ""
            lines.append(f"  {i}. {label}({args})" + (f"   # {doc}" if doc else ""))
        return "\n".join(lines)

    __str__ = describe


#: Ready-made pipelines for the three applied features. Copy one and edit it --
#: that is the fastest way to answer "now make it do X instead".
PRESET_PIPELINES = {
    "denoise":   Pipeline("denoise").then("align").then("reduce", method="sigma_clip"),
    "removal":   Pipeline("removal").then("align").then("reduce", method="median"),
    "highlight": Pipeline("highlight").then("align").then("detect"),
}
