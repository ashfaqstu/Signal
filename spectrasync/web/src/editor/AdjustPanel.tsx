import { ChevronDown, FlaskConical, ImagePlus, Play, RotateCcw } from "lucide-react";
import { useState } from "react";
import { useMedia, useRegistries } from "../api/queries";
import type { MediaItem } from "../api/types";
import { groupName } from "../media/MediaGrid";
import { useStudio } from "../state/studio";
import { prettyOption } from "../tools/catalog";
import type { Control, ControlContext, Source, ToolDef } from "../tools/types";
import { Button, Chips, Segmented, Select, Slider, Switch, cx } from "../ui";
import s from "./Editor.module.css";

const SOURCE_LABEL: Record<Source, string> = { sample: "Sample", files: "My files", simulate: "Simulate" };

export function useControlContext(tool: ToolDef): ControlContext {
  const { params, input } = useStudio((st) => st.tools[tool.id]);
  const media = useMedia().data ?? [];
  const video =
    input.source === "files"
      ? (input.mediaIds.map((id) => media.find((m) => m.id === id)).find((m) => m?.kind === "video") ?? null)
      : null;
  return { params, input, video };
}

function ControlView({ tool, c, ctx }: { tool: ToolDef; c: Control; ctx: ControlContext }) {
  const setParam = useStudio((st) => st.setParam);
  const registries = useRegistries().data;
  const media = useMedia().data ?? [];
  const value = ctx.params[c.key];
  const set = (v: number | string | boolean | null) => setParam(tool.id, c.key, v);

  switch (c.kind) {
    case "slider": {
      const max = (c.key === "aIndex" || c.key === "bIndex") && ctx.video?.nFrames ? ctx.video.nFrames - 1 : c.max;
      return (
        <Slider
          label={c.label}
          value={Number(value ?? c.min)}
          min={c.min}
          max={max}
          step={c.step}
          unit={c.unit}
          digits={c.digits}
          onCommit={set}
        />
      );
    }
    case "toggle":
      return <Switch label={c.label} value={Boolean(value)} onChange={set} />;
    case "choice":
      return (
        <Chips
          label={c.label}
          value={value as string | number}
          options={c.options}
          onChange={(v) => set(v)}
        />
      );
    case "registry": {
      const names = registries?.[c.registry]?.map((r) => r.name) ?? [String(value)];
      const options = names.map((n) => ({ value: n, label: prettyOption(n) }));
      return options.length <= 5 ? (
        <Chips label={c.label} value={String(value)} options={options} onChange={set} />
      ) : (
        <Select label={c.label} value={String(value)} options={options} onChange={set} />
      );
    }
    case "media": {
      const images = media.filter((m) => m.kind === "image");
      return (
        <Select
          label={c.label}
          value={String(value ?? "")}
          options={[{ value: "", label: "None" }, ...images.map((m) => ({ value: m.id, label: m.name }))]}
          onChange={(v) => set(v || null)}
        />
      );
    }
  }
}

function Controls({ tool, list, ctx }: { tool: ToolDef; list: Control[]; ctx: ControlContext }) {
  return (
    <>
      {list
        .filter((c) => !c.when || c.when(ctx))
        .map((c) => (
          <ControlView key={c.key} tool={tool} c={c} ctx={ctx} />
        ))}
    </>
  );
}

function InputPreview({ tool, ctx, onChoose }: { tool: ToolDef; ctx: ControlContext; onChoose: () => void }) {
  const media = useMedia().data ?? [];
  const { input } = ctx;
  let items: MediaItem[] = [];
  let name = "";
  let sub = "";

  if (input.source === "sample") {
    items = media.filter((m) => m.group === tool.sampleGroup);
    if (tool.input === "pair") items = items.slice(0, 2);
    name = groupName(tool.sampleGroup);
    sub = items.length > 1 ? `${items.length} photos` : "Sample";
  } else if (input.source === "simulate") {
    const base = media.find((m) => m.id === input.mediaIds[0] && m.kind === "image");
    items = base ? [base] : media.filter((m) => m.group === "Base");
    name = "Simulated";
    sub = `from ${items[0]?.name ?? "sample photo"}`;
  } else {
    items = input.mediaIds.map((id) => media.find((m) => m.id === id)).filter(Boolean) as MediaItem[];
    if (!items.length)
      return (
        <button className={s.chooseBtn} onClick={onChoose}>
          <ImagePlus size={20} />
          Choose files
        </button>
      );
    name = ctx.video ? ctx.video.name : items.length === 1 ? items[0].name : `${items.length} photos`;
    sub = ctx.video ? "Video" : items.length < tool.minFiles ? `Needs ${tool.minFiles}` : "Ready";
  }

  const shown = items.slice(0, 3);
  return (
    <button className={s.inputPreview} onClick={onChoose}>
      <span className={s.stackThumbs}>
        {input.source === "simulate" ? (
          <span style={{ background: tool.gradient, left: 0, top: 0 }}>
            <FlaskConical size={20} />
          </span>
        ) : (
          shown.map((m, i) => (
            <img
              key={m.id}
              src={`/api/media/${m.id}/thumb.jpg`}
              alt=""
              style={{ left: i * 8, top: i * 3, zIndex: 3 - i }}
            />
          ))
        )}
        {ctx.video && (
          <span style={{ left: 30, top: 24, width: 22, height: 22, background: "var(--brand)", zIndex: 5 }}>
            <Play size={11} fill="currentColor" />
          </span>
        )}
      </span>
      <span className={s.inputText}>
        <span className={s.inputName}>{name}</span>
        <span className={s.inputSub}>{sub}</span>
      </span>
      <span className={s.inputAction}>Change</span>
    </button>
  );
}

export function AdjustPanel({ tool, onChoose }: { tool: ToolDef; onChoose: () => void }) {
  const ctx = useControlContext(tool);
  const setInput = useStudio((st) => st.setInput);
  const resetTool = useStudio((st) => st.resetTool);
  const [more, setMore] = useState(false);
  const advanced = tool.advanced.filter((c) => !c.when || c.when(ctx));

  return (
    <>
      <section className={s.block}>
        <span className={s.blockTitle}>Input</span>
        {tool.sources.length > 1 && (
          <Segmented<Source>
            ariaLabel="Input source"
            value={ctx.input.source}
            onChange={(source) => setInput(tool.id, { ...ctx.input, source })}
            options={tool.sources.map((v) => ({ value: v, label: SOURCE_LABEL[v] }))}
          />
        )}
        <InputPreview tool={tool} ctx={ctx} onChoose={onChoose} />
      </section>

      {ctx.input.source === "simulate" && tool.simulate.length > 0 && (
        <section className={s.card}>
          <Controls tool={tool} list={tool.simulate} ctx={ctx} />
        </section>
      )}

      <section className={s.block}>
        <span className={s.blockTitle}>Settings</span>
        <Controls tool={tool} list={tool.basic} ctx={ctx} />
      </section>

      {advanced.length > 0 && (
        <section className={s.block}>
          <button className={cx(s.more, more && s.moreOpen)} onClick={() => setMore(!more)} aria-expanded={more}>
            More options
            <ChevronDown size={18} />
          </button>
          <div className={cx(s.collapse, more && s.collapseOpen)}>
            <div>
              <Controls tool={tool} list={tool.advanced} ctx={ctx} />
            </div>
          </div>
        </section>
      )}

      <Button variant="ghost" size="sm" icon={RotateCcw} onClick={() => resetTool(tool.id)}>
        Reset settings
      </Button>
    </>
  );
}
