import React, { useRef, useEffect } from "react";
import clsx from "clsx";
import styles from "./Viewer.module.css";
import { useViewportStore } from "../state/viewport";
import { useViewportGestures } from "./useViewportGestures";
import { MarkerLayer } from "./MarkerLayer";
import { Marker } from "../api/types";

export interface PaneProps {
  layerUrl?: string;
  layerName: string;
  markers?: Marker[];
  width?: number;
  height?: number;
  onProbeClick?: (x: number, y: number) => void;
  className?: string;
}

export const Pane: React.FC<PaneProps> = ({
  layerUrl,
  layerName,
  markers = [],
  width = 512,
  height = 512,
  onProbeClick,
  className,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const zoom = useViewportStore((s) => s.zoom);
  const cx = useViewportStore((s) => s.cx);
  const cy = useViewportStore((s) => s.cy);
  const setImageSize = useViewportStore((s) => s.setImageSize);

  useEffect(() => {
    if (width && height) {
      setImageSize(width, height);
    }
  }, [width, height, setImageSize]);

  const gestures = useViewportGestures(containerRef, layerUrl, onProbeClick);

  const [paneDimensions, setPaneDimensions] = React.useState({ w: 800, h: 600 });

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

  return (
    <div
      ref={containerRef}
      className={clsx(styles.pane, className)}
      onWheel={gestures.handleWheel}
      onPointerDown={gestures.handlePointerDown}
      onPointerMove={gestures.handlePointerMove}
      onPointerUp={gestures.handlePointerUp}
      onPointerLeave={gestures.handlePointerLeave}
    >
      <div
        className={styles.imageTransformWrapper}
        style={{
          transform: `translate(${tx}px, ${ty}px) scale(${zoom})`,
          transformOrigin: "0 0",
          width: width,
          height: height,
        }}
      >
        {layerUrl ? (
          <img
            src={layerUrl}
            alt={layerName}
            decoding="async"
            className={clsx(styles.layerImage, isPixelated && styles.pixelated)}
            style={{ width, height }}
            draggable={false}
          />
        ) : (
          <div className={styles.placeholderBox} style={{ width, height }} />
        )}

        <MarkerLayer
          markers={markers}
          layerName={layerName}
          width={width}
          height={height}
        />
      </div>

      <div className={styles.paneOverlayTag}>{layerName}</div>
    </div>
  );
};
