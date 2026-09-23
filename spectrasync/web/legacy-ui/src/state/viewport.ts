import { create } from "zustand";

export const ZOOM_STEPS = [
  0.0625, 0.125, 0.25, 0.333, 0.5, 0.667, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 8.0, 12.0, 16.0, 32.0
];

interface ViewportState {
  zoom: number;
  cx: number;
  cy: number;
  imgW: number;
  imgH: number;

  setImageSize: (w: number, h: number) => void;
  setZoom: (zoom: number) => void;
  setCenter: (cx: number, cy: number) => void;
  panBy: (screenDx: number, screenDy: number) => void;
  zoomAt: (screenX: number, screenY: number, factor: number, paneW: number, paneH: number) => void;
  stepZoom: (direction: 1 | -1, screenX?: number, screenY?: number, paneW?: number, paneH?: number) => void;
  fit: (paneW?: number, paneH?: number) => void;
  reset100: (paneW?: number, paneH?: number) => void;
}

export const useViewportStore = create<ViewportState>((set, get) => ({
  zoom: 1.0,
  cx: 256,
  cy: 256,
  imgW: 512,
  imgH: 512,

  setImageSize: (w, h) => {
    const prevW = get().imgW;
    const prevH = get().imgH;
    if (prevW !== w || prevH !== h) {
      set({ imgW: w, imgH: h });
    }
  },

  setZoom: (zoom) => set({ zoom: Math.max(0.05, Math.min(32.0, zoom)) }),
  setCenter: (cx, cy) => set({ cx, cy }),

  panBy: (screenDx, screenDy) => {
    const { cx, cy, zoom } = get();
    set({
      cx: cx - screenDx / zoom,
      cy: cy - screenDy / zoom,
    });
  },

  zoomAt: (screenX, screenY, factor, paneW, paneH) => {
    const { zoom, cx, cy } = get();
    const newZoom = Math.max(0.05, Math.min(32.0, zoom * factor));
    if (newZoom === zoom) return;

    // Image space coordinate currently under (screenX, screenY)
    const imgX = cx + (screenX - paneW / 2) / zoom;
    const imgY = cy + (screenY - paneH / 2) / zoom;

    // Adjust cx, cy so imgX, imgY remains under screenX, screenY at newZoom
    const newCx = imgX - (screenX - paneW / 2) / newZoom;
    const newCy = imgY - (screenY - paneH / 2) / newZoom;

    set({ zoom: newZoom, cx: newCx, cy: newCy });
  },

  stepZoom: (direction, screenX, screenY, paneW, paneH) => {
    const { zoom } = get();
    let targetZoom = zoom;

    if (direction > 0) {
      targetZoom = ZOOM_STEPS.find((s) => s > zoom * 1.01) ?? ZOOM_STEPS[ZOOM_STEPS.length - 1];
    } else {
      const reversed = [...ZOOM_STEPS].reverse();
      targetZoom = reversed.find((s) => s < zoom * 0.99) ?? ZOOM_STEPS[0];
    }

    if (screenX !== undefined && screenY !== undefined && paneW && paneH) {
      get().zoomAt(screenX, screenY, targetZoom / zoom, paneW, paneH);
    } else {
      set({ zoom: targetZoom });
    }
  },

  fit: (paneW = 800, paneH = 600) => {
    const { imgW, imgH } = get();
    const w = imgW || 512;
    const h = imgH || 512;
    const fitZoom = Math.min(paneW / w, paneH / h) * 0.95;
    set({
      zoom: Math.max(0.05, Math.min(32.0, fitZoom)),
      cx: w / 2,
      cy: h / 2,
    });
  },

  reset100: () => {
    const { imgW, imgH } = get();
    set({
      zoom: 1.0,
      cx: (imgW || 512) / 2,
      cy: (imgH || 512) / 2,
    });
  },
}));
