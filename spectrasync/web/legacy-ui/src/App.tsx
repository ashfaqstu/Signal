import React, { useEffect, useRef, useCallback } from "react";
import { Shell } from "./shell/Shell";
import { useUiStore } from "./state/ui";
import { useParamsStore } from "./state/params";
import { useViewportStore } from "./state/viewport";
import { useTimelineStore } from "./state/timeline";
import { useMedia, useRegistries, runWorkspace } from "./api/queries";
import { WORKSPACES } from "./workspaces";

export const App: React.FC = () => {
  const activeWorkspace = useUiStore((s) => s.activeWorkspace);
  const setActiveWorkspace = useUiStore((s) => s.setActiveWorkspace);
  const setRunning = useUiStore((s) => s.setRunning);
  const paneLayers = useUiStore((s) => s.paneLayers);
  const setPaneLayers = useUiStore((s) => s.setPaneLayers);

  const params = useParamsStore((s) => s.params);
  const setParam = useParamsStore((s) => s.setParam);
  const setResult = useParamsStore((s) => s.setResult);
  const setError = useParamsStore((s) => s.setError);

  const setImageSize = useViewportStore((s) => s.setImageSize);
  const fit = useViewportStore((s) => s.fit);
  const reset100 = useViewportStore((s) => s.reset100);

  const playing = useTimelineStore((s) => s.playing);
  const fps = useTimelineStore((s) => s.fps);
  const stepFrame = useTimelineStore((s) => s.stepFrame);
  const setCurrentFrame = useTimelineStore((s) => s.setCurrentFrame);
  const setMaxFrames = useTimelineStore((s) => s.setMaxFrames);
  const maxFrames = useTimelineStore((s) => s.maxFrames);
  const togglePlay = useTimelineStore((s) => s.togglePlay);

  const { data: mediaList } = useMedia();
  useRegistries(); // Preload registries cache

  const abortControllerRef = useRef<AbortController | null>(null);
  const debounceTimerRef = useRef<number | null>(null);
  const initialMediaPopulated = useRef<boolean>(false);

  // Auto-populate default sample media if available and params have empty IDs
  useEffect(() => {
    if (!mediaList || mediaList.length === 0 || initialMediaPopulated.current) return;
    initialMediaPopulated.current = true;

    const findMedia = (prefix: string) =>
      mediaList.find((m) => m.name.toLowerCase().includes(prefix.toLowerCase()))?.id || "";

    const cameraman = findMedia("cameraman") || mediaList[0]?.id || "";
    const mandrill = findMedia("mandrill") || mediaList[1]?.id || cameraman;
    const streetLight1 = findMedia("street_light_1") || mediaList[0]?.id || "";
    const streetLight2 = findMedia("street_light_2") || mediaList[1]?.id || streetLight1;
    const walkClean = findMedia("walk_clean") || findMedia("walk") || mediaList[0]?.id || "";
    const photoIds = mediaList.filter((m) => m.kind === "image").map((m) => m.id);

    // Default alignments
    if (!params.align.aId && streetLight1) setParam("align", "aId", streetLight1);
    if (!params.align.bId && streetLight2) setParam("align", "bId", streetLight2);
    if (!params.align.baseId && cameraman) setParam("align", "baseId", cameraman);

    // Default rotate
    if (!params.rotate.aId && mandrill) setParam("rotate", "aId", mandrill);
    if (!params.rotate.bId && mandrill) setParam("rotate", "bId", mandrill);
    if (!params.rotate.baseId && cameraman) setParam("rotate", "baseId", cameraman);

    // Default stack
    if (params.stack.mediaIds.length === 0 && photoIds.length > 0) {
      setParam("stack", "mediaIds", photoIds.slice(0, 16));
    }
    if (!params.stack.cleanId && walkClean) setParam("stack", "cleanId", walkClean);
    if (!params.stack.baseId && cameraman) setParam("stack", "baseId", cameraman);

    // Default remove
    if (params.remove.mediaIds.length === 0 && photoIds.length > 0) {
      setParam("remove", "mediaIds", photoIds.slice(0, 12));
    }
    if (!params.remove.baseId && cameraman) setParam("remove", "baseId", cameraman);

    // Default highlight
    if (params.highlight.mediaIds.length === 0 && photoIds.length > 0) {
      setParam("highlight", "mediaIds", photoIds.slice(0, 12));
    }
    if (!params.highlight.baseId && cameraman) setParam("highlight", "baseId", cameraman);

    // Default spectrum
    if (!params.spectrum.baseId && cameraman) setParam("spectrum", "baseId", cameraman);
  }, [mediaList, params, setParam]);

  // Execute workspace runner
  const executeRun = useCallback(
    async (ws: string) => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      const controller = new AbortController();
      abortControllerRef.current = controller;

      setRunning(true);
      const currentParams = params[ws as keyof typeof params];

      try {
        const res = await runWorkspace(ws, currentParams, controller.signal);
        setResult(ws, res);

        // Update viewport dimensions
        if (res.layers && res.layers.length > 0) {
          const firstLayer = res.layers[0];
          setImageSize(firstLayer.width, firstLayer.height);

          // If current pane layers are empty or default to non-existent layer, reset
          const availableNames = res.layers.map((l) => l.name);
          if (paneLayers.length === 0 || !availableNames.includes(paneLayers[0])) {
            setPaneLayers(availableNames);
          }
        }

        // Update timeline max frames if sequence
        if (res.frames && res.frames.length > 0) {
          setMaxFrames(res.frames.length);
        } else {
          setMaxFrames(1);
        }

        setRunning(false);
      } catch (err: any) {
        if (err.name === "AbortError") {
          return; // Ignore aborted requests
        }
        setError(ws, err);
        setRunning(false);
      }
    },
    [params, setRunning, setResult, setError, setImageSize, paneLayers, setPaneLayers, setMaxFrames]
  );

  // Trigger debounced run on active workspace or param changes
  useEffect(() => {
    if (debounceTimerRef.current) {
      window.clearTimeout(debounceTimerRef.current);
    }
    debounceTimerRef.current = window.setTimeout(() => {
      executeRun(activeWorkspace);
    }, 250);

    return () => {
      if (debounceTimerRef.current) {
        window.clearTimeout(debounceTimerRef.current);
      }
    };
  }, [activeWorkspace, params, executeRun]);

  // Timeline playback loop
  useEffect(() => {
    if (!playing) return;
    const intervalMs = 1000 / Math.max(1, fps);
    const timer = setInterval(() => {
      stepFrame(1);
    }, intervalMs);

    return () => clearInterval(timer);
  }, [playing, fps, stepFrame]);

  // Global Keyboard Shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      const isInput = target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable;

      // Ctrl + Enter -> Run immediately
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        executeRun(activeWorkspace);
        return;
      }

      // Ctrl + 0 -> Fit
      if ((e.ctrlKey || e.metaKey) && e.key === "0") {
        e.preventDefault();
        fit();
        return;
      }

      // Ctrl + 1 -> 100% Zoom
      if ((e.ctrlKey || e.metaKey) && e.key === "1") {
        e.preventDefault();
        reset100();
        return;
      }

      // Workspace switching: Alt+1..6 or 1..6 when outside inputs
      if (e.altKey && !e.ctrlKey && !e.metaKey) {
        const num = parseInt(e.key, 10);
        if (num >= 1 && num <= 6) {
          e.preventDefault();
          const targetWs = WORKSPACES[num - 1];
          if (targetWs) setActiveWorkspace(targetWs.id);
          return;
        }
      }

      if (isInput) return;

      // Unmodified 1..6 outside inputs
      const num = parseInt(e.key, 10);
      if (num >= 1 && num <= 6 && !e.ctrlKey && !e.altKey && !e.metaKey) {
        e.preventDefault();
        const targetWs = WORKSPACES[num - 1];
        if (targetWs) setActiveWorkspace(targetWs.id);
        return;
      }

      // J / K / L Shuttle
      if (e.key === "j" || e.key === "J") {
        e.preventDefault();
        stepFrame(-1);
      } else if (e.key === "k" || e.key === "K" || e.key === " ") {
        if (e.key !== " ") {
          e.preventDefault();
          togglePlay();
        }
      } else if (e.key === "l" || e.key === "L") {
        e.preventDefault();
        stepFrame(1);
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
        setCurrentFrame(maxFrames - 1);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [activeWorkspace, executeRun, fit, reset100, setActiveWorkspace, stepFrame, togglePlay, setCurrentFrame, maxFrames]);

  return <Shell />;
};
