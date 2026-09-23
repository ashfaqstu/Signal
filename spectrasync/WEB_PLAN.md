# SpectraSync Studio — web frontend implementation plan

> **Revision (2026-09-24): the frontend now uses a Canva-style design.** The
> backend sections (§0 rules, §1 `server/`, §3 API and services) still apply.
> The Photoshop/Premiere UX in §2 and §4–§5 has been **replaced**; the
> previous UI is kept in `web/legacy-ui/` for reference only. The new layout:
>
> | Where | What |
> |---|---|
> | `web/src/tools/catalog.ts` | **Every tool as data**: inputs, 2–3 main controls, "More options", views, headline numbers, request body. Add a tool = one entry. |
> | `web/src/pages/` | Dashboard (hero + search, tool tiles, stats, sample quick-starts, recent runs), Media library, History |
> | `web/src/editor/` | Editor: gradient top bar, icon rail + slide-out panels (Adjust / Media / Insights), canvas with a before/after slider, zoom, filmstrip playback, pixel probe |
> | `web/src/ui/` | Buttons, sliders (commit on release), chips, switch, select, menu |
> | `web/src/styles/tokens.css` | All colours, radii, shadows and timings, in light and dark themes |
> | `web/src/lib/useToolRun.ts` | Auto-run: debounced, cancels stale requests, and records history with a thumbnail |
>
> Rules 2, 3, 6 and 7 of §0 still hold: no maths in `web/`, colours only in
> tokens, and registry options appear automatically.

A second frontend for SpectraSync: a **FastAPI** backend plus a **React + Vite +
TypeScript** single-page app. Its look and interaction model come from **Adobe
Photoshop and Premiere Pro**. The Streamlit app stays exactly as it is, and both
frontends run against the same `spectrasync/` package.

This document is written for the implementer. Follow the phases in order, and
don't start a phase until the previous one meets its **Done when** checks.

---

## 0. Ground rules (read first, never break)

1. **Do not edit `spectrasync/`, `app/`, `tests/` (existing files), `tools/`,
   `run.py`, `requirements.txt` or `.streamlit/`.** Everything new goes in
   `server/`, `web/`, `tests/test_server.py` and `run_web.py`.
2. **`server/` owns no maths.** It is the web equivalent of `app/`: gather
   input → call `spectrasync` → encode the result. Allowed numpy in `server/`:
   slicing to a crop box, multiplying by a mask, `np.clip`, dtype conversion,
   and colour-mapping for PNG encoding. Anything else (a metric, a filter, a
   transform) means you are missing a `spectrasync` function. Look again in
   `spectrasync/__init__.py`. Every Streamlit page only calls `ss.*`, and
   every computation you need already exists there.
3. **`web/` owns no maths either.** It never computes an estimate. Pure
   *display* operations are allowed in the browser: zoom, pan, the A/B split
   slider, layer opacity, and reading a pixel value from a rendered PNG.
4. **Services are framework-free.** `server/services/*.py` must not import
   FastAPI, so they can be tested and reused from scripts, like `spectrasync/`.
5. **No explanatory prose anywhere in the UI.** The UI is a tool, not a
   lesson. Use labels, symbols, units and numbers only. No notes, captions
   that explain, "why" text, paragraphs, or registry doc strings on screen.
   See §5 Copy.
6. **No hard-coded colours, sizes or fonts outside `web/src/styles/tokens.css`.**
   Components use `var(--token)` only.
7. Adding an option to a `spectrasync` Registry must make it appear in the web
   dropdowns with **zero** web changes, as it already does in Streamlit (see §3.4
   `/api/registries`).

---

## 1. Target folder layout

```
signal/spectrasync/
  spectrasync/          (unchanged)  maths
  app/                  (unchanged)  Streamlit frontend
  server/               NEW          FastAPI backend, no maths
    __init__.py
    main.py             app factory, CORS (dev), mounts web/dist in prod
    config.py           paths, limits, sample folders, ports
    media.py            MediaStore: uploads + samples on disk, decode cache
    layers.py           LayerStore + RunStore: arrays kept in memory, LRU
    encode.py           ndarray -> PNG / JPEG / colormapped heatmap bytes
    schemas.py          pydantic models: every request and response
    services/           one module per workspace, pure python
      __init__.py
      common.py         load_pair(), load_sequence(), synthetic helpers
      align.py          (Streamlit p1_translation)
      rotate.py         (p2_rotation_scale)
      stack.py          (p3_stacking)
      remove.py         (p4_removal)
      highlight.py      (p5_highlight)
      spectrum.py       (p6_theory)
    routes/
      __init__.py
      media.py          /api/media ...
      registries.py     /api/registries
      runs.py           /api/run/{workspace}, /api/runs/{id}/...
      layers.py         /api/layers/{id}.png
    requirements.txt    -r ../requirements.txt + fastapi etc.
  web/                  NEW          React SPA
    (see §4.1)
  tests/test_server.py  NEW
  run_web.py            NEW          python run_web.py [--dev]
  WEB_PLAN.md           this file
```

Streamlit page → web workspace mapping (keep this table in mind throughout):

| Streamlit page | Workspace id | Tab label | Shortcut |
|---|---|---|---|
| 1. Translation | `align` | Align | Alt+1 |
| 2. Rotation & Scale | `rotate` | Rotate · Scale | Alt+2 |
| 3. Stacking | `stack` | Stack | Alt+3 |
| 4. Object Removal | `remove` | Remove | Alt+4 |
| 5. Highlight | `highlight` | Highlight | Alt+5 |
| 6. How it works | `spectrum` | Spectrum | Alt+6 |

---

## 2. The UX: what "Photoshop × Premiere" means here

### 2.1 Window layout (fixed dock, resizable, collapsible)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ ◆  File  View  Window  Help      Align  Rotate·Scale  Stack  Remove  Highlight  Spectrum      ◐ │  AppBar 32px
├──┬──────────────────────────────────────────────────────────┬──────────────────┤
│▣ │ reference ×  moved ×  aligned ×  overlay ×   [1-up|2-up|4-up|Split] │ PROPERTIES     ▾ │
│✥ │┌────────────────────────────────────────────────────────┐│  Source          │
│⌕ ││                                                        ││  Method          │
│⊕ ││                  VIEWER (pasteboard)                   ││  Display         │
│◧ ││                                                        ││  [✓ Preview] Run │
│  │└────────────────────────────────────────────────────────┘├──────────────────┤
│  ├──────────────────────────────────────────────────────────┤ INFO           ▾ │
│  │ ◀◀ ◀ ▶ ▶▶  00:07 / 00:24   ────●────────────────   A▾ B▾ │ dy    +12.503 px │
│  │ ▢▢▢▢▢▢▢▢▢▢▢▢▢▢▢▢▢▢▢▢▢▢▢▢▢▢▢▢▢▢▢▢▢▢▢▢   (filmstrip)      │ dx    −07.498 px │
│  │ ▁▁▁▂▂▇▇▂▁▁  (per-frame confidence track)                 │ ● LOCK   ratio 4.1│
├──┴──────────────────────────────────────────────────────────┼──────────────────┤
│ 100%   512 × 512   x 231  y 118   0.412   │ Done · 0.84 s  │ LAYERS / MEDIA  ▾ │
└──────────────────────────────────────────────────────────────┴──────────────────┘
   ToolBar 40px                                                   Right dock 300px
                     StatusBar 24px
```

Regions and their Adobe counterpart:

| Region | Adobe counterpart | Content |
|---|---|---|
| **AppBar** | Menu bar + Premiere workspace switcher | App mark, 4 menus, the 6 workspace tabs centred, theme toggle |
| **ToolBar** (left, vertical) | Photoshop Tools panel | Move/Hand, Zoom, Probe (eyedropper), Compare split, Marquee-free. One active tool at a time |
| **Document tabs** (top of viewer) | Photoshop document tabs | One tab per output *layer* of the current run; plus a layout switch 1-up / 2-up / 4-up / Split |
| **Viewer** | Canvas on pasteboard | Pan and zoom synced across panes, vector overlays (peak crosshair, boxes) |
| **Timeline** (bottom, only for sequence workspaces) | Premiere timeline + Program monitor transport | Filmstrip of frames, playhead, transport, per-frame confidence track, A/B markers |
| **Properties** (right dock) | Photoshop Properties / Premiere Effect Controls | Workspace parameters in collapsible groups; Preview checkbox + Run button |
| **Info** (right dock) | Photoshop Info panel | Numeric readouts only, tabular monospace |
| **Layers / Media / Graph** (right dock, tabbed) | Layers panel, Premiere Project bin, Lumetri scopes | Output layers (visibility, opacity), media bin (uploads + samples), charts |
| **StatusBar** | Photoshop status bar | Zoom %, image size, cursor x/y, pixel value, run state + time |

Workspaces **without a sequence** (Align, Rotate·Scale, Spectrum) hide the
Timeline, and the viewer takes that height.

### 2.2 Interaction rules

- **Preview is live.** With `Preview` ticked (the default), any parameter change
  re-runs after a 250 ms debounce, and an in-flight request is aborted. Unticked,
  nothing runs until you press **Run** (⌘/Ctrl+Enter). Heavy workspaces (Stack,
  Remove, Highlight) default to Preview **off**.
- **Scrub fields** (Adobe "scrubby sliders"): every numeric parameter is a
  label + number field. Drag horizontally on the *label* to change the value,
  Shift = ×10 step, Alt = ×0.1 step. Click the number to type. ↑/↓ nudge.
  Double-click the label to reset to the default.
- **Viewer:** wheel = zoom about the cursor, Space+drag = pan (from any tool),
  H = hand, Z = zoom tool (click in, Alt-click out), I = probe, C = compare
  split, Ctrl+0 = fit, Ctrl+1 = 100 %, Ctrl+= / Ctrl+- = zoom steps.
  All panes in 2-up/4-up **share one viewport** (zoom/pan in sync), so
  before/after compare at the same spot. This replaces Streamlit's
  `C.zoom` crops. Don't port `zoom()`.
- **Compare split (C):** in Split layout, a vertical divider shows layer L on the
  left and layer R on the right. Drag the divider, and pick L/R from two selects
  in the viewer header.
- **Probe (I):** hovering shows the pixel value in the status bar. Clicking in
  **Remove** fetches the time series of that pixel into the Graph panel. In
  other workspaces, clicking pins the value in Info.
- **Timeline:** J/K/L = back / pause / forward play, ←/→ = step one frame,
  Home/End. The **A** and **B** markers (Premiere in/out style) pick two frames
  of a sequence as the reference and moving image for Align / Rotate·Scale. The
  timeline shows in those workspaces only when their source is a video.
- **Drop anywhere:** dropping files on the window imports them into Media and
  assigns them to the current workspace's empty input slot(s).
- **Tab** hides/shows all panels (Photoshop behaviour).
- Layout sizes and the open/closed state of each panel persist in
  `localStorage` (wrapped in try/catch).

### 2.3 Visual language (anti-slop rules)

- Flat surfaces with 1 px hairline dividers. **No** gradients, glassmorphism,
  glows, emoji, or big rounded cards. Radius: 2 px on controls, 4 px on popovers,
  0 on panels.
- Shadows only on floating things (menus, popovers, tooltips).
- Dense desktop scale: base text 12 px, controls 24 px tall, panel headers
  28 px, 8 px grid (4 px half-steps).
- One accent colour (blue), used only for focus, the selection, the active tool,
  the primary button and the playhead. Status colours (green/amber/red) are used
  only for verdicts and per-frame confidence.
- Numbers in `font-variant-numeric: tabular-nums`, sign always shown for
  signed quantities (`+12.503`, `−7.498` using U+2212 minus).
- Icons: `lucide-react`, 16 px, `strokeWidth={1.5}`, in `--text-2` colour, and
  in `--accent` when active.
- Images are never stretched: `image-rendering: pixelated` above 200 % zoom.
- Motion: 120 ms ease-out for hover/focus/panel collapse only. No page-level
  animation.

### 2.4 Theme tokens (`web/src/styles/tokens.css`)

Fonts are Adobe's open-source families, loaded from Google Fonts:
**Source Sans 3** (UI) and **Source Code Pro** (numbers, readouts).

```css
:root {
  --font-ui: "Source Sans 3", system-ui, sans-serif;
  --font-mono: "Source Code Pro", ui-monospace, monospace;
  --fs-xs: 11px; --fs-sm: 12px; --fs-md: 13px; --fs-lg: 15px;
  --row: 24px; --header: 28px; --appbar: 32px; --status: 24px; --toolbar: 40px;
  --r-ctl: 2px; --r-pop: 4px;
  --dur: 120ms;
}
/* LIGHT (Photoshop "lightest" UI) */
:root, :root[data-theme="light"] {
  --bg-app:     #E8E8E8;  /* chrome behind panels            */
  --bg-panel:   #F5F5F5;  /* panel surfaces                  */
  --bg-raised:  #FFFFFF;  /* fields, menus                   */
  --bg-hover:   #E1E1E1;
  --pasteboard: #D4D4D4;  /* area around the image           */
  --line:       #CACACA;  /* 1px dividers                    */
  --text-1:     #222222;  --text-2: #505050;  --text-3: #8A8A8A;
  --accent:     #1473E6;  --accent-text: #FFFFFF;
  --ok: #268E6C;  --warn: #CB6F10;  --bad: #D7373F;
  --shadow-pop: 0 4px 16px rgb(0 0 0 / .18);
}
/* DARK (Photoshop "darkest" UI) */
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg-app: #1B1B1B; --bg-panel: #262626; --bg-raised: #323232;
    --bg-hover: #3A3A3A; --pasteboard: #141414; --line: #3E3E3E;
    --text-1: #E6E6E6; --text-2: #B3B3B3; --text-3: #7A7A7A;
    --accent: #378EF0; --accent-text: #FFFFFF;
    --ok: #2D9D78; --warn: #E68619; --bad: #E34850;
    --shadow-pop: 0 4px 16px rgb(0 0 0 / .5);
  }
}
:root[data-theme="dark"] { /* same values as the dark block above */ }
body { background: var(--bg-app); color: var(--text-1);
       font: var(--fs-sm)/1.4 var(--font-ui); }
```

The theme toggle cycles **System → Light → Dark** by setting
`document.documentElement.dataset.theme` (removing it means System). The choice
is stored in `localStorage`.

Heatmaps (spectra, correlation, change score) use **one** fixed colormap in
both themes, `inferno`, rendered server-side (§3.3). Grayscale images stay
grayscale.

---

## 3. Backend (`server/`)

### 3.1 Dependencies — `server/requirements.txt`

```
-r ../requirements.txt
fastapi>=0.110
uvicorn[standard]>=0.29
python-multipart>=0.0.9
imageio>=2.31
imageio-ffmpeg>=0.4
httpx>=0.27          # for fastapi.testclient in tests
```

### 3.2 `config.py`

- `ROOT` = the `signal/spectrasync` folder (parent of `server/`). `os.chdir` is
  **not** used, so build every path from `ROOT`.
- `UPLOAD_DIR` = `tempfile.gettempdir()/spectrasync_studio/uploads`, created on
  startup.
- `SAMPLES`: a list of `(group_label, glob, kind)` that registers the same sample
  files the Streamlit pages fall back to:

  | label | glob |
  |---|---|
  | `Base` | `data/raw/photo_b.jpg` |
  | `Pair · rotated` | `new_image/3/*.jpg` |
  | `Burst · noisy` | `new_image/2_noisy/set_1/*.jpg` |
  | `Burst · clean ref` | `new_image/2_noisy/_clean/set_1.png` |
  | `Crowd` | `new_image/1/*.jpg` |

- Limits: `MAX_UPLOAD_MB = 200`, `MAX_RUNS_KEPT = 8`, allowed image extensions =
  Streamlit's `IMAGE_TYPES`, allowed video extensions = `mp4 avi mov mkv webm`.
- `HOST = "127.0.0.1"`, `PORT = 8000`. Bind to localhost only.

### 3.3 `encode.py`

- `to_png(arr) -> bytes`: use `ss.png_bytes` for images. For 2-D float arrays
  that are not in [0, 1], first apply `ss.to_unit`, the same rule as
  `app/components.py::image`.
- `heatmap_png(arr, cmap="inferno") -> bytes`: `ss.to_unit` →
  `matplotlib.colormaps[cmap]` → uint8 RGB → `ss.png_bytes`.
- `thumb_jpeg(arr, max_side=160) -> bytes`: for the filmstrip and the media bin.

A layer's `kind` picks the encoder: `image` / `mask` → `to_png`, `heatmap` →
`heatmap_png`.

### 3.4 Stores

`media.py` — `MediaStore` (a module-level singleton; this is a single-user
local tool):

```python
@dataclass
class Media:
    id: str; name: str; kind: Literal["image", "video"]
    path: Path; group: str; sample: bool
    width: int; height: int; n_frames: int | None
```
- `import_upload(UploadFile) -> Media`: save to `UPLOAD_DIR/<uuid><ext>`, then
  read the size (Pillow for images, first frame via `ss.read_video(max_frames=1)`
  for videos).
- `register_samples()`: called at startup. Globs `config.SAMPLES` and registers
  each file with `sample=True`, so the ids are stable per run.
- `load(ids, max_side, gray) -> list[ndarray]`: calls `ss.load_many([paths],
  max_side=, gray=)`, cached with `functools.lru_cache(maxsize=16)` keyed on
  `(tuple(ids), max_side, gray)`. This mirrors `components._decode_many`.
- `load_video(id, max_frames, step, max_side, gray)`: `ss.read_video(...)`,
  also LRU-cached. A `RuntimeError` (no decoder) becomes HTTP 422 with
  `{"code":"no_video_backend"}`.

`layers.py`:
- `LayerStore.put(arr, kind, name) -> Layer` gives a uuid, keeps the ndarray,
  and encodes lazily on the first GET, then caches the bytes.
- `RunStore.put(run_id, payload)` keeps the service's full result object (for
  the pixel probe and exports). It's an `OrderedDict` LRU capped at
  `MAX_RUNS_KEPT`, and evicting a run also drops its layers.

### 3.5 API

All JSON is camelCase on the wire (pydantic `alias_generator=to_camel`,
`populate_by_name=True`).

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | `{ok, version: ss.__version__, video: bool}` (whether a video backend exists) |
| GET | `/api/registries` | `{window:[{name}], subpixel:[...], reducer:[...], detector:[...], overlay:[...]}` from `ss.registries()`, names in registration order. Docs are **not** sent (no prose in UI). |
| GET | `/api/media` | all media (samples + uploads), grouped |
| POST | `/api/media` | multipart `files[]` → `Media[]` |
| DELETE | `/api/media/{id}` | uploads only |
| GET | `/api/media/{id}/thumb.jpg` | bin thumbnail |
| GET | `/api/media/{id}/frames?maxFrames&step` | video → `[{index, thumbUrl}]` for the filmstrip before a run |
| POST | `/api/run/{workspace}` | body = that workspace's params model (§3.6) → `RunResult` |
| GET | `/api/layers/{id}.png` | encoded layer, `Cache-Control: max-age=3600, immutable` |
| GET | `/api/runs/{runId}/pixel?x&y` | Remove only: `ss.pixel_timeseries` on the stored `aligned` → `{signal[], median, freq[], spectrum[]}` |
| GET | `/api/runs/{runId}/export?layer={name}&format=png` | download one layer at full res (`Content-Disposition`) |
| GET | `/api/runs/{runId}/export-sequence?layer={name}&format=mp4\|gif&fps=12` | sequence export via `ss.write_video` / `ss.write_gif` to a temp file |

Run endpoints are plain `def` (not `async def`), so FastAPI runs them in its
threadpool and the numpy work doesn't block the event loop.

**`RunResult`** (`schemas.py`):

```python
class Readout(BaseModel):   key: str; label: str; value: float | int | str
                            unit: str = ""; fmt: str = ""   # "+.3f", ".2f", "d", "pct"
                            tone: Literal["default","ok","warn","bad","muted"] = "default"
class LayerRef(BaseModel):  id: str; name: str; group: str; kind: str
                            width: int; height: int; url: str
class Marker(BaseModel):    layer: str; type: Literal["crosshair","box"]
                            x: float; y: float; w: float = 0; h: float = 0
class FrameRef(BaseModel):  index: int; name: str; layers: dict[str, str]  # name->url
                            meta: dict[str, float | int | str | None]
class Chart(BaseModel):     id: str; kind: Literal["line","bar"]; x: list[float] | list[str]
                            series: list[dict]  # {name, values[], role:"primary"|"reference"}
class Table(BaseModel):     columns: list[str]; rows: list[list[float | str]]
class RunResult(BaseModel):
    run_id: str; workspace: str; elapsed_ms: int
    verdict: Literal["locked","marginal","no lock"] | None = None
    readouts: list[Readout]; layers: list[LayerRef]
    markers: list[Marker] = []; frames: list[FrameRef] = []
    charts: list[Chart] = []; table: Table | None = None
    flags: list[str] = []          # machine codes, e.g. "inverted_contrast"
```

`flags` are short codes, never sentences. The frontend turns them into
2–3-word badges (§5).

**Errors**: 422 `{code, detail}` where `code` ∈ `need_two_images`,
`need_two_frames`, `need_three_frames`, `no_video_backend`, `bad_media`. The
frontend maps each code to a short empty-state label (§5.3).

### 3.6 Services — one per Streamlit page, one-to-one

Each service is `run(params: <Model>, media: MediaStore) -> ServiceResult`,
where `ServiceResult` is a plain dataclass holding arrays, numbers and lists.
`routes/runs.py` turns it into `RunResult`: it puts arrays in the LayerStore and
builds the readouts. Port the **orchestration** from the Streamlit page line by
line, and drop every `st.*`, `C.*` and prose string. Crop every output layer
through the `valid_box` the page uses (its `view()` helper) before storing it.

`common.py` (shared input gathering):
- `load_pair(a_id, b_id, max_side, gray)` → `ss.match_shapes`-ready pair.
- `load_sequence(src)`, where `src` is a discriminated union:
  - `{"type":"photos","mediaIds":[...],"maxSide":int,"colour":bool}` → `media.load`
  - `{"type":"video","mediaId":str,"frames":int,"step":int}` → `media.load_video`,
    then `ss.even_square(f, 384)` per frame, as in p4
  - `{"type":"synthetic", ...}` → built per service, as each page does
- `frame_pair_from_video(media_id, a_index, b_index, max_side)` for the A/B
  timeline markers in Align / Rotate·Scale. It calls `ss.read_video` with
  `max_frames = max(a, b) + 1`.

Params and outputs per service (defaults and ranges are copied from the
Streamlit sliders, so keep them identical):

**align** (p1_translation)
- params: `source: "pair"|"synthetic"|"video"`; pair → `aId, bId`; video →
  `mediaId, aIndex, bIndex`; synthetic → `baseId` (default sample `Base`),
  `dy [-40,40] 12.5 step .5`, `dx [-40,40] -7.5 step .5`, `noise [0,.4] 0 step .01`;
  `window="hann"`, `subpixel="parabolic"`, `beta [0,1] 1.0 step .05`,
  `lowpass [0,.5] 0 step .01`, `overlay="anaglyph"`, `tile [8,128] 32`,
  `alpha [0,1] .5`.
- calls: `ss.even_square`, `ss.fourier_shift`, `ss.add_noise`, `ss.match_shapes`,
  `ss.lowpass`, `ss.phase_correlation`, `ss.apply_registration`,
  `ss.alignment_valid_mask`, `ss.OVERLAYS[name]`, `ss.difference`, `ss.psnr`,
  `ss.cross_power_spectrum`.
- layers: `A` (image), `B`, `B aligned`, `Overlay` (overlay after alignment),
  `Δ before` (`difference(ref,mov)*valid`), `Δ after`, `|F₁|` (heatmap of
  `log1p(abs(fftshift(F1)))`), `|F₂|`, `∠R` (heatmap of `angle(fftshift(R))`,
  cmap `twilight`), `r(x,y)` (heatmap of `fftshift(corr)`).
  These two log/angle/fftshift display transforms are the only exception to
  rule 2: they are pure presentation, copied from `viz/figures.py`. Put them in
  `encode.py` as `log_spectrum()` and `phase_image()`.
- markers: crosshair on `r(x,y)` at the argmax of `|fftshift(corr)|` (same as
  `figure_correlation`).
- readouts: `dy px +.3f`, `dx px +.3f`, `peak .3f`, `PSR .1f`, `ratio .2f`,
  `PSNR before dB .1f`, `PSNR after dB .1f`; synthetic adds `dy true`, `dx true`,
  `err dy`, `err dx` (`.3f`). Set `verdict = r.stats.verdict`. Add flag
  `inverted_contrast` if `r.stats.polarity < 0`.
- default view: 2-up `A | Overlay`.

**rotate** (p2_rotation_scale)
- params: `source: "pair"|"synthetic"|"video"`; pair → `aId, bId` (default the
  first two of `Pair · rotated`), `maxSide [320,1280] 704 step 32`; synthetic →
  `baseId`, `angle [-180,180] 20 step 1`, `scale [.70,2.00] 1.20 step .01`,
  `dy [-30,30] 9`, `dx [-30,30] -14`, `noise [0,.2] 0 step .01`;
  `robust=true`, `nTheta ∈ {180,360,720,1080}=720`, `nRho ∈ {128,256,512,768}=512`,
  `overlay="anaglyph"`.
- port lines 58–128 of p2 exactly (`to_even`, `to_gray`, `centre_square`,
  `register_similarity(presets=None if robust else [ss.PRESETS[0]])`, angle
  wrap, `apply_registration`, `alignment_valid_mask`, `ncc`,
  `estimate_rotation_scale` for the log-polar intermediates).
- layers: `A`, `B`, `B restored` (masked), `Overlay before`, `Overlay after`
  (masked as in p2), `log-polar A`, `log-polar B`, `ρθ correlation` (heatmap
  of `fftshift(rs.corr)`).
- readouts: `rotation ° +.2f`, `scale × .4f`, `dy px +.1f`, `dx px +.1f`,
  `peak`, `PSR`, `ratio`, `NCC before .3f`, `NCC after .3f`; synthetic adds
  `err ° .3f`, `err scale % .2f`. Verdict from `r.stats`. Drop
  `describe_similarity` (it produces prose).
- default view: Split `Overlay before | Overlay after`.

**stack** (p3_stacking)
- params: `source: "photos"|"video"|"synthetic"`; photos → `mediaIds` (default
  `Burst · noisy`), `maxSide [320,1600] 800 step 32`, `colour=true`,
  `cleanId` (optional; defaults to `Burst · clean ref` **only when** the
  default sample set is in use, as in p3 lines 77–80); synthetic → `baseId`,
  `n [2,32] 16`, `noise [0,.4] .12`, `shift [0,15] 5 step .5`;
  `reducer="mean"`, `align=true`, `compare=true`.
- port `render()` lines 72–150 and `_synthetic()` of p3.
- layers: `Raw` (frame 0), `Stacked`, `Residual` (vs clean) or `Removed`
  (raw − stacked). With `compare`, add one layer per reducer in `COMPARE`,
  named by the reducer, in group `Reducers`.
- frames: one `FrameRef` per aligned frame. `layers={"frame": url}`, `meta={dy,
  dx, confidence, locked: confidence>=1.5}`.
- table: the reducer comparison rows, the same columns as p3.
- chart: `bar`, x = reducer names, series `gain dB` (measured, if clean ref)
  and `theory dB`.
- readouts: with a clean ref: `PSNR dB`, `from dB`, `gain dB +.2f`; without:
  `σ out .3f`, `σ raw .3f`, `σ ratio ×.1f`. Always: `frames d`,
  `locked d/d` (as a string `"14/16"`), `theory dB +.2f`.
- export: `Stacked` → `stacked_{reducer}.png`.

**remove** (p4_removal)
- params: `source: "photos"|"synthetic"|"video"`; photos → `mediaIds` (default
  `Crowd`), `maxSide [320,1600] 640`, `colour=true`,
  `mode ∈ translation|auto|similarity = auto`; synthetic → `baseId`,
  `n [4,24] 12`, `radius [6,60] 26 step 2`, `noise [0,.2] .01 step .005`,
  `shake [0,12] 4 step .5`; video → `mediaId`, `frames [4,60] 24`,
  `step [1,10] 2`; `reducer="shorth"`, `compareFilters=true`.
- port p4 lines 186–300. Keep `res.aligned` in the RunStore for the pixel
  probe.
- layers: `Frame 0`, `Mid frame`, `Plate`; with `compareFilters`, one layer per
  entry of `ss.compare_temporal_filters(res.aligned)` in group `Filters`.
- frames: every aligned frame, `meta={dy, dx, confidence}` (from
  `res.shifts`, `res.stats["confidence"]`; frame 0 has `confidence: null`).
- chart (initial): the pixel from `ss.most_disturbed_pixel` →
  `line` chart `pixel` (signal, plus a reference series = its median) and a
  `line` chart `spectrum`. Report the pixel as a crosshair marker on `Plate`
  **in cropped coordinates** (subtract `x0, y0`).
- readouts: synthetic → `PSNR object dB .1f`, `from dB .1f`, `PSNR frame dB .1f`;
  photos → `frames`, `locked "n/N"`, `plate "W×H"`, `coverage %`; video →
  `frames`.
- `/pixel` endpoint: the x, y in the request are **cropped** coordinates, so
  add `x0, y0` back before calling `ss.pixel_timeseries`.
- export: `Plate` PNG.

**highlight** (p5_highlight)
- params: `source: "photos"|"synthetic"|"video"`; photos → `mediaIds` (default
  `Crowd`), `maxSide [320,1600] 640`, `colour=true`, `mode=auto`,
  `reducer="shorth"`; synthetic → `baseId`, `n [4,24] 12`, `radius [6,60] 26`,
  `noise [0,.2] .01`; video → as in remove; `detector="bandpass"`,
  `low [.005,.10] .02 step .005`, `high [.05,.45] .20 step .01` (only sent
  when detector == bandpass), `k [.5,8] 3 step .1`, `smooth [0,5] 1.5 step .1`,
  `minArea [5,500] 40 step 5`.
- port p5 lines 375–411 (video: same loading as remove).
- frames: **every** frame gets `layers={photo, overlay, mask, score, outline}`
  (score normalised per frame as in p5 lines 434–435) and `meta={objects,
  threshold, coverage}`. Boxes go in `markers` with `layer: "overlay#<i>"`,
  in cropped coordinates.
- layers (top level): `Plate`.
- readouts are **per frame**, so return them inside `frame.meta`. The Info
  panel reads the current frame's meta: `objects d`, `largest "y,x"`,
  `size "h×w"`, `threshold .4f`, `coverage % .2f`, plus a global
  `total objects d`.
- export-sequence: `overlay` → MP4 (fallback GIF), which is the "highlighted
  video" output.

**spectrum** (p6_theory)
- params: `baseId`, `dy [-30,30] 12 step .5`, `dx [-30,30] -8 step .5`.
- compute all stages at once (they're cheap at 320 px). Layers, one per
  stage, in stage order: `f₁ | f₂` (hstack), `|F₁|`, `|F₂|`, `phase swap`
  (`ss.phase_swap(ref, mov)`), `∠R`, `r(x,y)` (+ crosshair marker),
  `residual` (difference after applying the estimate), `log-polar A`,
  `log-polar B`, `ρθ correlation` (from the 20°, 1.15× warp in p6 line 553).
- readouts: `dy`, `dx`, `dy true`, `dx true`.
- The web UI shows the stage **names and formulas** (KaTeX, one line) and
  **no paragraph text**. Copy the `STAGES` formula strings into
  `web/src/workspaces/spectrum/stages.ts`. The prose column is not ported.

### 3.7 `main.py`

- `create_app()`: include routers under `/api`. On startup:
  `ss.use_paper_style()` is **not** needed (no matplotlib figures are served).
  Call `media.register_samples()`.
- Dev: CORS for `http://localhost:5173`.
- Prod: if `web/dist` exists, mount it with `StaticFiles(html=True)` at `/`,
  **after** the API routes.
- `python -m server` runs uvicorn on `config.HOST:config.PORT`
  (`server/__main__.py`).

### 3.8 `run_web.py`

- `python run_web.py`: if `web/dist` is missing, print
  `cd web && npm install && npm run build`, then start uvicorn and open the
  browser at `http://127.0.0.1:8000`.
- `python run_web.py --dev`: start uvicorn with `--reload` **and**
  `npm run dev` (in `web/`) as two subprocesses. Ctrl+C stops both.

---

## 4. Frontend (`web/`)

### 4.1 Stack and layout

- Vite + React 18 + TypeScript (strict), CSS Modules plus `tokens.css`. No
  Tailwind and no UI kit skins.
- `react-aria-components`: accessible, unstyled Select, Tabs, Menu, Tooltip,
  Checkbox, ToggleButton and Dialog. It's Adobe's own primitive library, so the
  behaviour matches the theme.
- `react-resizable-panels`: dock splits.
- `@tanstack/react-query`: the fetch cache and the abort signal on runs.
- `zustand`: client state (params per workspace, viewport, active tool,
  timeline).
- `recharts`: the Graph panel (line + bar), styled only with tokens.
- `katex`: Spectrum stage formulas.
- `lucide-react`: icons.
- Dev tooling: ESLint (typescript-eslint, react-hooks), Prettier, Vitest.
- `vite.config.ts`: proxy `/api` → `http://127.0.0.1:8000`.

```
web/src/
  main.tsx                 providers (QueryClient), theme init, <App/>
  App.tsx                  <Shell/>
  styles/  tokens.css  reset.css  base.css
  api/
    client.ts              fetch wrapper: JSON, errors -> ApiError{code}
    types.ts               TS mirror of server/schemas.py (hand-written, camelCase)
    queries.ts             useRegistries, useMedia, useImport, useRun, usePixel
  state/
    params.ts              zustand: params[workspaceId], setParam, reset
    viewport.ts            zoom, panX, panY, fit(), zoomAt(cx,cy,factor)
    ui.ts                  activeWorkspace, activeTool, layout(1up/2up/4up/split),
                           paneLayers[], splitPos, preview, theme, panelsHidden
    timeline.ts            currentFrame, playing, fps, markerA, markerB
  shell/
    Shell.tsx              the grid in §2.1
    AppBar.tsx  Menus.tsx  WorkspaceTabs.tsx  ThemeToggle.tsx
    ToolBar.tsx  StatusBar.tsx  DropOverlay.tsx  Shortcuts.ts
  viewer/
    Viewer.tsx             layout switch + DocumentTabs
    Pane.tsx               one image, transformed by the shared viewport
    SplitCompare.tsx       two images + draggable divider
    MarkerLayer.tsx        SVG crosshair/boxes in image coordinates
    useViewportGestures.ts wheel, space-drag, zoom tool, probe
    probe.ts               read pixel from an offscreen canvas of the PNG
  timeline/
    Timeline.tsx  Transport.tsx  FilmStrip.tsx  ConfidenceTrack.tsx  Playhead.tsx
  panels/
    Panel.tsx              header (title, collapse chevron, optional actions)
    PropertiesPanel.tsx    renders a workspace ParamSchema (see 4.2)
    InfoPanel.tsx          readouts + verdict chip + flag badges
    LayersPanel.tsx        run layers grouped; eye toggle; click = show in active pane
    MediaPanel.tsx         bin grid, groups, import button, drag source
    GraphPanel.tsx         charts[] + table
  controls/
    ScrubField.tsx  Select.tsx  Checkbox.tsx  Segmented.tsx  MediaSlot.tsx
    MediaMultiSlot.tsx  Button.tsx  IconButton.tsx  Badge.tsx  VerdictChip.tsx
  workspaces/
    types.ts               WorkspaceDef, ParamSchema
    index.ts               WORKSPACES = [align, rotate, stack, remove, highlight, spectrum]
    align/def.ts  rotate/def.ts  stack/def.ts  remove/def.ts  highlight/def.ts
    spectrum/def.ts  spectrum/stages.ts  spectrum/StageStrip.tsx
  lib/
    format.ts              formatReadout(value, fmt, unit) with U+2212 minus, tabular
    keys.ts                shortcut matcher
    storage.ts             safe localStorage get/set (try/catch)
```

### 4.2 Workspaces are data (the web twin of `app/registry.py`)

Adding a workspace = one `def.ts` + one line in `workspaces/index.ts`. No
component edits.

```ts
export type Param =
  | { key: string; label: string; type: "number"; min: number; max: number; step: number;
      default: number; unit?: string; when?: (p: Params) => boolean }
  | { key: string; label: string; type: "choice"; options: {value: string; label: string}[];
      default: string; when?: ... ; display?: "segmented" | "select" }
  | { key: string; label: string; type: "registry"; registry: RegistryKind; default: string; when?: ... }
  | { key: string; label: string; type: "toggle"; default: boolean; when?: ... }
  | { key: string; label: string; type: "media"; accept: "image" | "video"; default?: SampleRef; when?: ... }
  | { key: string; label: string; type: "mediaMany"; accept: "image"; min: number; default?: SampleRef; when?: ... };

export interface WorkspaceDef {
  id: "align" | "rotate" | "stack" | "remove" | "highlight" | "spectrum";
  label: string; shortcut: string; icon: LucideIcon;
  groups: { title: "Source" | "Method" | "Detection" | "Display"; params: Param[] }[];
  sequence: "always" | "whenVideo" | "never";     // shows Timeline
  previewDefault: boolean;
  defaultLayout: { layout: "1up" | "2up" | "4up" | "split"; panes: string[] };  // layer names
  frameLayer?: string;          // which FrameRef layer the viewer shows when scrubbing
  toRequest: (p: Params) => unknown;   // builds the server params body
}
```

`PropertiesPanel` walks `groups`, hides params whose `when` is false, and
renders `number` → ScrubField, `choice` → Segmented (≤3 options) or Select,
`registry` → Select filled from `useRegistries()`, `toggle` → Checkbox,
`media` → MediaSlot (thumbnail + name + clear; drop target; click opens a
Media picker popover), `mediaMany` → MediaMultiSlot (thumbnail row + count).

### 4.3 Run flow

1. `useRun(workspaceId)` watches `params[workspaceId]`.
2. If `preview` is on, a change debounces 250 ms, aborts the previous request,
   and POSTs `toRequest(params)`.
3. While running, the StatusBar shows `Running…` with a 2 px indeterminate
   bar under the AppBar. The **previous result stays visible** (no blank
   flash).
4. On success, the result is stored per workspace (switching tabs keeps each
   workspace's last result). If the pane's layer names still exist, the panes
   keep them; otherwise they fall back to `defaultLayout`.
5. On `ApiError`, the viewer shows the empty-state label for `code` (§5.3), and
   the Info panel keeps the last numbers dimmed (`--text-3`).

Image loading: `<img decoding="async">` per pane. For sequences, preload
`frames[i ± 3]` of the current `frameLayer` while playing.

### 4.4 Viewer maths (display only)

- Viewport state: `{ zoom, cx, cy }`, the image-space point shown at the pane
  centre. The pane transform is
  `translate(paneW/2 - cx*zoom, paneH/2 - cy*zoom) scale(zoom)` with
  `transform-origin: 0 0`.
- `zoomAt(screenX, screenY, factor)`: get the image point under the cursor
  before and after, and shift `cx, cy` so that point stays put. Clamp
  `zoom ∈ [0.05, 32]`. Zoom steps are
  `[.0625,.125,.25,.333,.5,.667,1,1.5,2,3,4,6,8,12,16,32]`.
- `fit()`: `zoom = min(paneW/imgW, paneH/imgH) * 0.95`, centred.
- The viewport is shared by all panes, and all layers of one run have the same
  size (they're all cropped to the same box), so the panes line up.
  Exception: Spectrum stages have different sizes, so Spectrum calls `fit()` on
  every stage change.
- Markers render in an SVG inside the same transformed container, with
  `vector-effect: non-scaling-stroke`, 1.5 px, `--accent` for the crosshair and
  `--warn` for boxes.
- Probe: draw the current PNG into a cached offscreen canvas once, then
  `getImageData(x, y, 1, 1)`. Show `0.412` for gray (v/255) or `R .41 G .38
  B .30` for RGB.

### 4.5 Timeline (sequence workspaces)

- The FilmStrip shows `frames[].layers[frameLayer]` thumbnails. Before the
  first run, it shows the source's own thumbnails (`/api/media/{id}/thumb.jpg`,
  or `/frames` for video).
- ConfidenceTrack: an 8 px tall bar per frame, coloured by
  `meta.confidence`: ≥ 2 → `--ok`, ≥ 1.2 → `--warn`, else `--bad`, and null
  (reference frame) → `--text-3`. These are the same thresholds as
  `PeakStats.verdict`. The Highlight workspace colours by `meta.objects > 0`
  instead.
- Transport: ⏮ ◀ ▶/⏸ ▶ ⏭, a timecode `07 / 24` (frame index / count), and fps
  select `6 | 12 | 24`.
- The playhead drives `timeline.currentFrame`. The viewer's frame-layer pane
  and the Info panel (Highlight per-frame readouts) follow it.
- Align / Rotate·Scale with a video source: the markers **A** and **B** are
  draggable flags on the ruler; changing them sets `aIndex`/`bIndex` and
  triggers a run.

---

## 5. Copy (labels only — the complete vocabulary)

### 5.1 Style

- Title Case for panel titles, tab labels and menu items. Sentence case is not
  used, because there are no sentences.
- Parameter labels are ≤ 2 words or a symbol. Units go in the field suffix,
  never in the label.
- No trailing punctuation, no "Please", no "Upload your…". Verbs only on
  buttons: `Run`, `Import`, `Export`, `Reset`.
- Tooltips give the name and the shortcut only: `Zoom (Z)`, `Probe (I)`.

### 5.2 Labels per workspace

| Workspace | Group | Labels (in order) |
|---|---|---|
| Align | Source | `Source` [Pair · Video · Generate], `A`, `B`, `Base`, `Δy`, `Δx`, `Noise σ` |
| | Method | `Window`, `Sub-pixel`, `Magnitude β`, `Low-pass` |
| | Display | `Overlay`, `Tile`, `Opacity` |
| Rotate·Scale | Source | `Source` [Pair · Video · Generate], `A`, `B`, `Working Size` (px), `Base`, `Rotation` (°), `Scale` (×), `Δy`, `Δx`, `Noise σ` |
| | Method | `Robust`, `θ Bins`, `ρ Bins` |
| | Display | `Overlay` |
| Stack | Source | `Source` [Photos · Video · Generate], `Frames`, `Clean Ref`, `Working Size`, `Colour`, `Base`, `Count`, `Noise σ`, `Max Shift` |
| | Method | `Reducer`, `Align`, `Compare` |
| Remove | Source | `Source` [Photos · Video · Generate], `Frames`, `Working Size`, `Colour`, `Alignment` [Translation · Auto · Similarity], `Base`, `Count`, `Radius`, `Noise σ`, `Shake`, `Video`, `Read`, `Every Nth` |
| | Method | `Reducer`, `Filter Compare` |
| Highlight | Source | as Remove (+ `Reducer` under Method) |
| | Detection | `Detector`, `Band Low`, `Band High`, `Threshold k`, `Smooth`, `Min Area` |
| Spectrum | Source | `Image`, `Δy`, `Δx` |

Info panel readout labels: exactly the `label` strings the server sends
(`dy`, `dx`, `peak`, `PSR`, `ratio`, `PSNR before`, …). The verdict chip says
`LOCK` / `WEAK` / `LOST` for `locked` / `marginal` / `no lock`.

Flag badges: `inverted_contrast` → `Inverted`.

### 5.3 Empty and error states (viewer centre, `--text-3`, one line + one button)

| Condition | Text | Button |
|---|---|---|
| no input yet | `Drop Images` | `Import` |
| `need_two_images` | `2 Images Required` | `Import` |
| `need_two_frames` | `2+ Frames Required` | `Import` |
| `need_three_frames` | `3+ Frames Required` | `Import` |
| `no_video_backend` | `No Video Decoder` | — (tooltip: `pip install imageio-ffmpeg`) |
| `bad_media` | `Unreadable File` | `Import` |
| network down | `Server Offline` | `Retry` |

### 5.4 Menus

- **File**: Import… (Ctrl+O), Export Layer… (Ctrl+E), Export Sequence…
  (Ctrl+Shift+E, sequence workspaces only), Reset Workspace.
- **View**: Fit (Ctrl+0), 100 % (Ctrl+1), Zoom In, Zoom Out, 1-Up, 2-Up,
  4-Up, Split, Theme ▸ System / Light / Dark.
- **Window**: Properties, Info, Layers, Media, Graph, Timeline (check items),
  Reset Layout.
- **Help**: Keyboard Shortcuts (a dialog with a two-column table, no prose).

---

## 6. Phases (do in order; each ends in something runnable)

### Phase 1 — Backend skeleton
- `server/` files: `config.py`, `main.py`, `__main__.py`, `schemas.py`,
  `media.py`, `layers.py`, `encode.py`, routes `media.py`, `registries.py`,
  `layers.py`.
- **Done when:** `python -m server` starts; `GET /api/health`,
  `/api/registries` (lists match `ss.REDUCERS.names()` etc.) and `/api/media`
  (samples listed) respond; you can upload a JPEG and fetch its thumbnail.

### Phase 2 — Services + run routes
- `services/common.py`, then the six services in order: align, rotate, stack,
  remove, highlight, spectrum. Then `routes/runs.py` (run, pixel, export,
  export-sequence).
- `tests/test_server.py` with FastAPI `TestClient`:
  - one test per workspace with the **synthetic** source (no sample files
    needed). Assert 200, that the expected layer names exist, that every layer
    URL returns `image/png`, and a numeric sanity check (align synthetic: `|dy
    - 12.5| < 0.1`, `|dx + 7.5| < 0.1`; rotate synthetic: angle error < 1°);
  - one test per workspace with the default **samples**, skipped if the
    folder is missing (`pytest.mark.skipif`);
  - `/registries` equals `ss.registries()` names;
  - `/pixel` returns equal-length `signal`/`freq`/`spectrum`;
  - a bad request returns the right 422 `code`.
- **Done when:** `pytest tests/test_server.py` passes **and** the existing
  `pytest tests` still passes, untouched.

### Phase 3 — Frontend scaffold + design system
- `npm create vite@latest web -- --template react-ts`, add the deps from §4.1,
  ESLint/Prettier, the Vite proxy.
- `tokens.css`, `reset.css`, `base.css`; Google Fonts link in `index.html`.
- Controls: Button, IconButton, Checkbox, Segmented, Select, ScrubField,
  Badge, VerdictChip. Build a hidden `/#kit` route that renders every control
  in every state (default, hover, focus, disabled), side by side in light and
  dark, and use it to review.
- **Done when:** `npm run build` and `npm run lint` are clean, `/#kit` looks
  right in both themes, and ScrubField drag, Shift and Alt modifiers and
  double-click reset all work.

### Phase 4 — Shell
- Shell grid, AppBar with menus, WorkspaceTabs, ThemeToggle, ToolBar,
  StatusBar, Panel, and the resizable right dock and bottom timeline slot.
  Layout persistence, the Tab key to hide panels, and the keyboard shortcut
  registry.
- **Done when:** all six tabs switch, panels collapse and resize and remember
  it, and the theme cycles System → Light → Dark and survives a reload.

### Phase 5 — Viewer
- Pane, shared viewport, gestures, DocumentTabs, 1/2/4-up, SplitCompare,
  MarkerLayer, probe → StatusBar.
- **Done when:** with a hard-coded sample layer URL you can zoom about the
  cursor, pan with Space, Ctrl+0/Ctrl+1 work, 2-up panes stay in sync, and
  the split divider drags.

### Phase 6 — Data + Properties + Info + Layers + Media
- `api/*`, `state/params.ts`, `workspaces/*/def.ts` (all six),
  PropertiesPanel, InfoPanel, LayersPanel, MediaPanel, drag-and-drop import,
  the Preview/Run flow (§4.3), empty states (§5.3).
- **Done when:** Align and Rotate·Scale are fully usable end to end with the
  samples and with uploads, and Spectrum works with its StageStrip (stage tabs
  plus a KaTeX formula line).

### Phase 7 — Timeline + sequence workspaces + Graph
- Timeline components, sequence preloading, playback, A/B markers for video
  in Align/Rotate, GraphPanel (recharts line and bar + table), Remove probe →
  `/pixel`, exports (PNG, MP4/GIF).
- **Done when:** Stack, Remove and Highlight work with photo sets, generated
  input **and** a video file. Highlight boxes follow the playhead, the Remove
  probe updates the Graph, and exports download.

### Phase 8 — Polish and verification
- An accessibility pass: every control is reachable by keyboard, has visible
  focus (2 px `--accent` outline) and an `aria-label` on icon buttons, and
  text contrast is ≥ 4.5:1 in both themes.
- Vitest unit tests for `lib/format.ts` and the viewport maths (`zoomAt` keeps
  the point under the cursor fixed; `fit` centres).
- `run_web.py` both modes. Add a short "Web frontend" section to the **end**
  of `ARCHITECTURE.md` describing `server/` and `web/` with the same "one rule"
  framing. This is the only permitted edit to an existing file.
- **Done when:** the §7 checklist passes.

---

## 7. Final acceptance checklist

- [ ] `streamlit run app/main.py` behaves exactly as before, and
      `pytest tests` passes with no changes to existing tests.
- [ ] `git diff --stat` (or a manual check) shows no edits under `spectrasync/`,
      `app/`, `tools/`.
- [ ] `grep -rn "import numpy" server/routes` → nothing, and in
      `server/services` numpy is used only for crop, mask, clip or dtype.
- [ ] `grep -rnE "#[0-9a-fA-F]{3,6}\b" web/src --include=*.tsx --include=*.module.css`
      → nothing (colours live only in tokens.css).
- [ ] No sentence-length strings in `web/src` (search for `". "` inside JSX
      text): the UI is labels and numbers only.
- [ ] Every workspace works in light and dark, at 1280×720 and at 1920×1080.
- [ ] Every Streamlit capability has a web equivalent: each page's inputs,
      method options, readouts, images, table and download (see the §3.6
      per-service lists).
- [ ] A new reducer registered in `spectrasync/features/temporal.py` appears in
      the web Reducer dropdown after a server restart, with no web change.
