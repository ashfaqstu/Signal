import React, { useEffect } from "react";
import styles from "./Timeline.module.css";
import { useUiStore } from "../state/ui";
import { useParamsStore } from "../state/params";
import { useTimelineStore } from "../state/timeline";
import { getWorkspaceDef } from "../workspaces";
import { Transport } from "./Transport";
import { ConfidenceTrack } from "./ConfidenceTrack";
import { FilmStrip } from "./FilmStrip";
import { Playhead } from "./Playhead";
import { useVideoFrames } from "../api/queries";

export const Timeline: React.FC = () => {
  const activeWorkspace = useUiStore((s) => s.activeWorkspace);
  const result = useParamsStore((s) => s.results[activeWorkspace]);
  const params = useParamsStore((s) => (s.params as any)[activeWorkspace] || {});
  const setMaxFrames = useTimelineStore((s) => s.setMaxFrames);
  const setParam = useParamsStore((s) => s.setParam);

  const def = getWorkspaceDef(activeWorkspace);

  const isVideoSource = params.source === "video";
  const showTimeline =
    def.sequence === "always" || (def.sequence === "whenVideo" && isVideoSource);

  const frames = result?.frames || [];
  const { data: videoPreviews } = useVideoFrames(
    isVideoSource ? params.mediaId : undefined,
    params.frames || 24,
    params.step || 1
  );

  const totalFrames = frames.length > 0 ? frames.length : videoPreviews?.length || 0;

  useEffect(() => {
    if (totalFrames > 0) {
      setMaxFrames(totalFrames);
    }
  }, [totalFrames, setMaxFrames]);

  // Sync timeline A/B markers with workspace video parameters
  const markerA = useTimelineStore((s) => s.markerA);
  const markerB = useTimelineStore((s) => s.markerB);

  useEffect(() => {
    if (isVideoSource && (activeWorkspace === "align" || activeWorkspace === "rotate")) {
      if (markerA !== null && markerA !== params.aIndex) {
        setParam(activeWorkspace as any, "aIndex", markerA);
      }
      if (markerB !== null && markerB !== params.bIndex) {
        setParam(activeWorkspace as any, "bIndex", markerB);
      }
    }
  }, [markerA, markerB, isVideoSource, activeWorkspace, params.aIndex, params.bIndex, setParam]);

  if (!showTimeline) return null;

  return (
    <div className={styles.timelineContainer}>
      <div className={styles.timelineHeader}>
        <Transport />
      </div>

      <div className={styles.timelineBody}>
        {frames.length > 0 && <ConfidenceTrack frames={frames} />}
        <div className={styles.filmstripContainer}>
          <FilmStrip
            frames={frames}
            previews={videoPreviews}
            frameLayer={def.frameLayer || "frame"}
            showMarkersAB={isVideoSource && (activeWorkspace === "align" || activeWorkspace === "rotate")}
          />
          <Playhead totalFrames={totalFrames} />
        </div>
      </div>
    </div>
  );
};
