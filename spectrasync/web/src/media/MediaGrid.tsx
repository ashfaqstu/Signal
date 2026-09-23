import { Play, Trash2, UploadCloud } from "lucide-react";
import { useRef, useState } from "react";
import { useDeleteMedia, useImportMedia, useMedia } from "../api/queries";
import type { MediaItem } from "../api/types";
import { Button, cx } from "../ui";
import s from "./MediaGrid.module.css";

const SAMPLE_NAMES: Record<string, string> = {
  Base: "Photo",
  "Pair · rotated": "Rotated pair",
  "Burst · noisy": "Noisy burst",
  "Burst · clean ref": "Clean reference",
  Crowd: "Crowd",
};

export const groupName = (g: string) => SAMPLE_NAMES[g] ?? g;

interface Props {
  /** Picked ids, in pick order; omit for a plain library view. */
  selected?: string[];
  onToggle?: (m: MediaItem) => void;
  onUseGroup?: (items: MediaItem[]) => void;
  onUploaded?: (items: MediaItem[]) => void;
  accept?: "image" | "any";
  tile?: number;
  filter?: "all" | "uploads" | "samples";
}

export function UploadZone({ onUploaded, compact }: { onUploaded?: (items: MediaItem[]) => void; compact?: boolean }) {
  const upload = useImportMedia();
  const input = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);

  const send = (files: FileList | null) => {
    if (!files?.length) return;
    upload.mutate(Array.from(files), { onSuccess: (items) => onUploaded?.(items) });
  };

  return (
    <div
      className={cx(s.drop, over && s.dropOver)}
      onDragOver={(e) => {
        e.preventDefault();
        setOver(true);
      }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setOver(false);
        send(e.dataTransfer.files);
      }}
    >
      <Button variant="primary" icon={UploadCloud} onClick={() => input.current?.click()} style={{ width: "100%" }}>
        Upload files
      </Button>
      {!compact && <span>or drop photos and videos here</span>}
      <input
        ref={input}
        type="file"
        multiple
        hidden
        accept="image/*,video/*,.tif,.tiff"
        onChange={(e) => {
          send(e.target.files);
          e.target.value = "";
        }}
      />
      {upload.isPending && <span className={s.dropProgress} />}
    </div>
  );
}

export function MediaGrid({ selected, onToggle, onUseGroup, onUploaded, accept = "any", tile, filter = "all" }: Props) {
  const all = useMedia().data ?? [];
  const del = useDeleteMedia();
  const items = accept === "image" ? all.filter((m) => m.kind === "image") : all;

  const groups = new Map<string, MediaItem[]>();
  for (const m of items) {
    const key = m.sample ? m.group : "Uploads";
    if (filter === "uploads" && m.sample) continue;
    if (filter === "samples" && !m.sample) continue;
    groups.set(key, [...(groups.get(key) ?? []), m]);
  }
  const ordered = [...groups.entries()].sort(([a], [b]) => (a === "Uploads" ? -1 : b === "Uploads" ? 1 : 0));

  return (
    <div className={s.wrap} style={tile ? { ["--tile" as string]: `${tile}px` } : undefined}>
      {filter !== "samples" && <UploadZone onUploaded={onUploaded} compact={Boolean(tile)} />}
      {ordered.map(([name, list]) => (
        <section key={name} className={s.group}>
          <div className={s.groupHead}>
            <span className={s.groupTitle}>
              {groupName(name)}
              <span className={s.groupCount}>{list.length}</span>
            </span>
            {onUseGroup && list.length > 1 && (
              <Button size="sm" variant="ghost" onClick={() => onUseGroup(list)}>
                Use all
              </Button>
            )}
          </div>
          <div className={s.grid}>
            {list.map((m, i) => {
              const order = selected ? selected.indexOf(m.id) : -1;
              const Tag = onToggle ? "button" : "div";
              return (
                <Tag
                  key={m.id}
                  className={cx(s.tile, onToggle && s.tileBtn, order >= 0 && s.tileOn)}
                  style={{ ["--i" as string]: Math.min(i, 12) }}
                  onClick={onToggle ? () => onToggle(m) : undefined}
                  aria-pressed={onToggle ? order >= 0 : undefined}
                  title={m.name}
                >
                  <img src={`/api/media/${m.id}/thumb.jpg?size=320`} alt={m.name} loading="lazy" />
                  <span className={s.tileName}>{m.name}</span>
                  {m.kind === "video" && (
                    <span className={s.video}>
                      <Play size={11} fill="currentColor" />
                      Video
                    </span>
                  )}
                  {order >= 0 && <span className={s.order}>{order + 1}</span>}
                  {!m.sample && !onToggle && (
                    <button className={s.del} aria-label={`Delete ${m.name}`} onClick={() => del.mutate(m.id)}>
                      <Trash2 size={15} />
                    </button>
                  )}
                </Tag>
              );
            })}
          </div>
        </section>
      ))}
    </div>
  );
}
