import {
  BarChart3,
  ChevronDown,
  Download,
  Film,
  Home,
  ImageDown,
  Images,
  Monitor,
  Moon,
  SlidersHorizontal,
  Sun,
  X,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useStudio } from "../state/studio";
import { go } from "../lib/router";
import { useToolRun } from "../lib/useToolRun";
import { TOOLS } from "../tools/catalog";
import type { ToolDef } from "../tools/types";
import { availableViews } from "../tools/views";
import { Button, Menu, MenuItem, Spinner, ToolBadge, cx } from "../ui";
import { AdjustPanel } from "./AdjustPanel";
import s from "./Editor.module.css";
import { InsightsPanel } from "./InsightsPanel";
import { MediaPanel } from "./MediaPanel";
import { Stage, currentImage } from "./Stage";

type Panel = "adjust" | "media" | "insights";

const PANELS: { id: Panel; label: string; icon: typeof Images }[] = [
  { id: "adjust", label: "Adjust", icon: SlidersHorizontal },
  { id: "media", label: "Media", icon: Images },
  { id: "insights", label: "Insights", icon: BarChart3 },
];

function ThemeCycle() {
  const theme = useStudio((st) => st.theme);
  const setTheme = useStudio((st) => st.setTheme);
  const next = theme === "system" ? "light" : theme === "light" ? "dark" : "system";
  const Icon = theme === "light" ? Sun : theme === "dark" ? Moon : Monitor;
  return (
    <Button variant="glass" iconOnly icon={Icon} aria-label={`Theme: ${theme}`} title={`Theme: ${theme}`} onClick={() => setTheme(next)} />
  );
}

function save(url: string, name: string) {
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
}

export function Editor({ tool }: { tool: ToolDef }) {
  const { running, error, run } = useToolRun(tool);
  const result = useStudio((st) => st.results[tool.id]);
  const nPicked = useStudio((st) => (st.tools[tool.id].input.source === "files" ? st.tools[tool.id].input.mediaIds.length : 0));
  const [panel, setPanel] = useState<Panel | null>("adjust");
  const [viewId, setViewId] = useState(tool.views[0].id);
  const [frame, setFrame] = useState(0);

  const views = useMemo(() => availableViews(tool, result), [tool, result]);
  const view = views.find((v) => v.id === viewId) ?? views[0] ?? tool.views[0];

  useEffect(() => {
    setViewId(tool.views[0].id);
    setFrame(0);
  }, [tool]);

  useEffect(() => {
    if (result && frame >= result.frames.length) setFrame(Math.floor(result.frames.length / 2));
  }, [result, frame]);

  const image = result ? currentImage(result, view, frame) : null;
  const hasSequence = Boolean(result?.frames.length);

  return (
    <div className={s.editor}>
      <header className={s.top}>
        <Button variant="glass" icon={Home} onClick={() => go("/")}>
          Home
        </Button>
        <span className={s.topSep} />
        <Menu
          trigger={(_, toggle) => (
            <button className={s.topTitle} onClick={toggle} aria-haspopup="menu">
              <ToolBadge icon={tool.icon} gradient="rgb(255 255 255 / 0.2)" size={30} radius={8} />
              {tool.name}
              <ChevronDown size={16} />
            </button>
          )}
        >
          {(close) =>
            TOOLS.map((t) => (
              <MenuItem
                key={t.id}
                icon={<ToolBadge icon={t.icon} gradient={t.gradient} size={32} radius={9} />}
                label={t.name}
                sub={t.tagline}
                onClick={() => {
                  close();
                  go(`/tool/${t.id}`);
                }}
              />
            ))
          }
        </Menu>

        <span className={s.spacer} />

        {running ? (
          <span className={s.status}>
            <Spinner />
            Processing
          </span>
        ) : result && !error ? (
          <span className={s.status} key={result.runId}>
            <span className={s.statusDot} />
            Done · {(result.elapsedMs / 1000).toFixed(2)} s
          </span>
        ) : error && error.code !== "choose_files" ? (
          <span className={s.status}>
            <span className={cx(s.statusDot, s.statusErr)} />
            Not applied
          </span>
        ) : null}

        <ThemeCycle />

        <Menu
          align="right"
          trigger={(_, toggle) => (
            <Button variant="white" icon={Download} onClick={toggle} disabled={!result || Boolean(error && !running)}>
              Download
            </Button>
          )}
        >
          {(close) => (
            <>
              {image && (
                <MenuItem
                  icon={<ImageDown size={18} />}
                  label="Image"
                  sub={`PNG · ${view.label}`}
                  onClick={() => {
                    close();
                    save(image, `${tool.id}-${view.id}.png`);
                  }}
                />
              )}
              {hasSequence && result && (
                <>
                  <MenuItem
                    icon={<Film size={18} />}
                    label="Video"
                    sub="MP4 · all frames"
                    onClick={() => {
                      close();
                      save(`/api/runs/${result.runId}/export-sequence?format=mp4&fps=12`, `${tool.id}.mp4`);
                    }}
                  />
                  <MenuItem
                    icon={<Film size={18} />}
                    label="GIF"
                    sub="Animated · all frames"
                    onClick={() => {
                      close();
                      save(`/api/runs/${result.runId}/export-sequence?format=gif&fps=10`, `${tool.id}.gif`);
                    }}
                  />
                </>
              )}
            </>
          )}
        </Menu>
      </header>

      <div className={s.body}>
        <nav className={s.rail} aria-label="Panels">
          {PANELS.map((p) => (
            <button
              key={p.id}
              className={cx(s.railBtn, panel === p.id && s.railOn)}
              onClick={() => setPanel(panel === p.id ? null : p.id)}
              aria-pressed={panel === p.id}
            >
              <span className={s.railIcon}>
                <p.icon size={21} strokeWidth={2} />
              </span>
              {p.id === "media" && nPicked > 0 && <span className={s.railBadge}>{nPicked}</span>}
              {p.label}
            </button>
          ))}
        </nav>

        <aside className={cx(s.flyout, panel && s.flyoutOpen)} aria-hidden={!panel}>
          {panel && (
            <div className={s.flyoutInner}>
              <div className={s.flyHead}>
                <span className={s.flyTitle}>{PANELS.find((p) => p.id === panel)!.label}</span>
                <Button variant="ghost" size="sm" iconOnly icon={X} aria-label="Close panel" onClick={() => setPanel(null)} />
              </div>
              <div className={s.flyBody} key={panel}>
                {panel === "adjust" && <AdjustPanel tool={tool} onChoose={() => setPanel("media")} />}
                {panel === "media" && <MediaPanel tool={tool} />}
                {panel === "insights" && <InsightsPanel tool={tool} frame={frame} />}
              </div>
            </div>
          )}
        </aside>

        <Stage
          tool={tool}
          result={result}
          views={views}
          view={view}
          setView={setViewId}
          frame={frame}
          setFrame={setFrame}
          running={running}
          error={error}
          onChoose={() => setPanel("media")}
          onRetry={run}
        />
      </div>
    </div>
  );
}
