import React from "react";
import clsx from "clsx";
import styles from "./Shell.module.css";
import { useViewportStore } from "../state/viewport";
import { useUiStore } from "../state/ui";
import { useParamsStore } from "../state/params";

export const StatusBar: React.FC = () => {
  const zoom = useViewportStore((s) => s.zoom);
  const imgW = useViewportStore((s) => s.imgW);
  const imgH = useViewportStore((s) => s.imgH);

  const activeWorkspace = useUiStore((s) => s.activeWorkspace);
  const cursorPos = useUiStore((s) => s.cursorPos);
  const probePixel = useUiStore((s) => s.probePixel);
  const running = useUiStore((s) => s.running);

  const result = useParamsStore((s) => s.results[activeWorkspace]);

  const zoomPercent = `${Math.round(zoom * 100)}%`;

  const renderPixelValue = () => {
    if (!probePixel) return null;
    if (probePixel.isRgb) {
      return (
        <span className={styles.statusSegment}>
          R {probePixel.r.toFixed(2)} G {probePixel.g.toFixed(2)} B {probePixel.b.toFixed(2)}
        </span>
      );
    }
    return (
      <span className={styles.statusSegment}>
        {probePixel.gray.toFixed(3)}
      </span>
    );
  };

  return (
    <div className={styles.statusBar}>
      <div className={styles.statusLeft}>
        <span className={clsx(styles.statusSegment, "tabular-nums")}>{zoomPercent}</span>
        <span className={styles.statusDivider}>|</span>
        <span className={clsx(styles.statusSegment, "tabular-nums")}>
          {imgW} × {imgH}
        </span>
        {cursorPos && (
          <>
            <span className={styles.statusDivider}>|</span>
            <span className={clsx(styles.statusSegment, "tabular-nums")}>
              x {cursorPos.x} &nbsp; y {cursorPos.y}
            </span>
          </>
        )}
        {renderPixelValue() && (
          <>
            <span className={styles.statusDivider}>|</span>
            {renderPixelValue()}
          </>
        )}
      </div>

      <div className={styles.statusRight}>
        {running ? (
          <span className={styles.statusRunning}>Running…</span>
        ) : result ? (
          <span className={clsx(styles.statusDone, "tabular-nums")}>
            Done · {(result.elapsedMs / 1000).toFixed(2)} s
          </span>
        ) : (
          <span className={styles.statusReady}>Ready</span>
        )}
      </div>
    </div>
  );
};
