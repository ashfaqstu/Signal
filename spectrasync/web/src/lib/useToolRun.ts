import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ApiError } from "../api/client";
import { runWorkspace, useMedia } from "../api/queries";
import type { MediaItem } from "../api/types";
import { useStudio } from "../state/studio";
import type { ToolDef, ToolInput } from "../tools/types";
import { heroUrl, thumbnail } from "../tools/views";

export interface RunState {
  running: boolean;
  error: ApiError | null;
  run: () => void;
}

/** Last request body sent per tool, so revisiting a tool does not re-run it. */
const lastBody: Record<string, string> = {};

function missingFiles(tool: ToolDef, input: ToolInput, media: MediaItem[]): boolean {
  if (input.source !== "files") return false;
  const picked = input.mediaIds.map((id) => media.find((m) => m.id === id)).filter(Boolean) as MediaItem[];
  if (picked.some((m) => m.kind === "video")) return false;
  return picked.length < tool.minFiles;
}

export function useToolRun(tool: ToolDef): RunState {
  const { params, input } = useStudio((s) => s.tools[tool.id]);
  const setResult = useStudio((s) => s.setResult);
  const addHistory = useStudio((s) => s.addHistory);
  const media = useMedia().data;

  const [running, setRunning] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const abort = useRef<AbortController | null>(null);

  const body = useMemo(
    () => (media ? JSON.stringify(tool.request(params, input, media)) : null),
    [tool, params, input, media],
  );
  const blocked = media ? missingFiles(tool, input, media) : false;

  const execute = useCallback(async () => {
    if (!body) return;
    abort.current?.abort();
    const ctrl = new AbortController();
    abort.current = ctrl;
    setRunning(true);
    setError(null);
    try {
      const r = await runWorkspace(tool.id, JSON.parse(body), ctrl.signal);
      if (ctrl.signal.aborted) return;
      lastBody[tool.id] = body;
      setResult(tool.id, r);
      const url = heroUrl(tool, r);
      const gain = r.readouts.find((o) => o.key === "gain");
      addHistory({
        id: r.runId,
        tool: tool.id,
        at: Date.now(),
        thumb: url ? await thumbnail(url) : null,
        headline: tool
          .headline(r, 0)
          .slice(0, 2)
          .map((m) => m.value)
          .join("  ·  "),
        frames: r.frames.length || 2,
        elapsedMs: r.elapsedMs,
        gainDb: gain && typeof gain.value === "number" ? gain.value : null,
      });
    } catch (e) {
      if (ctrl.signal.aborted) return;
      setError(e instanceof ApiError ? e : new ApiError(0, { code: "offline" }));
    } finally {
      if (abort.current === ctrl) setRunning(false);
    }
  }, [body, tool, setResult, addHistory]);

  useEffect(() => {
    if (!body) return;
    if (blocked) {
      abort.current?.abort();
      setRunning(false);
      setError(new ApiError(0, { code: "choose_files" }));
      return;
    }
    if (lastBody[tool.id] === body && useStudio.getState().results[tool.id]) {
      setError(null);
      return;
    }
    const t = window.setTimeout(execute, 350);
    return () => window.clearTimeout(t);
  }, [body, blocked, execute, tool.id]);

  useEffect(() => () => abort.current?.abort(), []);

  return { running, error, run: execute };
}
