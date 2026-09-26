import type { LucideIcon } from "lucide-react";
import type { MediaItem, RegistriesResponse, RunResult } from "../api/types";

export type ToolId = "align" | "rotate" | "stack" | "remove" | "highlight" | "spectrum";

/** Where a tool's input comes from. */
export type Source = "sample" | "files" | "simulate";

export type ParamValue = number | string | boolean | null;
export type Params = Record<string, ParamValue>;

export interface ToolInput {
  source: Source;
  /** Picked media, in order. Empty with source "sample" = the tool's default sample. */
  mediaIds: string[];
}

/** What a control can see when deciding whether to show itself. */
export interface ControlContext {
  params: Params;
  input: ToolInput;
  video: MediaItem | null;
}

type Base = {
  key: string;
  label: string;
  when?: (ctx: ControlContext) => boolean;
};

export type Control =
  | (Base & { kind: "slider"; min: number; max: number; step: number; unit?: string; digits?: number })
  | (Base & { kind: "choice"; options: { value: string | number; label: string }[] })
  | (Base & { kind: "registry"; registry: keyof RegistriesResponse })
  | (Base & { kind: "toggle" })
  | (Base & { kind: "media"; accept: "image" });

/**
 * A way of looking at a result. Layer names are the ones the server sends
 * (`server/services/*.py`); frame keys are `FrameRef.layers` keys.
 */
export type View =
  | { id: string; label: string; type: "compare"; before: string; after: string }
  | { id: string; label: string; type: "single"; layer: string | string[]; probe?: boolean }
  | { id: string; label: string; type: "grid"; layers?: string[]; group?: string }
  | { id: string; label: string; type: "frame"; frameLayer: string; boxes?: boolean }
  | { id: string; label: string; type: "frameCompare"; before: string; after: string };

export interface Metric {
  label: string;
  value: string;
  tone?: "ok" | "warn" | "bad";
}

export interface ToolDef {
  id: ToolId;
  name: string;
  tagline: string;
  icon: LucideIcon;
  /** CSS custom property holding the tool gradient. */
  gradient: string;
  input: "pair" | "sequence" | "single";
  sources: Source[];
  defaultSource: Source;
  /** Media group used by "Sample" (see server/config.py SAMPLES). */
  sampleGroup: string;
  /** Media group for the "Simulate" preview thumbnail's base photo, when no
   * media has been explicitly picked (see server/config.py SAMPLES). Falls
   * back to `sampleGroup` when omitted. */
  baseGroup?: string;
  acceptsVideo: boolean;
  minFiles: number;
  defaults: Params;
  simulate: Control[];
  basic: Control[];
  advanced: Control[];
  views: View[];
  /** Spectrum only: a formula per view id, shown above the page. */
  formulas?: Record<string, string>;
  headline: (r: RunResult, frame: number) => Metric[];
  request: (p: Params, input: ToolInput, media: MediaItem[]) => Record<string, unknown>;
}
