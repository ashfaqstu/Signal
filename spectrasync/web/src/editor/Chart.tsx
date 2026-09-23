import { useState } from "react";
import type { Chart as ChartData } from "../api/types";
import { prettyOption } from "../tools/catalog";
import s from "./Editor.module.css";

const W = 300;
const H = 130;
const PAD = { l: 30, r: 6, t: 8, b: 20 };

const fmt = (v: number) => (Math.abs(v) >= 100 ? v.toFixed(0) : Math.abs(v) >= 1 ? v.toFixed(1) : v.toFixed(3));

/** Line and bar charts drawn as plain SVG so they follow the theme tokens exactly. */
export function Chart({ data, title }: { data: ChartData; title: string }) {
  const [hover, setHover] = useState<number | null>(null);
  const all = data.series.flatMap((x) => x.values);
  const lo = Math.min(0, ...all);
  const hi = Math.max(...all, lo + 1e-9);
  const iw = W - PAD.l - PAD.r;
  const ih = H - PAD.t - PAD.b;
  const y = (v: number) => PAD.t + ih - ((v - lo) / (hi - lo)) * ih;
  const n = data.x.length;

  return (
    <div className={s.chart}>
      <div className={s.chartHead}>
        <span>{title}</span>
        <span className={s.legend}>
          {data.series.map((ser) => (
            <span key={ser.name}>
              <i style={{ background: ser.role === "reference" ? "var(--teal)" : "var(--brand)" }} />
              {ser.name}
            </span>
          ))}
        </span>
      </div>
      <svg className={s.svg} viewBox={`0 0 ${W} ${H}`} onMouseLeave={() => setHover(null)}>
        <line className={s.axis} x1={PAD.l} x2={W - PAD.r} y1={y(lo)} y2={y(lo)} />
        <text className={s.tick} x={PAD.l - 4} y={y(hi) + 3} textAnchor="end">
          {fmt(hi)}
        </text>
        <text className={s.tick} x={PAD.l - 4} y={y(lo) + 3} textAnchor="end">
          {fmt(lo)}
        </text>
        {data.kind === "line" ? (
          <LineMarks data={data} y={y} n={n} iw={iw} lo={lo} hover={hover} setHover={setHover} />
        ) : (
          <BarMarks data={data} y={y} n={n} iw={iw} lo={lo} setHover={setHover} />
        )}
      </svg>
      <div className={s.chartTip}>
        {hover !== null
          ? `${data.x[hover]}  ·  ${data.series.map((ser) => `${ser.name} ${fmt(ser.values[hover])}`).join("  ·  ")}`
          : " "}
      </div>
    </div>
  );
}

interface MarkProps {
  data: ChartData;
  y: (v: number) => number;
  n: number;
  iw: number;
  lo: number;
  setHover: (i: number | null) => void;
}

function LineMarks({ data, y, n, iw, lo, hover, setHover }: MarkProps & { hover: number | null }) {
  const x = (i: number) => PAD.l + (n > 1 ? (i / (n - 1)) * iw : iw / 2);
  const primary = data.series.find((ser) => ser.role !== "reference") ?? data.series[0];
  const path = (vals: number[]) => vals.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)} ${y(v).toFixed(1)}`).join(" ");
  return (
    <>
      <path className={s.area} d={`${path(primary.values)} L${x(n - 1)} ${y(lo)} L${x(0)} ${y(lo)} Z`} />
      {data.series.map((ser) => (
        <path key={ser.name} className={ser.role === "reference" ? s.lineRef : s.linePrimary} d={path(ser.values)} />
      ))}
      {hover !== null && (
        <>
          <line className={s.hoverLine} x1={x(hover)} x2={x(hover)} y1={PAD.t} y2={y(lo)} />
          <circle className={s.hoverDot} cx={x(hover)} cy={y(primary.values[hover])} r={4} />
        </>
      )}
      <rect
        x={PAD.l}
        y={PAD.t}
        width={iw}
        height={H - PAD.t - PAD.b}
        fill="transparent"
        onMouseMove={(e) => {
          const r = (e.currentTarget as SVGRectElement).getBoundingClientRect();
          const f = (e.clientX - r.left) / r.width;
          setHover(Math.max(0, Math.min(n - 1, Math.round(f * (n - 1)))));
        }}
      />
    </>
  );
}

function BarMarks({ data, y, n, iw, lo, setHover }: MarkProps) {
  const band = iw / n;
  const k = data.series.length;
  const bw = Math.min(22, (band * 0.72) / k);
  return (
    <>
      {data.x.map((label, i) => (
        <g key={String(label)} onMouseEnter={() => setHover(i)}>
          <rect x={PAD.l + i * band} y={PAD.t} width={band} height={y(lo) - PAD.t} fill="transparent" />
          {data.series.map((ser, j) => {
            const v = ser.values[i];
            const top = Math.min(y(v), y(0));
            return (
              <rect
                key={ser.name}
                className={`${s.bar} ${ser.role === "reference" ? s.barRef : s.barPrimary}`}
                style={{ animationDelay: `${i * 50}ms` }}
                x={PAD.l + i * band + (band - bw * k) / 2 + j * bw}
                y={top}
                width={bw - 2}
                height={Math.max(1, Math.abs(y(v) - y(0)))}
                rx={3}
              />
            );
          })}
          <text className={s.tick} x={PAD.l + i * band + band / 2} y={H - 6} textAnchor="middle">
            {prettyOption(String(label)).slice(0, 10)}
          </text>
        </g>
      ))}
    </>
  );
}
