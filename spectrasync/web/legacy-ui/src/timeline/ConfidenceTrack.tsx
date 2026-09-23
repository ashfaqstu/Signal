import React from "react";
import styles from "./Timeline.module.css";
import { FrameRef } from "../api/types";
import { useUiStore } from "../state/ui";

export interface ConfidenceTrackProps {
  frames: FrameRef[];
}

export const ConfidenceTrack: React.FC<ConfidenceTrackProps> = ({ frames }) => {
  const activeWorkspace = useUiStore((s) => s.activeWorkspace);

  if (frames.length === 0) return null;

  const getColor = (f: FrameRef) => {
    const meta = f.meta || {};

    if (activeWorkspace === "highlight") {
      const count = meta.objects;
      if (count !== undefined && count > 0) return "var(--ok)";
      return "var(--text-3)";
    }

    const conf = meta.confidence;
    if (conf === null || conf === undefined) return "var(--text-3)";
    if (conf >= 2.0) return "var(--ok)";
    if (conf >= 1.2) return "var(--warn)";
    return "var(--bad)";
  };

  return (
    <div className={styles.confidenceTrack}>
      {frames.map((f) => (
        <div
          key={f.index}
          className={styles.confidenceSegment}
          style={{ backgroundColor: getColor(f) }}
          title={`Frame ${f.index + 1}: ${
            activeWorkspace === "highlight"
              ? `${f.meta?.objects ?? 0} objects`
              : `Confidence ${f.meta?.confidence?.toFixed(2) ?? "ref"}`
          }`}
        />
      ))}
    </div>
  );
};
