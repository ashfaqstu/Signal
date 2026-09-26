/**
 * Every tool in the studio, as data.
 *
 * The web twin of app/registry.py: adding a tool is one entry here. Defaults
 * and ranges mirror the Streamlit sliders in app/pages/*.py, and the request
 * bodies match server/schemas.py.
 */

import {
  Crosshair,
  Layers,
  RotateCw,
  ScanSearch,
  Eraser,
  Waves,
} from "lucide-react";
import type { MediaItem, RunResult } from "../api/types";
import { formatReadout } from "../lib/format";
import type { Control, ControlContext, Metric, Params, ToolDef, ToolId, ToolInput } from "./types";

/* ---------- helpers ---------- */

function readout(r: RunResult, key: string): string {
  const x = r.readouts.find((o) => o.key === key);
  return x ? formatReadout(x.value, x.fmt, x.unit) : "—";
}

function has(r: RunResult, key: string): boolean {
  return r.readouts.some((o) => o.key === key);
}

function picked(input: ToolInput, media: MediaItem[]): MediaItem[] {
  if (input.source === "sample") return [];
  return input.mediaIds
    .map((id) => media.find((m) => m.id === id))
    .filter((m): m is MediaItem => Boolean(m));
}

function pickedVideo(input: ToolInput, media: MediaItem[]): MediaItem | null {
  return picked(input, media).find((m) => m.kind === "video") ?? null;
}

function pickedImageIds(input: ToolInput, media: MediaItem[]): string[] {
  return picked(input, media)
    .filter((m) => m.kind === "image")
    .map((m) => m.id);
}

const isSim = (c: ControlContext) => c.input.source === "simulate";
const isVideo = (c: ControlContext) => c.input.source === "files" && c.video !== null;
const isPhotos = (c: ControlContext) => c.input.source !== "simulate" && !isVideo(c);

const verdictTone = (r: RunResult): Metric["tone"] =>
  r.verdict === "locked" ? "ok" : r.verdict === "marginal" ? "warn" : r.verdict ? "bad" : undefined;

const verdictLabel = (r: RunResult) =>
  r.verdict === "locked" ? "Locked" : r.verdict === "marginal" ? "Weak" : r.verdict ? "Lost" : "—";

/* shared controls */

const colour: Control = { key: "colour", label: "Colour", kind: "toggle", when: (c) => !isSim(c) };

const frameA: Control = {
  key: "aIndex", label: "Frame A", kind: "slider", min: 0, max: 120, step: 1, when: isVideo,
};
const frameB: Control = {
  key: "bIndex", label: "Frame B", kind: "slider", min: 0, max: 120, step: 1, when: isVideo,
};
const videoFrames: Control = {
  key: "frames", label: "Frames to read", kind: "slider", min: 4, max: 60, step: 1, when: isVideo,
};
const videoStep: Control = {
  key: "step", label: "Every Nth frame", kind: "slider", min: 1, max: 10, step: 1, when: isVideo,
};
const alignment: Control = {
  key: "mode", label: "Alignment", kind: "choice", when: (c) => !isSim(c),
  options: [
    { value: "auto", label: "Auto" },
    { value: "translation", label: "Shift" },
    { value: "similarity", label: "Rotate + scale" },
  ],
};

function sizeCtl(max: number): Control {
  return { key: "maxSide", label: "Working size", kind: "slider", min: 320, max, step: 32, unit: "px", when: isPhotos };
}

/** Body fields shared by the three sequence tools. */
function sequenceSource(p: Params, input: ToolInput, media: MediaItem[]) {
  const video = pickedVideo(input, media);
  if (input.source === "simulate") return { source: "synthetic", baseId: pickedImageIds(input, media)[0] ?? null };
  if (video) return { source: "video", mediaId: video.id, frames: p.frames, step: p.step };
  return { source: "photos", mediaIds: pickedImageIds(input, media) };
}

function pairSource(input: ToolInput, media: MediaItem[], p: Params) {
  const video = pickedVideo(input, media);
  if (input.source === "simulate") return { source: "synthetic", baseId: pickedImageIds(input, media)[0] ?? null };
  if (video) return { source: "video", mediaId: video.id, aIndex: p.aIndex, bIndex: p.bIndex };
  const ids = pickedImageIds(input, media);
  return { source: "pair", aId: ids[0] ?? null, bId: ids[1] ?? null };
}

/* ---------- tools ---------- */

const align: ToolDef = {
  id: "align",
  name: "Align",
  tagline: "Line up two shots",
  icon: Crosshair,
  gradient: "var(--tool-align)",
  input: "pair",
  sources: ["simulate", "sample", "files"],
  defaultSource: "simulate",
  sampleGroup: "Pair · translation",
  baseGroup: "Base · translation",
  acceptsVideo: true,
  minFiles: 2,
  defaults: {
    dy: 12.5, dx: -7.5, noise: 0, window: "hann", subpixel: "parabolic", beta: 1, lowpass: 0,
    overlay: "anaglyph", tile: 32, alpha: 0.5, aIndex: 0, bIndex: 1,
  },
  simulate: [
    { key: "dy", label: "Shift Y", kind: "slider", min: -40, max: 40, step: 0.5, unit: "px", digits: 1 },
    { key: "dx", label: "Shift X", kind: "slider", min: -40, max: 40, step: 0.5, unit: "px", digits: 1 },
    { key: "noise", label: "Noise", kind: "slider", min: 0, max: 0.4, step: 0.01, digits: 2 },
  ],
  basic: [
    frameA,
    frameB,
    { key: "overlay", label: "Overlay", kind: "registry", registry: "overlay" },
  ],
  advanced: [
    { key: "tile", label: "Tile", kind: "slider", min: 8, max: 128, step: 1, unit: "px",
      when: (c) => c.params.overlay === "checkerboard" },
    { key: "alpha", label: "Opacity", kind: "slider", min: 0, max: 1, step: 0.05, digits: 2,
      when: (c) => c.params.overlay === "blend" },
    { key: "window", label: "Window", kind: "registry", registry: "window" },
    { key: "subpixel", label: "Sub-pixel", kind: "registry", registry: "subpixel" },
    { key: "beta", label: "Magnitude β", kind: "slider", min: 0, max: 1, step: 0.05, digits: 2 },
    { key: "lowpass", label: "Low-pass", kind: "slider", min: 0, max: 0.5, step: 0.01, digits: 2 },
  ],
  views: [
    { id: "compare", label: "Before / After", type: "compare", before: "Overlay before", after: "Overlay" },
    { id: "diff", label: "Difference", type: "compare", before: "Δ before", after: "Δ after" },
    { id: "images", label: "Images", type: "grid", layers: ["A", "B", "B aligned"] },
    { id: "freq", label: "Frequency", type: "grid", layers: ["|F₁|", "|F₂|", "∠R", "r(x,y)"] },
  ],
  headline: (r) => {
    const m: Metric[] = [
      { label: "Shift Y", value: readout(r, "dy") },
      { label: "Shift X", value: readout(r, "dx") },
      { label: "Lock", value: verdictLabel(r), tone: verdictTone(r) },
    ];
    if (has(r, "err_dy")) m.push({ label: "Error", value: `${readout(r, "err_dy")} · ${readout(r, "err_dx")}` });
    return m;
  },
  request: (p, input, media) => ({
    ...pairSource(input, media, p),
    dy: p.dy, dx: p.dx, noise: p.noise, window: p.window, subpixel: p.subpixel,
    beta: p.beta, lowpass: p.lowpass, overlay: p.overlay, tile: p.tile, alpha: p.alpha,
  }),
};

const rotate: ToolDef = {
  id: "rotate",
  name: "Rotate & Scale",
  tagline: "Undo turn and zoom",
  icon: RotateCw,
  gradient: "var(--tool-rotate)",
  input: "pair",
  sources: ["sample", "files", "simulate"],
  defaultSource: "sample",
  sampleGroup: "Pair · rotated",
  baseGroup: "Base · rotation & scale",
  acceptsVideo: true,
  minFiles: 2,
  defaults: {
    maxSide: 704, angle: 20, scale: 1.2, dy: 9, dx: -14, noise: 0, robust: true,
    nTheta: 720, nRho: 512, overlay: "anaglyph", aIndex: 0, bIndex: 1,
  },
  simulate: [
    { key: "angle", label: "Rotation", kind: "slider", min: -180, max: 180, step: 1, unit: "°" },
    { key: "scale", label: "Scale", kind: "slider", min: 0.7, max: 2, step: 0.01, unit: "×", digits: 2 },
    { key: "noise", label: "Noise", kind: "slider", min: 0, max: 0.2, step: 0.01, digits: 2 },
  ],
  basic: [
    frameA,
    frameB,
    { key: "overlay", label: "Overlay", kind: "registry", registry: "overlay" },
  ],
  advanced: [
    { key: "dy", label: "Shift Y", kind: "slider", min: -30, max: 30, step: 1, unit: "px", when: isSim },
    { key: "dx", label: "Shift X", kind: "slider", min: -30, max: 30, step: 1, unit: "px", when: isSim },
    { key: "robust", label: "Robust search", kind: "toggle" },
    { key: "nTheta", label: "Angle bins", kind: "choice",
      options: [180, 360, 720, 1080].map((v) => ({ value: v, label: String(v) })) },
    { key: "nRho", label: "Radius bins", kind: "choice",
      options: [128, 256, 512, 768].map((v) => ({ value: v, label: String(v) })) },
    sizeCtl(1280),
  ],
  views: [
    { id: "compare", label: "Before / After", type: "compare", before: "Overlay before", after: "Overlay after" },
    { id: "restored", label: "Restored", type: "single", layer: "B restored" },
    { id: "images", label: "Images", type: "grid", layers: ["A", "B"] },
    { id: "freq", label: "Log-polar", type: "grid", layers: ["log-polar A", "log-polar B", "ρθ correlation"] },
  ],
  headline: (r) => {
    const m: Metric[] = [
      { label: "Rotation", value: readout(r, "rotation") },
      { label: "Scale", value: readout(r, "scale") },
      { label: "Lock", value: verdictLabel(r), tone: verdictTone(r) },
    ];
    if (has(r, "err_deg")) m.push({ label: "Error", value: `${readout(r, "err_deg")} · ${readout(r, "err_scale")}` });
    return m;
  },
  request: (p, input, media) => ({
    ...pairSource(input, media, p),
    maxSide: p.maxSide, angle: p.angle, scale: p.scale, dy: p.dy, dx: p.dx, noise: p.noise,
    robust: p.robust, nTheta: p.nTheta, nRho: p.nRho, overlay: p.overlay,
  }),
};

const stack: ToolDef = {
  id: "stack",
  name: "Denoise",
  tagline: "Stack a burst",
  icon: Layers,
  gradient: "var(--tool-stack)",
  input: "sequence",
  sources: ["sample", "files", "simulate"],
  defaultSource: "sample",
  sampleGroup: "Burst · noisy",
  baseGroup: "Base · stacking",
  acceptsVideo: true,
  minFiles: 2,
  defaults: {
    reducer: "mean", align: true, compare: true, maxSide: 800, colour: true, cleanId: null,
    n: 16, noise: 0.12, shift: 5, frames: 16, step: 1,
  },
  simulate: [
    { key: "n", label: "Frames", kind: "slider", min: 2, max: 32, step: 1 },
    { key: "noise", label: "Noise", kind: "slider", min: 0, max: 0.4, step: 0.01, digits: 2 },
    { key: "shift", label: "Camera shake", kind: "slider", min: 0, max: 15, step: 0.5, unit: "px", digits: 1 },
  ],
  basic: [
    videoFrames,
    { key: "reducer", label: "Method", kind: "registry", registry: "reducer" },
    { key: "align", label: "Align frames", kind: "toggle" },
  ],
  advanced: [
    videoStep,
    { key: "compare", label: "Compare methods", kind: "toggle" },
    { key: "cleanId", label: "Clean reference", kind: "media", accept: "image",
      when: (c) => c.input.source === "files" && c.video === null },
    sizeCtl(1600),
    colour,
  ],
  views: [
    { id: "compare", label: "Before / After", type: "compare", before: "Raw", after: "Stacked" },
    { id: "result", label: "Result", type: "single", layer: "Stacked" },
    { id: "removed", label: "Noise removed", type: "single", layer: ["Residual", "Removed"] },
    { id: "methods", label: "Methods", type: "grid", group: "Reducers" },
    { id: "frames", label: "Frames", type: "frame", frameLayer: "frame" },
  ],
  headline: (r) => {
    const m: Metric[] = has(r, "gain")
      ? [
          { label: "Gain", value: readout(r, "gain"), tone: "ok" },
          { label: "PSNR", value: readout(r, "psnr") },
        ]
      : [
          { label: "Noise down", value: readout(r, "sigma_ratio"), tone: "ok" },
          { label: "σ", value: `${readout(r, "sigma_raw")} → ${readout(r, "sigma_out")}` },
        ];
    m.push({ label: "Frames", value: readout(r, "frames") });
    m.push({ label: "Aligned", value: readout(r, "locked") });
    return m;
  },
  request: (p, input, media) => ({
    ...sequenceSource(p, input, media),
    reducer: p.reducer, align: p.align, compare: p.compare, maxSide: p.maxSide, colour: p.colour,
    cleanId: input.source === "files" ? p.cleanId : null,
    n: p.n, noise: p.noise, shift: p.shift,
  }),
};

const remove: ToolDef = {
  id: "remove",
  name: "Remove Objects",
  tagline: "Erase passers-by",
  icon: Eraser,
  gradient: "var(--tool-remove)",
  input: "sequence",
  sources: ["sample", "files", "simulate"],
  defaultSource: "sample",
  sampleGroup: "Crowd · object removal",
  baseGroup: "Base · object removal",
  acceptsVideo: true,
  minFiles: 3,
  defaults: {
    reducer: "shorth", mode: "auto", compareFilters: true, maxSide: 640, colour: true,
    n: 12, radius: 26, noise: 0.01, shake: 4, frames: 24, step: 2,
  },
  simulate: [
    { key: "n", label: "Frames", kind: "slider", min: 4, max: 24, step: 1 },
    { key: "radius", label: "Object size", kind: "slider", min: 6, max: 60, step: 2, unit: "px" },
    { key: "shake", label: "Camera shake", kind: "slider", min: 0, max: 12, step: 0.5, unit: "px", digits: 1 },
    { key: "noise", label: "Noise", kind: "slider", min: 0, max: 0.2, step: 0.005, digits: 3 },
  ],
  basic: [
    videoFrames,
    { key: "reducer", label: "Method", kind: "registry", registry: "reducer" },
    alignment,
  ],
  advanced: [
    videoStep,
    { key: "compareFilters", label: "Compare filters", kind: "toggle" },
    sizeCtl(1600),
    colour,
  ],
  views: [
    { id: "compare", label: "Before / After", type: "compare", before: "Frame 0", after: "Plate" },
    { id: "plate", label: "Clean plate", type: "single", layer: "Plate", probe: true },
    { id: "filters", label: "Filters", type: "grid", group: "Filters" },
    { id: "frames", label: "Frames", type: "frame", frameLayer: "frame" },
  ],
  headline: (r) => {
    if (has(r, "psnr_object"))
      return [
        { label: "Object area", value: readout(r, "psnr_object"), tone: "ok" },
        { label: "Was", value: readout(r, "from_psnr") },
        { label: "Frames", value: readout(r, "frames") },
      ];
    const m: Metric[] = [{ label: "Frames", value: readout(r, "frames") }];
    if (has(r, "locked")) m.push({ label: "Aligned", value: readout(r, "locked") });
    if (has(r, "coverage")) m.push({ label: "Coverage", value: readout(r, "coverage") });
    return m;
  },
  request: (p, input, media) => ({
    ...sequenceSource(p, input, media),
    reducer: p.reducer, mode: p.mode, compareFilters: p.compareFilters, maxSide: p.maxSide,
    colour: p.colour, n: p.n, radius: p.radius, noise: p.noise, shake: p.shake,
  }),
};

const highlight: ToolDef = {
  id: "highlight",
  name: "Highlight Motion",
  tagline: "Spot what moved",
  icon: ScanSearch,
  gradient: "var(--tool-highlight)",
  input: "sequence",
  sources: ["sample", "files", "simulate"],
  defaultSource: "sample",
  sampleGroup: "Crowd · highlight",
  baseGroup: "Base · highlight",
  acceptsVideo: true,
  minFiles: 3,
  defaults: {
    k: 3, minArea: 40, detector: "bandpass", low: 0.02, high: 0.2, smooth: 1.5,
    reducer: "shorth", mode: "auto", maxSide: 640, colour: true,
    n: 12, radius: 26, noise: 0.01, frames: 24, step: 2,
  },
  simulate: [
    { key: "n", label: "Frames", kind: "slider", min: 4, max: 24, step: 1 },
    { key: "radius", label: "Object size", kind: "slider", min: 6, max: 60, step: 2, unit: "px" },
    { key: "noise", label: "Noise", kind: "slider", min: 0, max: 0.2, step: 0.005, digits: 3 },
  ],
  basic: [
    videoFrames,
    { key: "k", label: "Threshold", kind: "slider", min: 0.5, max: 8, step: 0.1, digits: 1 },
    { key: "minArea", label: "Min size", kind: "slider", min: 5, max: 500, step: 5, unit: "px" },
  ],
  advanced: [
    videoStep,
    { key: "detector", label: "Detector", kind: "registry", registry: "detector" },
    { key: "low", label: "Band low", kind: "slider", min: 0.005, max: 0.1, step: 0.005, digits: 3,
      when: (c) => c.params.detector === "bandpass" },
    { key: "high", label: "Band high", kind: "slider", min: 0.05, max: 0.45, step: 0.01, digits: 2,
      when: (c) => c.params.detector === "bandpass" },
    { key: "smooth", label: "Smoothing", kind: "slider", min: 0, max: 5, step: 0.1, digits: 1 },
    { key: "reducer", label: "Background", kind: "registry", registry: "reducer", when: (c) => !isSim(c) },
    alignment,
    sizeCtl(1600),
    colour,
  ],
  views: [
    { id: "detected", label: "Detected", type: "frame", frameLayer: "overlay", boxes: true },
    { id: "compare", label: "Before / After", type: "frameCompare", before: "photo", after: "overlay" },
    { id: "mask", label: "Mask", type: "frame", frameLayer: "mask" },
    { id: "score", label: "Change", type: "frame", frameLayer: "score" },
    { id: "plate", label: "Background", type: "single", layer: "Plate" },
  ],
  headline: (r, frame) => {
    const meta = r.frames[frame]?.meta ?? {};
    const m: Metric[] = [
      { label: "In frame", value: String(meta.objects ?? 0), tone: meta.objects ? "ok" : undefined },
      { label: "Total", value: readout(r, "total_objects") },
    ];
    if (meta.size) m.push({ label: "Largest", value: String(meta.size) });
    if (meta.coverage !== undefined) m.push({ label: "Coverage", value: `${Number(meta.coverage).toFixed(2)} %` });
    return m;
  },
  request: (p, input, media) => ({
    ...sequenceSource(p, input, media),
    k: p.k, minArea: p.minArea, detector: p.detector, low: p.low, high: p.high, smooth: p.smooth,
    reducer: p.reducer, mode: p.mode, maxSide: p.maxSide, colour: p.colour,
    n: p.n, radius: p.radius, noise: p.noise,
  }),
};

const spectrum: ToolDef = {
  id: "spectrum",
  name: "Spectrum",
  tagline: "See the frequencies",
  icon: Waves,
  gradient: "var(--tool-spectrum)",
  input: "single",
  sources: ["sample", "files"],
  defaultSource: "sample",
  sampleGroup: "Base · theory",
  acceptsVideo: false,
  minFiles: 1,
  defaults: { dy: 12, dx: -8 },
  simulate: [],
  basic: [
    { key: "dy", label: "Shift Y", kind: "slider", min: -30, max: 30, step: 0.5, unit: "px", digits: 1 },
    { key: "dx", label: "Shift X", kind: "slider", min: -30, max: 30, step: 0.5, unit: "px", digits: 1 },
  ],
  advanced: [],
  views: [
    { id: "s1", label: "Pair", type: "single", layer: "f₁ | f₂" },
    { id: "s2", label: "|F₁|", type: "single", layer: "|F₁|" },
    { id: "s3", label: "|F₂|", type: "single", layer: "|F₂|" },
    { id: "s4", label: "Phase swap", type: "single", layer: "phase swap" },
    { id: "s5", label: "∠R", type: "single", layer: "∠R" },
    { id: "s6", label: "Peak", type: "single", layer: "r(x,y)" },
    { id: "s7", label: "Residual", type: "single", layer: "residual" },
    { id: "s8", label: "Log-polar A", type: "single", layer: "log-polar A" },
    { id: "s9", label: "Log-polar B", type: "single", layer: "log-polar B" },
    { id: "s10", label: "ρθ peak", type: "single", layer: "ρθ correlation" },
  ],
  formulas: {
    s1: "f_2(x,y) = f_1(x - x_0,\\; y - y_0)",
    s2: "F_2(u,v) = F_1(u,v)\\, e^{-j2\\pi(u x_0 + v y_0)}",
    s3: "\\left|F_2\\right| = \\left|F_1\\right|",
    s4: "|F_A|\\, e^{j\\angle F_B}",
    s5: "R = \\frac{F_2 \\overline{F_1}}{\\left|F_2 \\overline{F_1}\\right|}",
    s6: "\\mathcal{F}^{-1}\\{R\\} = \\delta(x - x_0,\\; y - y_0)",
    s7: "f_1 - \\hat f_2",
    s8: "|F_1|(\\log\\rho,\\ \\theta)",
    s9: "|F_2|(\\log\\rho,\\ \\theta)",
    s10: "(\\Delta\\theta,\\ \\Delta\\log\\rho) \\to (\\text{angle},\\ \\text{scale})",
  },
  headline: (r) => [
    { label: "Found Y", value: readout(r, "dy") },
    { label: "Found X", value: readout(r, "dx") },
    { label: "True", value: `${readout(r, "dy_true")} · ${readout(r, "dx_true")}` },
  ],
  request: (p, input, media) => ({
    baseId: pickedImageIds(input, media)[0] ?? null,
    dy: p.dy,
    dx: p.dx,
  }),
};

export const TOOLS: ToolDef[] = [remove, stack, highlight, align, rotate, spectrum];

export const TOOL_BY_ID: Record<ToolId, ToolDef> = Object.fromEntries(
  TOOLS.map((t) => [t.id, t]),
) as Record<ToolId, ToolDef>;

export function isToolId(x: string): x is ToolId {
  return x in TOOL_BY_ID;
}

/** A registry option name as a UI label: "sigma_clip" -> "Sigma clip". */
const PRETTY: Record<string, string> = {
  shorth: "Shorth",
  fourier_snr: "Fourier SNR",
  sigma_clip: "Sigma clip",
  trimmed_mean: "Trimmed mean",
  weighted_mean: "Weighted mean",
  ideal_lowpass: "Ideal low-pass",
  lowpass: "Low-pass",
  highpass: "High-pass",
  bandpass: "Band-pass",
  none: "None",
};

export function prettyOption(name: string): string {
  if (PRETTY[name]) return PRETTY[name];
  const s = name.replace(/_/g, " ");
  return s.charAt(0).toUpperCase() + s.slice(1);
}

export function defaultInput(tool: ToolDef): ToolInput {
  return { source: tool.defaultSource, mediaIds: [] };
}

export function withDefaults(tool: ToolDef, params: Params | undefined): Params {
  return { ...tool.defaults, ...(params ?? {}) };
}
