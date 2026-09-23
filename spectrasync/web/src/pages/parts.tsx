import type { ReactNode } from "react";
import type { HistoryEntry } from "../state/studio";
import { TOOL_BY_ID } from "../tools/catalog";
import { ToolBadge } from "../ui";
import s from "./Home.module.css";

/** Concentric "spectrum" rings, used as quiet decoration on gradients. */
export function Rings({ className }: { className: string }) {
  return (
    <svg className={className} viewBox="0 0 200 200" aria-hidden fill="none" stroke="#fff">
      {[96, 80, 64, 48, 32, 16].map((r, i) => (
        <circle key={r} cx="100" cy="100" r={r} strokeWidth={0.6 + i * 0.15} strokeDasharray={i % 2 ? "2 4" : "none"} />
      ))}
      <path d="M4 100h192M100 4v192" strokeWidth="0.4" />
    </svg>
  );
}

export function Sparkline({ values, className }: { values: number[]; className: string }) {
  if (values.length < 2) return null;
  const max = Math.max(...values);
  const min = Math.min(...values);
  const span = max - min || 1;
  const pts = values.map((v, i) => [(i / (values.length - 1)) * 100, 34 - ((v - min) / span) * 30]);
  const d = pts.map((p, i) => `${i ? "L" : "M"}${p[0].toFixed(1)} ${p[1].toFixed(1)}`).join(" ");
  return (
    <svg className={className} viewBox="0 0 100 36" preserveAspectRatio="none" aria-hidden>
      <path d={`${d} L100 36 L0 36 Z`} fill="currentColor" opacity="0.12" />
      <path d={d} fill="none" stroke="currentColor" strokeWidth="2" vectorEffect="non-scaling-stroke" strokeLinejoin="round" />
    </svg>
  );
}

export function timeAgo(t: number): string {
  const s = Math.round((Date.now() - t) / 1000);
  if (s < 60) return "Just now";
  const m = Math.round(s / 60);
  if (m < 60) return `${m} min ago`;
  const h = Math.round(m / 60);
  if (h < 24) return `${h} h ago`;
  return new Date(t).toLocaleDateString();
}

export function HistoryCard({ e, i }: { e: HistoryEntry; i: number }) {
  const tool = TOOL_BY_ID[e.tool];
  if (!tool) return null;
  return (
    <a className={`${s.card} rise`} style={{ ["--i" as string]: i }} href={`#/tool/${e.tool}`}>
      <div className={s.thumb}>
        {e.thumb ? (
          <img src={e.thumb} alt="" />
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
        <span className={s.cardTitle}>{tool.name}</span>
        <span className={s.cardSub}>{e.headline}</span>
        <span className={s.cardMeta}>
          <span>{timeAgo(e.at)}</span>
          <span>{(e.elapsedMs / 1000).toFixed(1)} s</span>
        </span>
      </div>
    </a>
  );
}

export function Empty({ icon, title, action }: { icon: ReactNode; title: string; action?: ReactNode }) {
  return (
    <div className={s.empty}>
      <span className={s.emptyIcon}>{icon}</span>
      <strong>{title}</strong>
      {action}
    </div>
  );
}
