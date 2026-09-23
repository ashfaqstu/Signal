import { create } from "zustand";

interface TimelineState {
  currentFrame: number;
  playing: boolean;
  fps: number;
  markerA: number | null;
  markerB: number | null;
  maxFrames: number;

  setCurrentFrame: (frame: number) => void;
  setPlaying: (playing: boolean) => void;
  togglePlay: () => void;
  setFps: (fps: number) => void;
  stepFrame: (delta: number) => void;
  setMarkerA: (frame: number | null) => void;
  setMarkerB: (frame: number | null) => void;
  setMaxFrames: (n: number) => void;
}

export const useTimelineStore = create<TimelineState>((set, get) => ({
  currentFrame: 0,
  playing: false,
  fps: 12,
  markerA: 0,
  markerB: 1,
  maxFrames: 1,

  setCurrentFrame: (frame) => {
    const { maxFrames } = get();
    const clamped = Math.max(0, Math.min(Math.max(0, maxFrames - 1), frame));
    set({ currentFrame: clamped });
  },

  setPlaying: (playing) => set({ playing }),

  togglePlay: () => set((state) => ({ playing: !state.playing })),

  setFps: (fps) => set({ fps }),

  stepFrame: (delta) => {
    const { currentFrame, maxFrames } = get();
    if (maxFrames <= 1) return;
    const next = (currentFrame + delta + maxFrames) % maxFrames;
    set({ currentFrame: next });
  },

  setMarkerA: (markerA) => set({ markerA }),
  setMarkerB: (markerB) => set({ markerB }),
  setMaxFrames: (maxFrames) =>
    set((state) => ({
      maxFrames: Math.max(1, maxFrames),
      currentFrame: Math.min(state.currentFrame, Math.max(0, maxFrames - 1)),
    })),
}));
