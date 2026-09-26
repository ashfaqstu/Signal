import { Activity, Clock3, Film, Search, Sparkles, TrendingUp } from "lucide-react";
import { useMemo, useState } from "react";
import { useMedia } from "../api/queries";
import type { MediaItem } from "../api/types";
import { go } from "../lib/router";
import { useStudio } from "../state/studio";
import { TOOLS, TOOL_BY_ID } from "../tools/catalog";
import type { ToolId } from "../tools/types";
import { Button, ToolBadge } from "../ui";
import s from "./Home.module.css";
import { Empty, HistoryCard, Rings, Sparkline } from "./parts";

interface Start {
  tool: ToolId;
  title: string;
  group: string;
  pick: number;
  simulate?: boolean;
}

const STARTS: Start[] = [
  { tool: "remove", title: "Erase passers-by", group: "Crowd · object removal", pick: 0 },
  { tool: "stack", title: "Clean a noisy burst", group: "Burst · noisy", pick: 0 },
  { tool: "highlight", title: "Spot moving people", group: "Crowd · highlight", pick: 5 },
  { tool: "rotate", title: "Straighten a pair", group: "Pair · rotated", pick: 1 },
  { tool: "align", title: "Align a shifted shot", group: "Base · translation", pick: 0, simulate: true },
  { tool: "spectrum", title: "Explore the spectrum", group: "Base · theory", pick: 0 },
];

export function startTool(tool: ToolId, simulate = false) {
  useStudio.getState().setInput(tool, { source: simulate ? "simulate" : "sample", mediaIds: [] });
  go(`/tool/${tool}`);
}

function sampleThumb(media: MediaItem[], group: string, pick: number): string | null {
  const g = media.filter((m) => m.group === group);
  const m = g[Math.min(pick, g.length - 1)];
  return m ? `/api/media/${m.id}/thumb.jpg?size=640` : null;
}

export function Home() {
  const [q, setQ] = useState("");
  const history = useStudio((st) => st.history);
  const media = useMedia().data ?? [];

  const matches = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return new Set(
      TOOLS.filter((t) => !needle || `${t.name} ${t.tagline}`.toLowerCase().includes(needle)).map((t) => t.id),
    );
  }, [q]);

  const stats = useMemo(() => {
    const gains = history.map((h) => h.gainDb).filter((g): g is number => g !== null);
    const avg = history.length ? history.reduce((a, h) => a + h.elapsedMs, 0) / history.length : 0;
    return {
      runs: history.length,
      frames: history.reduce((a, h) => a + h.frames, 0),
      best: gains.length ? Math.max(...gains) : null,
      avg,
      times: history.slice(0, 14).reverse().map((h) => h.elapsedMs),
    };
  }, [history]);

  return (
    <>
      <section className={s.hero}>
        <Rings className={s.heroRings} />
        <Rings className={s.heroRings2} />
        <h1 className={s.heroTitle}>What will you fix today?</h1>
        <label className={s.search}>
          <Search size={20} strokeWidth={2.2} />
          <input
            value={q}
            placeholder="Search tools"
            aria-label="Search tools"
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => {
              const first = TOOLS.find((t) => matches.has(t.id));
              if (e.key === "Enter" && first) go(`/tool/${first.id}`);
            }}
          />
        </label>
      </section>

      <nav className={s.tools} aria-label="Tools">
        {TOOLS.map((t, i) => (
          <a
            key={t.id}
            href={`#/tool/${t.id}`}
            className={`${s.toolBtn} rise`}
            style={{ ["--i" as string]: i }}
            data-dim={!matches.has(t.id)}
          >
            <span className={s.circle} style={{ background: t.gradient }}>
              <t.icon size={26} strokeWidth={2} />
            </span>
            {t.name}
          </a>
        ))}
      </nav>

      <section className={s.section}>
        <div className={s.stats}>
          <Stat i={0} icon={<Activity size={18} />} value={String(stats.runs)} label="Runs" spark={stats.times} />
          <Stat i={1} icon={<Film size={18} />} value={String(stats.frames)} label="Frames processed" />
          <Stat
            i={2}
            icon={<TrendingUp size={18} />}
            value={stats.best === null ? "—" : `+${stats.best.toFixed(1)} dB`}
            label="Best denoise gain"
          />
          <Stat
            i={3}
            icon={<Clock3 size={18} />}
            value={stats.runs ? `${(stats.avg / 1000).toFixed(1)} s` : "—"}
            label="Average run"
          />
        </div>
      </section>

      <section className={s.section}>
        <div className={s.sectionHead}>
          <h2 className={s.h2}>Start with a sample</h2>
        </div>
        <div className={s.cards}>
          {STARTS.map((st, i) => {
            const tool = TOOL_BY_ID[st.tool];
            const thumb = sampleThumb(media, st.group, st.pick);
            return (
              <button
                key={st.title}
                className={`${s.card} rise`}
                style={{ ["--i" as string]: i }}
                onClick={() => startTool(st.tool, st.simulate)}
              >
                <div className={s.thumb}>
                  {thumb ? (
                    <img src={thumb} alt="" loading="lazy" />
                  ) : (
                    <div className={s.thumbFallback} style={{ background: tool.gradient }}>
                      <tool.icon size={40} />
                    </div>
                  )}
                  <span className={s.thumbBadge}>
                    <ToolBadge icon={tool.icon} gradient={tool.gradient} size={30} radius={9} />
                  </span>
                </div>
                <div className={s.cardBody}>
                  <span className={s.cardTitle}>{st.title}</span>
                  <span className={s.cardSub}>{tool.name}</span>
                </div>
              </button>
            );
          })}
        </div>
      </section>

      <section className={s.section}>
        <div className={s.sectionHead}>
          <h2 className={s.h2}>Recent</h2>
          {history.length > 0 && (
            <a className={s.link} href="#/history">
              See all
            </a>
          )}
        </div>
        {history.length ? (
          <div className={s.cards}>
            {history.slice(0, 8).map((e, i) => (
              <HistoryCard key={e.id} e={e} i={i} />
            ))}
          </div>
        ) : (
          <Empty
            icon={<Sparkles size={26} />}
            title="Nothing here yet"
            action={
              <Button variant="primary" onClick={() => startTool("remove")}>
                Try a sample
              </Button>
            }
          />
        )}
      </section>
    </>
  );
}

function Stat({
  i,
  icon,
  value,
  label,
  spark,
}: {
  i: number;
  icon: React.ReactNode;
  value: string;
  label: string;
  spark?: number[];
}) {
  return (
    <div className={`${s.stat} rise`} style={{ ["--i" as string]: i }}>
      <span className={s.statIcon}>{icon}</span>
      <span className={s.statValue}>{value}</span>
      <span className={s.statLabel}>{label}</span>
      {spark && <Sparkline values={spark} className={s.spark} />}
    </div>
  );
}
