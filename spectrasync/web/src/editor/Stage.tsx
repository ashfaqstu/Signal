import {
  AlertTriangle,
  ChevronsLeftRight,
  ImagePlus,
  Maximize,
  Minus,
  Pause,
  Play,
  Plus,
  RefreshCw,
  WifiOff,
  X,
} from "lucide-react";
import { Suspense, lazy, useEffect, useLayoutEffect, useMemo, useRef, useState, type PointerEvent as RPE } from "react";
import type { ApiError } from "../api/client";
import { usePixelTimeseries } from "../api/queries";
import type { Marker, RunResult } from "../api/types";
import type { ToolDef, View } from "../tools/types";
import { prettyOption } from "../tools/catalog";
import { findLayer, gridLayers, markersFor } from "../tools/views";
import { Button, Spinner, cx } from "../ui";
import { Chart } from "./Chart";
import s from "./Editor.module.css";

const Formula = lazy(() => import("./Formula"));

/* ---------- what is on screen ---------- */

export function frameKey(view: View | undefined, r: RunResult): string {
  if (view?.type === "frame") return view.frameLayer;
  if (view?.type === "frameCompare") return view.after;
  return Object.keys(r.frames[0]?.layers ?? {})[0] ?? "frame";
}

/** The URL a "Download image" should save for the current view. */
export function currentImage(r: RunResult, view: View, frame: number): string | null {
  switch (view.type) {
    case "compare":
      return findLayer(r, view.after)?.url ?? null;
    case "single":
      return findLayer(r, view.layer)?.url ?? null;
    case "grid":
      return gridLayers(r, view)[0]?.url ?? null;
    case "frame":
      return r.frames[frame]?.layers[view.frameLayer] ?? null;
    case "frameCompare":
      return r.frames[frame]?.layers[view.after] ?? null;
  }
}

function naturalSize(r: RunResult, view: View): { w: number; h: number } {
  const l =
    view.type === "compare"
      ? findLayer(r, view.after)
      : view.type === "single"
        ? findLayer(r, view.layer)
        : r.layers.find((x) => x.group !== "Frequency") ?? r.layers[0];
  return { w: l?.width ?? 512, h: l?.height ?? 512 };
}

/* ---------- pieces ---------- */

function Markers({ markers, w, h }: { markers: Marker[]; w: number; h: number }) {
  if (!markers.length) return null;
  const r = Math.max(w, h) * 0.035;
  return (
    <svg className={s.markers} viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none">
      {markers.map((m, i) =>
        m.type === "box" ? (
          <rect
            key={i}
            className={s.box}
            style={{ ["--len" as string]: 2 * ((m.w ?? 0) + (m.h ?? 0)), animationDelay: `${i * 80}ms` }}
            x={m.x}
            y={m.y}
            width={m.w}
            height={m.h}
            rx={4}
            vectorEffect="non-scaling-stroke"
          />
        ) : (
          <g key={i} className={s.cross}>
            <circle cx={m.x} cy={m.y} r={r} vectorEffect="non-scaling-stroke" />
            <path
              d={`M${m.x - r * 1.8} ${m.y}h${r * 1.2}M${m.x + r * 0.6} ${m.y}h${r * 1.2}M${m.x} ${m.y - r * 1.8}v${r * 1.2}M${m.x} ${m.y + r * 0.6}v${r * 1.2}`}
              vectorEffect="non-scaling-stroke"
            />
          </g>
        ),
      )}
    </svg>
  );
}

function CompareSlider({ before, after, pixelated }: { before: string; after: string; pixelated: boolean }) {
  const [pos, setPos] = useState(50);
  const ref = useRef<HTMLDivElement>(null);
  const move = (e: RPE) => {
    const r = ref.current!.getBoundingClientRect();
    setPos(Math.max(0, Math.min(100, ((e.clientX - r.left) / r.width) * 100)));
  };
  return (
    <div
      ref={ref}
      className={s.compare}
      onPointerDown={(e) => {
        (e.target as Element).setPointerCapture(e.pointerId);
        move(e);
      }}
      onPointerMove={(e) => e.buttons && move(e)}
      role="slider"
      aria-label="Before and after"
      aria-valuenow={Math.round(pos)}
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "ArrowLeft") setPos((p) => Math.max(0, p - 5));
        if (e.key === "ArrowRight") setPos((p) => Math.min(100, p + 5));
      }}
    >
      <img className={cx(s.img, pixelated && s.pixelated)} src={after} alt="After" draggable={false} />
      <img
        className={cx(s.img, pixelated && s.pixelated)}
        src={before}
        alt="Before"
        draggable={false}
        style={{ clipPath: `inset(0 ${100 - pos}% 0 0)` }}
      />
      <span className={s.compareTag} style={{ left: 12, opacity: pos > 12 ? 1 : 0 }}>
        Before
      </span>
      <span className={s.compareTag} style={{ right: 12, opacity: pos < 88 ? 1 : 0 }}>
        After
      </span>
      <div className={s.compareHandle} style={{ left: `${pos}%` }}>
        <span className={s.compareKnob}>
          <ChevronsLeftRight size={20} strokeWidth={2.4} />
        </span>
      </div>
    </div>
  );
}

function GridView({ r, view }: { r: RunResult; view: Extract<View, { type: "grid" }> }) {
  const layers = gridLayers(r, view);
  const cols = layers.length <= 3 ? layers.length : layers.length === 4 ? 2 : 3;
  const rows = Math.ceil(layers.length / cols);
  return (
    <div
      className={s.grid}
      style={{ gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))`, ["--rows" as string]: rows }}
    >
      {layers.map((l, i) => (
        <div key={l.id} className={s.gridTile} style={{ ["--i" as string]: i }}>
          <div className={s.gridImg}>
            <img src={l.url} alt={l.name} className={l.width < 400 ? s.pixelated : undefined} />
            <Markers markers={markersFor(r, l.name)} w={l.width} h={l.height} />
          </div>
          <span className={s.gridLabel}>{view.group ? prettyOption(l.name) : l.name}</span>
        </div>
      ))}
    </div>
  );
}

function Empty({ tool, error, onChoose, onRetry }: { tool: ToolDef; error: ApiError; onChoose: () => void; onRetry: () => void }) {
  const need = tool.input === "single" ? "an image" : tool.input === "pair" ? "2 images" : `${tool.minFiles}+ photos`;
  const map: Record<string, { title: string; sub?: string; icon: typeof ImagePlus; action?: "choose" | "retry" }> = {
    choose_files: { title: `Choose ${need}`, icon: ImagePlus, action: "choose" },
    need_two_images: { title: "Choose 2 images", icon: ImagePlus, action: "choose" },
    need_two_frames: { title: "Needs 2+ frames", icon: ImagePlus, action: "choose" },
    need_three_frames: { title: "Needs 3+ frames", icon: ImagePlus, action: "choose" },
    no_video_backend: { title: "Video decoder missing", sub: "pip install imageio-ffmpeg", icon: AlertTriangle },
    bad_media: { title: "Can't read this file", icon: AlertTriangle, action: "choose" },
    offline: { title: "Server offline", sub: "python run_web.py", icon: WifiOff, action: "retry" },
  };
  const e = map[error.code] ?? { title: "Couldn't process this", sub: error.message, icon: AlertTriangle, action: "retry" as const };
  return (
    <div className={s.empty}>
      <span className={s.emptyIcon} style={{ background: tool.gradient }}>
        <e.icon size={32} />
      </span>
      <span className={s.emptyTitle}>{e.title}</span>
      {e.sub && <span className={s.emptySub}>{e.sub}</span>}
      {e.action === "choose" && (
        <Button variant="primary" icon={ImagePlus} onClick={onChoose}>
          Open media
        </Button>
      )}
      {e.action === "retry" && (
        <Button variant="secondary" icon={RefreshCw} onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  );
}

function PixelCard({ runId, x, y, onClose }: { runId: string; x: number; y: number; onClose: () => void }) {
  const q = usePixelTimeseries(runId, x, y);
  return (
    <div className={s.float}>
      <div className={s.floatHead}>
        <span>Pixel</span>
        <span className={s.floatSub}>
          {x}, {y}
          <button className={s.floatClose} aria-label="Close" onClick={onClose}>
            <X size={14} />
          </button>
        </span>
      </div>
      {q.data ? (
        <Chart
          title=""
          data={{
            id: "px",
            kind: "line",
            x: q.data.signal.map((_, i) => i),
            series: [
              { name: "value", values: q.data.signal, role: "primary" },
              { name: "median", values: q.data.signal.map(() => q.data!.median), role: "reference" },
            ],
          }}
        />
      ) : (
        <div className="skeleton" style={{ height: 150, borderRadius: 8 }} />
      )}
    </div>
  );
}

/* ---------- stage ---------- */

interface StageProps {
  tool: ToolDef;
  result: RunResult | undefined;
  views: View[];
  view: View;
  setView: (id: string) => void;
  frame: number;
  setFrame: (f: number) => void;
  running: boolean;
  error: ApiError | null;
  onChoose: () => void;
  onRetry: () => void;
}

export function Stage({ tool, result: r, views, view, setView, frame, setFrame, running, error, onChoose, onRetry }: StageProps) {
  const canvas = useRef<HTMLDivElement>(null);
  const [box, setBox] = useState({ w: 800, h: 600 });
  const [zoom, setZoom] = useState<number | null>(null);
  const [playing, setPlaying] = useState(false);
  const [probe, setProbe] = useState<{ x: number; y: number } | null>(null);
  const isPages = Boolean(tool.formulas);
  const nFrames = r?.frames.length ?? 0;

  useLayoutEffect(() => {
    const el = canvas.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setBox({ w: el.clientWidth, h: el.clientHeight }));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useEffect(() => setProbe(null), [r?.runId]);
  useEffect(() => setZoom(null), [view.id, tool.id]);

  useEffect(() => {
    if (!playing || nFrames < 2) return;
    const t = window.setInterval(() => setFrame((frame + 1) % nFrames), 160);
    return () => window.clearInterval(t);
  }, [playing, frame, nFrames, setFrame]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement).closest("input, select, textarea")) return;
      if (nFrames > 1 && e.key === "ArrowRight") setFrame(Math.min(nFrames - 1, frame + 1));
      if (nFrames > 1 && e.key === "ArrowLeft") setFrame(Math.max(0, frame - 1));
      if (e.key === "0") setZoom(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [frame, nFrames, setFrame]);

  const nat = useMemo(() => (r ? naturalSize(r, view) : { w: 1, h: 1 }), [r, view]);
  const fit = Math.min((box.w - 80) / nat.w, (box.h - 56) / nat.h, 6);
  const scale = zoom ?? fit;
  const zoomable = view.type !== "grid";
  const pixelated = scale > 2;

  const onWheel = (e: React.WheelEvent) => {
    if (!zoomable || !(e.ctrlKey || e.metaKey)) return;
    e.preventDefault();
    setZoom(Math.min(8, Math.max(0.05, scale * (e.deltaY < 0 ? 1.1 : 0.9))));
  };

  const pick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!(view.type === "single" && view.probe)) return;
    const rect = e.currentTarget.getBoundingClientRect();
    setProbe({
      x: Math.floor(((e.clientX - rect.left) / rect.width) * nat.w),
      y: Math.floor(((e.clientY - rect.top) / rect.height) * nat.h),
    });
  };

  const blank = Boolean(error && !(running && r));
  let content: React.ReactNode = null;
  if (blank && error) {
    content = <Empty tool={tool} error={error} onChoose={onChoose} onRetry={onRetry} />;
  } else if (!r) {
    content = <div className={cx(s.skeletonPage, "skeleton")} />;
  } else if (view.type === "grid") {
    content = <GridView r={r} view={view} />;
  } else {
    const pageStyle = { width: nat.w * scale, height: nat.h * scale };
    let inner: React.ReactNode = null;
    let markers: Marker[] = [];
    if (view.type === "compare") {
      inner = (
        <CompareSlider before={findLayer(r, view.before)!.url} after={findLayer(r, view.after)!.url} pixelated={pixelated} />
      );
    } else if (view.type === "frameCompare") {
      const f = r.frames[frame];
      inner = f && <CompareSlider before={f.layers[view.before]} after={f.layers[view.after]} pixelated={pixelated} />;
    } else {
      const url =
        view.type === "single" ? findLayer(r, view.layer)?.url : r.frames[frame]?.layers[view.frameLayer];
      const lname = view.type === "single" ? findLayer(r, view.layer)?.name ?? "" : `overlay#${frame}`;
      markers = view.type === "frame" && !view.boxes ? [] : markersFor(r, lname);
      if (probe && view.type === "single" && view.probe) markers = [{ layer: lname, type: "crosshair", ...probe }];
      inner = url && <img key={url} className={cx(s.img, pixelated && s.pixelated)} src={url} alt={view.label} draggable={false} />;
    }
    content = (
      <div
        className={cx(s.page, running && s.pageBusy, view.type === "single" && view.probe && s.probe)}
        style={pageStyle}
        onClick={pick}
        key={`${r.runId}-${view.id}`}
      >
        {inner}
        <Markers markers={markers} w={nat.w} h={nat.h} />
      </div>
    );
  }

  const formula = tool.formulas?.[view.id];
  const stripKey = r && nFrames ? frameKey(views.find((v) => v.type === "frame"), r) : "";

  return (
    <div className={s.stage}>
      {!isPages && r && !blank && views.length > 1 ? (
        <div className={s.viewsBar}>
          <div className={s.views} role="tablist">
            {views.map((v) => (
              <button
                key={v.id}
                role="tab"
                aria-selected={v.id === view.id}
                className={cx(s.viewBtn, v.id === view.id && s.viewOn)}
                onClick={() => setView(v.id)}
              >
                {v.label}
              </button>
            ))}
          </div>
        </div>
      ) : formula && r && !blank ? (
        <Suspense fallback={<div className={s.formula} />}>
          <Formula key={view.id} tex={formula} className={s.formula} />
        </Suspense>
      ) : (
        <div />
      )}

      <div className={s.canvas} ref={canvas} onWheel={onWheel}>
        {running && <div className={s.progress} />}
        <div className={s.canvasInner}>{content}</div>
        {running && r && (
          <span className={s.busyPill}>
            <Spinner />
            Updating
          </span>
        )}
        {probe && r && !blank && view.type === "single" && view.probe && (
          <PixelCard runId={r.runId} x={probe.x} y={probe.y} onClose={() => setProbe(null)} />
        )}
      </div>

      <div className={s.bottom}>
        {blank ? (
          <div className={s.strip} />
        ) : isPages && r ? (
          <div className={s.stripScroll}>
            {views.map((v, i) => {
              const l = v.type === "single" ? findLayer(r, v.layer) : undefined;
              return (
                <button key={v.id} className={s.page2} onClick={() => setView(v.id)}>
                  <span className={cx(s.frame, v.id === view.id && s.frameOn)}>
                    {l && <img src={l.url} alt="" />}
                    <span className={s.frameNum}>{i + 1}</span>
                  </span>
                  {v.label}
                </button>
              );
            })}
          </div>
        ) : r && nFrames > 1 ? (
          <div className={s.strip}>
            <Button
              variant="primary"
              size="sm"
              iconOnly
              icon={playing ? Pause : Play}
              aria-label={playing ? "Pause" : "Play"}
              onClick={() => {
                if (view.type !== "frame" && view.type !== "frameCompare") {
                  const fv = views.find((v) => v.type === "frame");
                  if (fv) setView(fv.id);
                }
                setPlaying(!playing);
              }}
            />
            <span className={s.counter}>
              {frame + 1} / {nFrames}
            </span>
            <FrameStrip r={r} frame={frame} layerKey={stripKey} onPick={(i) => {
              setPlaying(false);
              setFrame(i);
              if (view.type !== "frame" && view.type !== "frameCompare") {
                const fv = views.find((v) => v.type === "frame");
                if (fv) setView(fv.id);
              }
            }} />
          </div>
        ) : (
          <div className={s.strip} />
        )}

        {zoomable && r && !blank && (
          <div className={s.zoom}>
            <Button variant="ghost" size="sm" iconOnly icon={Minus} aria-label="Zoom out" onClick={() => setZoom(Math.max(0.05, scale / 1.25))} />
            <input
              type="range"
              className={s.zoomRange}
              min={0.1}
              max={4}
              step={0.01}
              value={Math.min(4, scale)}
              aria-label="Zoom"
              onChange={(e) => setZoom(parseFloat(e.target.value))}
              style={{ accentColor: "var(--brand)" }}
            />
            <Button variant="ghost" size="sm" iconOnly icon={Plus} aria-label="Zoom in" onClick={() => setZoom(Math.min(8, scale * 1.25))} />
            <span className={s.zoomPct}>{Math.round(scale * 100)}%</span>
            <Button variant="ghost" size="sm" iconOnly icon={Maximize} aria-label="Fit" title="Fit (0)" onClick={() => setZoom(null)} />
          </div>
        )}
      </div>
    </div>
  );
}

function FrameStrip({ r, frame, layerKey, onPick }: { r: RunResult; frame: number; layerKey: string; onPick: (i: number) => void }) {
  const wrap = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = wrap.current?.children[frame] as HTMLElement | undefined;
    el?.scrollIntoView({ block: "nearest", inline: "nearest" });
  }, [frame]);

  return (
    <div className={s.stripScroll} ref={wrap}>
      {r.frames.map((f, i) => {
        const conf = f.meta.confidence;
        const dot =
          "objects" in f.meta
            ? f.meta.objects > 0
              ? "var(--highlight-dot, #ff4f8b)"
              : null
            : conf === null || conf === undefined
              ? "var(--text-3)"
              : conf >= 2
                ? "var(--ok)"
                : conf >= 1.2
                  ? "var(--warn)"
                  : "var(--bad)";
        return (
          <button key={f.index} className={cx(s.frame, i === frame && s.frameOn)} onClick={() => onPick(i)} aria-label={`Frame ${i + 1}`}>
            <img src={f.layers[layerKey] ?? Object.values(f.layers)[0]} alt="" loading="lazy" />
            <span className={s.frameNum}>{i + 1}</span>
            {dot && <span className={s.frameDot} style={{ background: dot }} />}
          </button>
        );
      })}
    </div>
  );
}
