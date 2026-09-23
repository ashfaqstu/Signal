import { create } from "zustand";
import { RunResult } from "../api/types";

export interface WorkspaceParams {
  align: {
    source: "pair" | "synthetic" | "video";
    aId: string;
    bId: string;
    mediaId: string;
    aIndex: number;
    bIndex: number;
    baseId: string;
    dy: number;
    dx: number;
    noise: number;
    window: string;
    subpixel: string;
    beta: number;
    lowpass: number;
    overlay: string;
    tile: number;
    alpha: number;
  };
  rotate: {
    source: "pair" | "synthetic" | "video";
    aId: string;
    bId: string;
    mediaId: string;
    aIndex: number;
    bIndex: number;
    maxSide: number;
    baseId: string;
    angle: number;
    scale: number;
    dy: number;
    dx: number;
    noise: number;
    robust: boolean;
    nTheta: number;
    nRho: number;
    overlay: string;
  };
  stack: {
    source: "photos" | "video" | "synthetic";
    mediaIds: string[];
    maxSide: number;
    colour: boolean;
    cleanId: string;
    mediaId: string;
    frames: number;
    step: number;
    baseId: string;
    n: number;
    noise: number;
    shift: number;
    reducer: string;
    align: boolean;
    compare: boolean;
  };
  remove: {
    source: "photos" | "synthetic" | "video";
    mediaIds: string[];
    maxSide: number;
    colour: boolean;
    mode: "translation" | "auto" | "similarity";
    baseId: string;
    n: number;
    radius: number;
    noise: number;
    shake: number;
    mediaId: string;
    frames: number;
    step: number;
    reducer: string;
    compareFilters: boolean;
  };
  highlight: {
    source: "photos" | "synthetic" | "video";
    mediaIds: string[];
    maxSide: number;
    colour: boolean;
    mode: "translation" | "auto" | "similarity";
    reducer: string;
    baseId: string;
    n: number;
    radius: number;
    noise: number;
    mediaId: string;
    frames: number;
    step: number;
    detector: string;
    low: number;
    high: number;
    k: number;
    smooth: number;
    minArea: number;
  };
  spectrum: {
    baseId: string;
    dy: number;
    dx: number;
    activeStage: number;
  };
}

export const DEFAULT_PARAMS: WorkspaceParams = {
  align: {
    source: "synthetic",
    aId: "",
    bId: "",
    mediaId: "",
    aIndex: 0,
    bIndex: 1,
    baseId: "",
    dy: 12.5,
    dx: -7.5,
    noise: 0.0,
    window: "hann",
    subpixel: "parabolic",
    beta: 1.0,
    lowpass: 0.0,
    overlay: "anaglyph",
    tile: 32,
    alpha: 0.5,
  },
  rotate: {
    source: "pair",
    aId: "",
    bId: "",
    mediaId: "",
    aIndex: 0,
    bIndex: 1,
    maxSide: 704,
    baseId: "",
    angle: 20.0,
    scale: 1.20,
    dy: 9.0,
    dx: -14.0,
    noise: 0.0,
    robust: true,
    nTheta: 720,
    nRho: 512,
    overlay: "anaglyph",
  },
  stack: {
    source: "photos",
    mediaIds: [],
    maxSide: 800,
    colour: true,
    cleanId: "",
    mediaId: "",
    frames: 16,
    step: 1,
    baseId: "",
    n: 16,
    noise: 0.12,
    shift: 5.0,
    reducer: "mean",
    align: true,
    compare: true,
  },
  remove: {
    source: "photos",
    mediaIds: [],
    maxSide: 640,
    colour: true,
    mode: "auto",
    baseId: "",
    n: 12,
    radius: 26,
    noise: 0.01,
    shake: 4.0,
    mediaId: "",
    frames: 24,
    step: 2,
    reducer: "shorth",
    compareFilters: true,
  },
  highlight: {
    source: "photos",
    mediaIds: [],
    maxSide: 640,
    colour: true,
    mode: "auto",
    reducer: "shorth",
    baseId: "",
    n: 12,
    radius: 26,
    noise: 0.01,
    mediaId: "",
    frames: 24,
    step: 2,
    detector: "bandpass",
    low: 0.02,
    high: 0.20,
    k: 3.0,
    smooth: 1.5,
    minArea: 40,
  },
  spectrum: {
    baseId: "",
    dy: 12.0,
    dx: -8.0,
    activeStage: 0,
  },
};

interface ParamsState {
  params: WorkspaceParams;
  results: Record<string, RunResult | null>;
  errors: Record<string, any | null>;

  setParam: <W extends keyof WorkspaceParams, K extends keyof WorkspaceParams[W]>(
    workspace: W,
    key: K,
    value: WorkspaceParams[W][K]
  ) => void;
  setWorkspaceParams: (workspace: string, params: Record<string, any>) => void;
  resetParams: (workspace: keyof WorkspaceParams) => void;
  setResult: (workspace: string, result: RunResult | null) => void;
  setError: (workspace: string, error: any | null) => void;
}

export const useParamsStore = create<ParamsState>((set) => ({
  params: { ...DEFAULT_PARAMS },
  results: {},
  errors: {},

  setParam: (workspace, key, value) =>
    set((state) => ({
      params: {
        ...state.params,
        [workspace]: {
          ...state.params[workspace],
          [key]: value,
        },
      },
    })),

  setWorkspaceParams: (workspace, params) =>
    set((state) => ({
      params: {
        ...state.params,
        [workspace]: {
          ...(state.params as any)[workspace],
          ...params,
        },
      },
    })),

  resetParams: (workspace) =>
    set((state) => ({
      params: {
        ...state.params,
        [workspace]: { ...DEFAULT_PARAMS[workspace] },
      },
    })),

  setResult: (workspace, result) =>
    set((state) => ({
      results: {
        ...state.results,
        [workspace]: result,
      },
      errors: {
        ...state.errors,
        [workspace]: null,
      },
    })),

  setError: (workspace, error) =>
    set((state) => ({
      errors: {
        ...state.errors,
        [workspace]: error,
      },
    })),
}));
