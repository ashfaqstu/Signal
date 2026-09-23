import React from "react";
import clsx from "clsx";
import styles from "./Timeline.module.css";
import { FrameRef, VideoFrameItem } from "../api/types";
import { useTimelineStore } from "../state/timeline";

export interface FilmStripProps {
  frames?: FrameRef[];
  previews?: VideoFrameItem[];
  frameLayer?: string;
  showMarkersAB?: boolean;
}

export const FilmStrip: React.FC<FilmStripProps> = ({
  frames = [],
  previews = [],
  frameLayer = "frame",
  showMarkersAB = false,
}) => {
  const currentFrame = useTimelineStore((s) => s.currentFrame);
  const setCurrentFrame = useTimelineStore((s) => s.setCurrentFrame);
  const markerA = useTimelineStore((s) => s.markerA);
  const markerB = useTimelineStore((s) => s.markerB);
  const setMarkerA = useTimelineStore((s) => s.setMarkerA);
  const setMarkerB = useTimelineStore((s) => s.setMarkerB);

  const items = frames.length > 0 ? frames : previews;

  return (
    <div className={styles.filmstripWrapper}>
      <div className={styles.filmstripTrack}>
        {items.map((item, idx) => {
          let thumbUrl = "";
          if ("layers" in item) {
            thumbUrl = item.layers[frameLayer] || Object.values(item.layers)[0] || "";
          } else {
            thumbUrl = item.thumbUrl;
          }

          const isSelected = currentFrame === idx;
          const isMarkerA = markerA === idx;
          const isMarkerB = markerB === idx;

          return (
            <div
              key={idx}
              className={clsx(
                styles.filmstripItem,
                isSelected && styles.filmstripItemSelected
              )}
              onClick={() => setCurrentFrame(idx)}
            >
              {thumbUrl ? (
                <img src={thumbUrl} alt={`Frame ${idx + 1}`} className={styles.filmThumb} />
              ) : (
                <div className={styles.filmThumbPlaceholder} />
              )}

              <span className={clsx(styles.frameNumber, "tabular-nums")}>{idx + 1}</span>

              {showMarkersAB && (
                <div className={styles.abMarkersContainer} onClick={(e) => e.stopPropagation()}>
                  <button
                    type="button"
                    className={clsx(styles.markerFlag, isMarkerA && styles.markerActiveA)}
                    onClick={() => setMarkerA(idx)}
                    title="Set Marker A"
                  >
                    A
                  </button>
                  <button
                    type="button"
                    className={clsx(styles.markerFlag, isMarkerB && styles.markerActiveB)}
                    onClick={() => setMarkerB(idx)}
                    title="Set Marker B"
                  >
                    B
                  </button>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
