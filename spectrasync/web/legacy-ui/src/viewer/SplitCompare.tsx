import React, { useRef, useState, useEffect } from "react";
import clsx from "clsx";
import styles from "./Viewer.module.css";
import { useViewportStore } from "../state/viewport";
import { useUiStore } from "../state/ui";
import { useViewportGestures } from "./useViewportGestures";

export interface SplitCompareProps {
  layerLeftUrl?: string;
  layerRightUrl?: string;
  layerLeftName: string;
  layerRightName: string;
  width?: number;
  height?: number;
  onProbeClick?: (x: number, y: number) => void;
  className?: string;
}

export const SplitCompare: React.FC<SplitCompareProps> = ({
  layerLeftUrl,
  layerRightUrl,
  layerLeftName,
  layerRightName,
  width = 512,
  height = 512,
  onProbeClick,
  className,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const isDraggingDividerRef = useRef(false);

  const zoom = useViewportStore((s) => s.zoom);
  const cx = useViewportStore((s) => s.cx);
  const cy = useViewportStore((s) => s.cy);
  const splitPos = useUiStore((s) => s.splitPos);
  const setSplitPos = useUiStore((s) => s.setSplitPos);

  const gestures = useViewportGestures(containerRef, layerLeftUrl, onProbeClick);

  const [paneDimensions, setPaneDimensions] = useState({ w: 800, h: 600 });

  useEffect(() => {
    const updateSize = () => {
      if (containerRef.current) {
        setPaneDimensions({
          w: containerRef.current.clientWidth,
          h: containerRef.current.clientHeight,
        });
      }
    };
    updateSize();
    window.addEventListener("resize", updateSize);
    return () => window.removeEventListener("resize", updateSize);
  }, []);

  const tx = paneDimensions.w / 2 - cx * zoom;
  const ty = paneDimensions.h / 2 - cy * zoom;
  const isPixelated = zoom >= 2.0;

  const handleDividerPointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
    e.stopPropagation();
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
    isDraggingDividerRef.current = true;
  };

  const handleDividerPointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    if (!isDraggingDividerRef.current || !containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const newPos = (e.clientX - rect.left) / rect.width;
    setSplitPos(newPos);
  };

  const handleDividerPointerUp = (e: React.PointerEvent<HTMLDivElement>) => {
    if (isDraggingDividerRef.current) {
      isDraggingDividerRef.current = false;
      try {
        (e.target as HTMLElement).releasePointerCapture(e.pointerId);
      } catch {
        // Ignore
      }
    }
  };

  const splitPx = paneDimensions.w * splitPos;

  return (
    <div
      ref={containerRef}
      className={clsx(styles.pane, styles.splitPane, className)}
      onWheel={gestures.handleWheel}
      onPointerDown={gestures.handlePointerDown}
      onPointerMove={gestures.handlePointerMove}
      onPointerUp={gestures.handlePointerUp}
      onPointerLeave={gestures.handlePointerLeave}
    >
      {/* Left Layer (Full viewport, clipped to left of split) */}
      <div
        className={styles.splitClipLeft}
        style={{ width: `${splitPos * 100}%` }}
      >
        <div
          className={styles.imageTransformWrapper}
          style={{
            transform: `translate(${tx}px, ${ty}px) scale(${zoom})`,
            transformOrigin: "0 0",
            width,
            height,
          }}
        >
          {layerLeftUrl && (
            <img
              src={layerLeftUrl}
              alt={layerLeftName}
              decoding="async"
              className={clsx(styles.layerImage, isPixelated && styles.pixelated)}
              style={{ width, height }}
              draggable={false}
            />
          )}
        </div>
      </div>

      {/* Right Layer (Full viewport, clipped to right of split) */}
      <div
        className={styles.splitClipRight}
        style={{ left: `${splitPos * 100}%` }}
      >
        <div
          className={styles.imageTransformWrapper}
          style={{
            transform: `translate(${tx - splitPx}px, ${ty}px) scale(${zoom})`,
            transformOrigin: "0 0",
            width,
            height,
          }}
        >
          {layerRightUrl && (
            <img
              src={layerRightUrl}
              alt={layerRightName}
              decoding="async"
              className={clsx(styles.layerImage, isPixelated && styles.pixelated)}
              style={{ width, height }}
              draggable={false}
            />
          )}
        </div>
      </div>

      {/* Draggable Divider */}
      <div
        className={styles.splitDivider}
        style={{ left: `${splitPos * 100}%` }}
        onPointerDown={handleDividerPointerDown}
        onPointerMove={handleDividerPointerMove}
        onPointerUp={handleDividerPointerUp}
      >
        <div className={styles.splitHandle} />
      </div>

      <div className={styles.splitLeftTag}>{layerLeftName}</div>
      <div className={styles.splitRightTag}>{layerRightName}</div>
    </div>
  );
};
