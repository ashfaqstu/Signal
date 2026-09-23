import React, { useEffect } from "react";
import clsx from "clsx";
import {
  Play,
  Pause,
  SkipBack,
  SkipForward,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import styles from "./Timeline.module.css";
import { useTimelineStore } from "../state/timeline";
import { IconButton } from "../controls/IconButton";
import { Segmented } from "../controls/Segmented";

export const Transport: React.FC = () => {
  const currentFrame = useTimelineStore((s) => s.currentFrame);
  const playing = useTimelineStore((s) => s.playing);
  const fps = useTimelineStore((s) => s.fps);
  const maxFrames = useTimelineStore((s) => s.maxFrames);
  const togglePlay = useTimelineStore((s) => s.togglePlay);
  const setPlaying = useTimelineStore((s) => s.setPlaying);
  const stepFrame = useTimelineStore((s) => s.stepFrame);
  const setCurrentFrame = useTimelineStore((s) => s.setCurrentFrame);
  const setFps = useTimelineStore((s) => s.setFps);

  // Playback timer
  useEffect(() => {
    if (!playing || maxFrames <= 1) return;

    const interval = 1000 / fps;
    const timer = setInterval(() => {
      stepFrame(1);
    }, interval);

    return () => clearInterval(timer);
  }, [playing, fps, maxFrames, stepFrame]);

  // J/K/L and arrow keyboard shortcuts for playback
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable) {
        return;
      }

      if (e.key === " " && !e.ctrlKey && !e.metaKey && !e.altKey) {
        // Space toggle play/pause when timeline is active
        e.preventDefault();
        togglePlay();
      } else if (e.key === "k" || e.key === "K") {
        setPlaying(false);
      } else if (e.key === "l" || e.key === "L") {
        setPlaying(true);
      } else if (e.key === "j" || e.key === "J") {
        stepFrame(-1);
      } else if (e.key === "ArrowLeft") {
        e.preventDefault();
        stepFrame(-1);
      } else if (e.key === "ArrowRight") {
        e.preventDefault();
        stepFrame(1);
      } else if (e.key === "Home") {
        e.preventDefault();
        setCurrentFrame(0);
      } else if (e.key === "End") {
        e.preventDefault();
        setCurrentFrame(Math.max(0, maxFrames - 1));
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [togglePlay, setPlaying, stepFrame, setCurrentFrame, maxFrames]);

  const frameStr = String(currentFrame + 1).padStart(2, "0");
  const totalStr = String(maxFrames).padStart(2, "0");

  return (
    <div className={styles.transportContainer}>
      <div className={styles.transportButtons}>
        <IconButton
          size="sm"
          icon={<SkipBack size={12} />}
          onClick={() => setCurrentFrame(0)}
          tooltip="Go to start (Home)"
        />
        <IconButton
          size="sm"
          icon={<ChevronLeft size={14} />}
          onClick={() => stepFrame(-1)}
          tooltip="Step frame back (←, J)"
        />
        <IconButton
          size="md"
          icon={playing ? <Pause size={14} /> : <Play size={14} />}
          onClick={togglePlay}
          active={playing}
          tooltip="Play/Pause (Space, K/L)"
        />
        <IconButton
          size="sm"
          icon={<ChevronRight size={14} />}
          onClick={() => stepFrame(1)}
          tooltip="Step frame forward (→)"
        />
        <IconButton
          size="sm"
          icon={<SkipForward size={12} />}
          onClick={() => setCurrentFrame(maxFrames - 1)}
          tooltip="Go to end (End)"
        />
      </div>

      <div className={clsx(styles.timecodeDisplay, "tabular-nums")}>
        <span className={styles.timecodeCurrent}>00:{frameStr}</span>
        <span className={styles.timecodeSep}>/</span>
        <span className={styles.timecodeTotal}>00:{totalStr}</span>
      </div>

      <div className={styles.fpsSelector}>
        <Segmented
          options={[
            { value: "6", label: "6" },
            { value: "12", label: "12" },
            { value: "24", label: "24" },
          ]}
          value={String(fps)}
          onChange={(v) => setFps(parseInt(v, 10))}
        />
      </div>
    </div>
  );
};
