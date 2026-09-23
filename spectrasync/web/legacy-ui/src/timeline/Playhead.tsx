import React, { useRef } from "react";
import styles from "./Timeline.module.css";
import { useTimelineStore } from "../state/timeline";

export interface PlayheadProps {
  totalFrames: number;
}

export const Playhead: React.FC<PlayheadProps> = ({ totalFrames }) => {
  const currentFrame = useTimelineStore((s) => s.currentFrame);
  const isDraggingRef = useRef(false);

  if (totalFrames <= 0) return null;

  const handlePointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
    isDraggingRef.current = true;
  };

  const handlePointerUp = (e: React.PointerEvent<HTMLDivElement>) => {
    if (isDraggingRef.current) {
      isDraggingRef.current = false;
      try {
        (e.target as HTMLElement).releasePointerCapture(e.pointerId);
      } catch {
        // Ignore
      }
    }
  };

  // 60px item width + 4px gap = 64px per frame
  const itemWidth = 64;
  const leftPos = currentFrame * itemWidth + itemWidth / 2;

  return (
    <div
      className={styles.playhead}
      style={{ left: `${leftPos}px` }}
      onPointerDown={handlePointerDown}
      onPointerUp={handlePointerUp}
    >
      <div className={styles.playheadHead} />
      <div className={styles.playheadLine} />
    </div>
  );
};
