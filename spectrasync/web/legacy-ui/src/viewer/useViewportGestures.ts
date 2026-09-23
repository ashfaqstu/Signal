import { useRef, useCallback } from "react";
import { useViewportStore } from "../state/viewport";
import { useUiStore } from "../state/ui";
import { readPixelFromUrl } from "./probe";

export function useViewportGestures(
  containerRef: React.RefObject<HTMLDivElement>,
  currentLayerUrl?: string,
  onProbeClick?: (x: number, y: number) => void
) {
  const isDraggingRef = useRef(false);
  const lastMousePosRef = useRef({ x: 0, y: 0 });

  const zoomAt = useViewportStore((s) => s.zoomAt);
  const panBy = useViewportStore((s) => s.panBy);
  const zoom = useViewportStore((s) => s.zoom);
  const cx = useViewportStore((s) => s.cx);
  const cy = useViewportStore((s) => s.cy);
  const imgW = useViewportStore((s) => s.imgW);
  const imgH = useViewportStore((s) => s.imgH);

  const activeTool = useUiStore((s) => s.activeTool);
  const setProbePixel = useUiStore((s) => s.setProbePixel);
  const setCursorPos = useUiStore((s) => s.setCursorPos);

  const getImageCoords = useCallback(
    (screenX: number, screenY: number, paneW: number, paneH: number) => {
      const ix = cx + (screenX - paneW / 2) / zoom;
      const iy = cy + (screenY - paneH / 2) / zoom;
      return { x: ix, y: iy };
    },
    [cx, cy, zoom]
  );

  const handleWheel = useCallback(
    (e: React.WheelEvent<HTMLDivElement>) => {
      e.preventDefault();
      if (!containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const screenX = e.clientX - rect.left;
      const screenY = e.clientY - rect.top;
      const factor = e.deltaY < 0 ? 1.15 : 1 / 1.15;
      zoomAt(screenX, screenY, factor, rect.width, rect.height);
    },
    [containerRef, zoomAt]
  );

  const handlePointerDown = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      if (!containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const screenX = e.clientX - rect.left;
      const screenY = e.clientY - rect.top;

      if (activeTool === "zoom") {
        const factor = e.altKey ? 1 / 1.5 : 1.5;
        zoomAt(screenX, screenY, factor, rect.width, rect.height);
        return;
      }

      if (activeTool === "probe") {
        const { x, y } = getImageCoords(screenX, screenY, rect.width, rect.height);
        if (x >= 0 && x < imgW && y >= 0 && y < imgH) {
          onProbeClick?.(Math.floor(x), Math.floor(y));
        }
        return;
      }

      // Hand tool or Space+drag
      (e.target as HTMLElement).setPointerCapture(e.pointerId);
      isDraggingRef.current = true;
      lastMousePosRef.current = { x: e.clientX, y: e.clientY };
    },
    [activeTool, containerRef, getImageCoords, imgW, imgH, onProbeClick, zoomAt]
  );

  const handlePointerMove = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      if (!containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const screenX = e.clientX - rect.left;
      const screenY = e.clientY - rect.top;

      const { x, y } = getImageCoords(screenX, screenY, rect.width, rect.height);
      const ix = Math.floor(x);
      const iy = Math.floor(y);

      if (ix >= 0 && ix < imgW && iy >= 0 && iy < imgH) {
        setCursorPos({ x: ix, y: iy });
        if (currentLayerUrl) {
          readPixelFromUrl(currentLayerUrl, ix, iy).then((p) => {
            if (p) setProbePixel(p);
          });
        }
      } else {
        setCursorPos(null);
        setProbePixel(null);
      }

      if (isDraggingRef.current) {
        const dx = e.clientX - lastMousePosRef.current.x;
        const dy = e.clientY - lastMousePosRef.current.y;
        lastMousePosRef.current = { x: e.clientX, y: e.clientY };
        panBy(dx, dy);
      }
    },
    [containerRef, currentLayerUrl, getImageCoords, imgW, imgH, panBy, setCursorPos, setProbePixel]
  );

  const handlePointerUp = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      if (isDraggingRef.current) {
        isDraggingRef.current = false;
        try {
          (e.target as HTMLElement).releasePointerCapture(e.pointerId);
        } catch {
          // Ignore
        }
      }
    },
    []
  );

  const handlePointerLeave = useCallback(() => {
    setCursorPos(null);
    setProbePixel(null);
  }, [setCursorPos, setProbePixel]);

  return {
    handleWheel,
    handlePointerDown,
    handlePointerMove,
    handlePointerUp,
    handlePointerLeave,
  };
}
