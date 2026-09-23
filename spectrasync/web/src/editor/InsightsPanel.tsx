import { BarChart3, ChevronDown } from "lucide-react";
import { useState } from "react";
import type { RunResult } from "../api/types";
import { formatReadout } from "../lib/format";
import { useStudio } from "../state/studio";
import { prettyOption } from "../tools/catalog";
import type { Metric, ToolDef } from "../tools/types";
import { StatusPill, cx } from "../ui";
import { Chart } from "./Chart";
import s from "./Editor.module.css";

const CHART_TITLES: Record<string, string> = {
  reducer_comparison: "Gain by method",
  pixel_timeseries: "Pixel over time",
  pixel_spectrum: "Temporal spectrum",
};

const FLAG_LABELS: Record<string, string> = { inverted_contrast: "Inverted contrast" };

export function Metrics({ items }: { items: Metric[] }) {
  return (
    <div className={s.metrics}>
      {items.map((m) => (
        <div key={m.label} className={s.metric} data-tone={m.tone}>
          <span className={s.metricValue} key={m.value}>
            {m.value}
          </span>
          <span className={s.metricLabel}>{m.label}</span>
        </div>
      ))}
    </div>
  );
}

function FrameDetails({ r, frame }: { r: RunResult; frame: number }) {
  const meta = r.frames[frame]?.meta;
  if (!meta) return null;
  const rows: [string, string][] = [];
  if (typeof meta.dy === "number") rows.push(["Shift Y", formatReadout(meta.dy, "+.2f", "px")]);
  if (typeof meta.dx === "number") rows.push(["Shift X", formatReadout(meta.dx, "+.2f", "px")]);
  if ("confidence" in meta)
    rows.push(["Confidence", meta.confidence === null ? "Reference" : formatReadout(meta.confidence, ".1f")]);
  if (typeof meta.threshold === "number") rows.push(["Threshold", formatReadout(meta.threshold, ".4f")]);
  if (meta.largest) rows.push(["Largest at", String(meta.largest)]);
  if (!rows.length) return null;
  return (
    <section className={s.block}>
      <span className={s.blockTitle}>Frame {frame + 1}</span>
      <div className={s.rows}>
        {rows.map(([k, v]) => (
          <div key={k} className={s.row}>
            <span className={s.rowLabel}>{k}</span>
            <span className={s.rowValue}>{v}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

export function InsightsPanel({ tool, frame }: { tool: ToolDef; frame: number }) {
  const r = useStudio((st) => st.results[tool.id]);
  const reducer = useStudio((st) => st.tools[tool.id].params.reducer);
  const [all, setAll] = useState(false);

  if (!r)
    return (
      <div className={s.empty}>
        <span className={s.emptyIcon} style={{ background: tool.gradient, width: 56, height: 56 }}>
          <BarChart3 size={26} />
        </span>
        <span className={s.inputSub}>No results yet</span>
      </div>
    );

  const verdict =
    r.verdict === "locked" ? (
      <StatusPill tone="ok">Locked</StatusPill>
    ) : r.verdict === "marginal" ? (
      <StatusPill tone="warn">Weak lock</StatusPill>
    ) : r.verdict ? (
      <StatusPill tone="bad">No lock</StatusPill>
    ) : null;

  return (
    <>
      <Metrics items={tool.headline(r, frame)} />

      {(verdict || r.flags.length > 0) && (
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {verdict}
          {r.flags.map((f) => (
            <StatusPill key={f} tone="warn">
              {FLAG_LABELS[f] ?? f}
            </StatusPill>
          ))}
        </div>
      )}

      {r.charts.map((c) => (
        <section key={c.id} className={s.card}>
          <Chart data={c} title={CHART_TITLES[c.id] ?? c.id} />
        </section>
      ))}

      {r.table && (
        <section className={s.block}>
          <span className={s.blockTitle}>Methods</span>
          <table className={s.table}>
            <thead>
              <tr>
                {r.table.columns.map((c) => (
                  <th key={c}>{c.replace(" (dB)", "")}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {r.table.rows.map((row) => (
                <tr key={String(row[0])} data-on={row[0] === reducer}>
                  {row.map((v, i) => (
                    <td key={i}>{i === 0 ? prettyOption(String(v)) : typeof v === "number" ? v.toFixed(2) : v}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      <FrameDetails r={r} frame={frame} />

      <section className={s.block}>
        <button className={cx(s.more, all && s.moreOpen)} onClick={() => setAll(!all)} aria-expanded={all}>
          All numbers
          <ChevronDown size={18} />
        </button>
        <div className={cx(s.collapse, all && s.collapseOpen)}>
          <div className={s.rows}>
            {r.readouts.map((o) => (
              <div key={o.key} className={s.row} data-tone={o.tone}>
                <span className={s.rowLabel}>{o.label}</span>
                <span className={s.rowValue}>{formatReadout(o.value, o.fmt, o.unit)}</span>
              </div>
            ))}
            <div className={s.row}>
              <span className={s.rowLabel}>time</span>
              <span className={s.rowValue}>{(r.elapsedMs / 1000).toFixed(2)} s</span>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
