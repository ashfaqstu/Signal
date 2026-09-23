# SpectraSync -- how the code is laid out

This is a map of the project, not a tutorial on the signal processing (that
lives in the docstrings, and in `../legacy/docs` for the full derivations).
Read this once and every file's *purpose* should be predictable from where it
sits.

## The one rule

    app/           <- Streamlit only. Renders things. Owns no maths.
    spectrasync/   <- Plain numpy (+ matplotlib for viz/). Owns no Streamlit.

**`spectrasync/` never imports `streamlit`.** That is not a style preference,
it is what makes every algorithm testable without a browser, reusable from
`tools/*.py`, and reusable from a future frontend that isn't Streamlit.
`tests/test_features.py`, `test_translation.py` and `test_rotation_scale.py`
exercise `spectrasync/` directly and never launch the app.

Concretely: if a page file (`app/pages/pN_*.py`) is about to compute
something with `np.` beyond reshaping a mask for `st.image`, that computation
almost certainly belongs in `spectrasync/` instead, as a small named,
documented function the page then just calls. `app/components.py` says this
at the top of the file too -- it is the one place UI glue is allowed to touch
`spectrasync`'s loaders directly, and even there it only gathers input and
hands it off.

## Inside `spectrasync/`

```
spectrasync/
  types.py          Every result is a dataclass here (PeakStats, StackResult, ...).
  registry.py        Registry -- the plugin mechanism used everywhere below.
  core/              Pure numpy. No file I/O, no matplotlib, no UI.
  features/          The three applied features, built ONLY from core/.
  io/                Image/video/file access. The only place Pillow/imageio/PIL appear.
  viz/               Matplotlib figures + overlay images. No Streamlit.
```

Dependency direction is one-way: `features` and `io` and `viz` may depend on
`core`; `core` depends on nothing else in the package. (`features/highlight.py`
also reaches into `viz.overlays.tint` for its overlay image, and
`features/stacking.py` reaches into `io.images.resize_to` for one helper --
both are deliberate, narrow exceptions, not a general licence to blur the
boundary.)

### `core/` -- the two functions named in the spec, and what they're built from

| file | what it owns |
|---|---|
| `correlation.py` | `phase_correlation` -- `func_translation` |
| `mellin.py`, `logpolar.py` | `estimate_rotation_scale` -- `func_rotation_and_scale` |
| `register.py` | the facade that composes both, resolves the 180 deg ambiguity, and reports the result in English (`describe_similarity`) |
| `transform.py` | shifting, warping, resampling, and every "which pixels are real" mask (`valid_mask`, `alignment_valid_mask`, `valid_box`, `border_mask`, `mask_from_box`) |
| `filters.py` | every frequency-domain filter, as a transfer function you multiply by |
| `metrics.py` | `psnr`, `ncc`, `estimate_noise`, and the small comparison helpers (`angle_error_deg`, `percent_error`) used to score an estimate against ground truth |
| `preprocess.py`, `windows.py`, `subpixel.py` | building blocks the above are made of |

### `features/` -- one engine, three applied uses

`align + reduce` (`features/stacking.py::stack`) is the whole engine.
`remove_moving_objects` and `highlight` are it, called with a different
reducer and a different question asked of the output. `features/temporal.py`
holds every reducer (`mean`, `median`, `shorth`, `sigma_clip`, ...) as a
`Registry`, which is why a new reducer needs no changes anywhere else.

### `io/` and `viz/`

`io/` decodes bytes into `float64` arrays in `[0, 1]` and back; `viz/` turns
arrays into matplotlib `Figure`s and RGB overlay arrays. Neither one performs
an *estimate* -- resizing, cropping, colour-space conversion and drawing are
not signal analysis, but they are also not `app/`'s job, because a script in
`tools/` needs them with no Streamlit running.

## Inside `app/`

```
app/
  main.py           Page routing + the sidebar shell. No maths.
  theme.py          CSS + matplotlib style, from ONE shared palette.
  registry.py        @page(...) -- drop a file in pages/, it appears in the sidebar.
  components.py      Streamlit widgets that call spectrasync and render the result.
  pages/pN_*.py       One screen each: gather input -> call spectrasync -> C.image(...).
```

A page function reads roughly: build inputs from the sidebar, call one or two
`spectrasync` functions, then a sequence of `C.result_line` / `C.image` /
`C.figure` calls to lay the answer out. If a page starts accumulating `if`
branches around array indices instead, that logic has drifted out of
`spectrasync` and should move back.

## Extension points

Every family of interchangeable algorithms is a `Registry`
(`spectrasync/registry.py`): `WINDOWS`, `SUBPIXEL`, `FILTERS`, `REDUCERS`,
`DETECTORS`, `OVERLAYS`, `STEPS`, plus `app.registry`'s page list. Adding an
option is one `@REGISTRY.register("name", doc="...")` decorated function --
nothing else changes, and it appears in the matching UI dropdown automatically
(`app/components.py::registry_select`, tested by
`tests/test_app.py::test_registry_drives_the_dropdowns`).

## Where to add the next thing

| I want to... | ...touch |
|---|---|
| add a reducer / window / detector / overlay | one `@REGISTRY.register` function in the matching `core/` or `features/` file |
| change what a page shows | the page file only, via calls into existing `spectrasync` functions |
| add a new computed quantity a page needs | a small documented function in `core/` (a metric or transform) or `features/` (something built from align+reduce) -- then one call from the page |
| add a new page | one file in `app/pages/` with an `@page(...)`-decorated `render()` |
| add a new frame source (folder, video, camera, ...) | one class in `spectrasync/io/sources.py` implementing `FrameSource` |

## Tests

`tests/test_translation.py`, `test_rotation_scale.py`, `test_features.py` and
`test_helpers.py` exercise `spectrasync/` directly -- no browser, no
Streamlit. `tests/test_app.py` is the smoke layer: it runs the real app
through `streamlit.testing.v1.AppTest` for every page and every input source,
so a refactor inside `spectrasync/` that breaks a screen is caught even
though the test never looks at pixels.
