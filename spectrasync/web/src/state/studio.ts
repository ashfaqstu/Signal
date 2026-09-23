import { create } from "zustand";
import type { RunResult } from "../api/types";
import { getItem, setItem } from "../lib/storage";
import { TOOLS, defaultInput, withDefaults } from "../tools/catalog";
import type { ParamValue, Params, ToolId, ToolInput } from "../tools/types";

export type ThemeMode = "system" | "light" | "dark";

export interface HistoryEntry {
  id: string;
  tool: ToolId;
  at: number;
  thumb: string | null;
  headline: string;
  frames: number;
  elapsedMs: number;
  gainDb: number | null;
}

interface ToolState {
  params: Params;
  input: ToolInput;
}

interface StudioState {
  theme: ThemeMode;
  tools: Record<ToolId, ToolState>;
  results: Partial<Record<ToolId, RunResult>>;
  history: HistoryEntry[];
  setTheme: (t: ThemeMode) => void;
  setParam: (tool: ToolId, key: string, value: ParamValue) => void;
  setInput: (tool: ToolId, input: ToolInput) => void;
  resetTool: (tool: ToolId) => void;
  setResult: (tool: ToolId, r: RunResult) => void;
  addHistory: (e: HistoryEntry) => void;
  clearHistory: () => void;
}

const K_THEME = "ss.theme";
const K_TOOLS = "ss.tools.v2";
const K_HISTORY = "ss.history.v2";
const HISTORY_MAX = 24;

function initialTools(): Record<ToolId, ToolState> {
  const saved = getItem<Partial<Record<ToolId, ToolState>>>(K_TOOLS, {});
  return Object.fromEntries(
    TOOLS.map((t) => [
      t.id,
      {
        params: withDefaults(t, saved[t.id]?.params),
        input: saved[t.id]?.input ?? defaultInput(t),
      },
    ]),
  ) as Record<ToolId, ToolState>;
}

export function applyTheme(t: ThemeMode) {
  const root = document.documentElement;
  if (t === "system") delete root.dataset.theme;
  else root.dataset.theme = t;
}

export const useStudio = create<StudioState>((set) => ({
  theme: getItem<ThemeMode>(K_THEME, "system"),
  tools: initialTools(),
  results: {},
  history: getItem<HistoryEntry[]>(K_HISTORY, []),

  setTheme: (theme) => {
    applyTheme(theme);
    setItem(K_THEME, theme);
    set({ theme });
  },
  setParam: (tool, key, value) =>
    set((s) => ({
      tools: { ...s.tools, [tool]: { ...s.tools[tool], params: { ...s.tools[tool].params, [key]: value } } },
    })),
  setInput: (tool, input) =>
    set((s) => ({ tools: { ...s.tools, [tool]: { ...s.tools[tool], input } } })),
  resetTool: (tool) =>
    set((s) => {
      const def = TOOLS.find((t) => t.id === tool)!;
      return { tools: { ...s.tools, [tool]: { params: withDefaults(def, {}), input: s.tools[tool].input } } };
    }),
  setResult: (tool, r) => set((s) => ({ results: { ...s.results, [tool]: r } })),
  addHistory: (e) =>
    set((s) => {
      const history = [e, ...s.history].slice(0, HISTORY_MAX);
      setItem(K_HISTORY, history);
      return { history };
    }),
  clearHistory: () => {
    setItem(K_HISTORY, []);
    set({ history: [] });
  },
}));

useStudio.subscribe((s, prev) => {
  if (s.tools !== prev.tools) setItem(K_TOOLS, s.tools);
});
