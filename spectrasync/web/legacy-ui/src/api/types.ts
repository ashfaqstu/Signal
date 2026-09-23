export type ThemeMode = "system" | "light" | "dark";
export type ToolMode = "hand" | "zoom" | "probe" | "split";
export type LayoutMode = "1up" | "2up" | "4up" | "split";

export interface HealthResponse {
  ok: boolean;
  version: string;
  video: boolean;
}

export interface RegistryItem {
  name: string;
}

export interface RegistriesResponse {
  window: RegistryItem[];
  subpixel: RegistryItem[];
  reducer: RegistryItem[];
  detector: RegistryItem[];
  overlay: RegistryItem[];
  filter: RegistryItem[];
}

export interface MediaItem {
  id: string;
  name: string;
  kind: "image" | "video";
  path: string;
  group: string;
  sample: boolean;
  width: number;
  height: number;
  nFrames?: number | null;
}

export interface VideoFrameItem {
  index: number;
  thumbUrl: string;
}

export interface Readout {
  key: string;
  label: string;
  value: number | string;
  unit?: string;
  fmt?: string;
  tone?: "default" | "ok" | "warn" | "bad" | "muted";
}

export interface LayerRef {
  id: string;
  name: string;
  group: string;
  kind: "image" | "mask" | "heatmap";
  width: number;
  height: number;
  url: string;
}

export interface Marker {
  layer: string;
  type: "crosshair" | "box";
  x: number;
  y: number;
  w?: number;
  h?: number;
}

export interface FrameRef {
  index: number;
  name: string;
  layers: Record<string, string>;
  meta: Record<string, any>;
}

export interface ChartSeries {
  name: string;
  values: number[];
  role?: "primary" | "reference";
}

export interface Chart {
  id: string;
  kind: "line" | "bar";
  x: number[] | string[];
  series: ChartSeries[];
}

export interface Table {
  columns: string[];
  rows: (number | string)[][];
}

export interface RunResult {
  runId: string;
  workspace: string;
  elapsedMs: number;
  verdict?: "locked" | "marginal" | "no lock" | null;
  readouts: Readout[];
  layers: LayerRef[];
  markers: Marker[];
  frames: FrameRef[];
  charts: Chart[];
  table?: Table | null;
  flags: string[];
}

export interface PixelTimeseriesResponse {
  signal: number[];
  median: number;
  freq: number[];
  spectrum: number[];
}

export interface ApiErrorPayload {
  code: string;
  message?: string;
  detail?: any;
}
