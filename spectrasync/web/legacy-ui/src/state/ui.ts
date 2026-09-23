import { create } from "zustand";
import { LayoutMode, ThemeMode, ToolMode } from "../api/types";
import { getItem, setItem } from "../lib/storage";

export interface ProbePixelData {
  x: number;
  y: number;
  r: number;
  g: number;
  b: number;
  gray: number;
  isRgb: boolean;
}

interface UiState {
  activeWorkspace: string;
  activeTool: ToolMode;
  layout: LayoutMode;
  paneLayers: string[];
  splitPos: number; // 0..1
  splitLayers: [string, string];
  preview: boolean;
  theme: ThemeMode;
  panelsHidden: boolean;
  activeRightTab: "layers" | "media" | "graph";
  probePixel: ProbePixelData | null;
  cursorPos: { x: number; y: number } | null;
  running: boolean;
  statusText: string;

  setActiveWorkspace: (id: string) => void;
  setActiveTool: (tool: ToolMode) => void;
  setLayout: (layout: LayoutMode) => void;
  setPaneLayer: (paneIndex: number, layerName: string) => void;
  setPaneLayers: (layers: string[]) => void;
  setSplitPos: (pos: number) => void;
  setSplitLayers: (layers: [string, string]) => void;
  setPreview: (preview: boolean) => void;
  setTheme: (theme: ThemeMode) => void;
  toggleTheme: () => void;
  togglePanelsHidden: () => void;
  setActiveRightTab: (tab: "layers" | "media" | "graph") => void;
  setProbePixel: (data: ProbePixelData | null) => void;
  setCursorPos: (pos: { x: number; y: number } | null) => void;
  setRunning: (running: boolean) => void;
  setStatusText: (text: string) => void;
}

const savedTheme = getItem<ThemeMode>("spectrasync_theme", "system");

export const useUiStore = create<UiState>((set, get) => ({
  activeWorkspace: "align",
  activeTool: "hand",
  layout: "1up",
  paneLayers: ["Overlay"],
  splitPos: 0.5,
  splitLayers: ["A", "Overlay"],
  preview: true,
  theme: savedTheme,
  panelsHidden: false,
  activeRightTab: "layers",
  probePixel: null,
  cursorPos: null,
  running: false,
  statusText: "",

  setActiveWorkspace: (id) => set({ activeWorkspace: id }),
  setActiveTool: (tool) => set({ activeTool: tool }),
  setLayout: (layout) => set({ layout }),
  setPaneLayer: (paneIndex, layerName) =>
    set((state) => {
      const copy = [...state.paneLayers];
      copy[paneIndex] = layerName;
      return { paneLayers: copy };
    }),
  setPaneLayers: (layers) => set({ paneLayers: layers }),
  setSplitPos: (pos) => set({ splitPos: Math.max(0.05, Math.min(0.95, pos)) }),
  setSplitLayers: (layers) => set({ splitLayers: layers }),
  setPreview: (preview) => set({ preview }),
  setTheme: (theme) => {
    setItem("spectrasync_theme", theme);
    if (theme === "system") {
      delete document.documentElement.dataset.theme;
    } else {
      document.documentElement.dataset.theme = theme;
    }
    set({ theme });
  },
  toggleTheme: () => {
    const current = get().theme;
    const next: ThemeMode =
      current === "system" ? "light" : current === "light" ? "dark" : "system";
    get().setTheme(next);
  },
  togglePanelsHidden: () => set((state) => ({ panelsHidden: !state.panelsHidden })),
  setActiveRightTab: (tab) => set({ activeRightTab: tab }),
  setProbePixel: (probePixel) => set({ probePixel }),
  setCursorPos: (cursorPos) => set({ cursorPos }),
  setRunning: (running) => set({ running }),
  setStatusText: (statusText) => set({ statusText }),
}));
