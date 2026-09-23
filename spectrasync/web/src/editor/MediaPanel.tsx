import { useMedia } from "../api/queries";
import type { MediaItem } from "../api/types";
import { MediaGrid } from "../media/MediaGrid";
import { useStudio } from "../state/studio";
import type { ToolDef } from "../tools/types";
import s from "./Editor.module.css";

/** Apply one click on a media tile to the tool's picked list. */
function toggle(tool: ToolDef, current: string[], m: MediaItem, media: MediaItem[]): string[] {
  if (m.kind === "video") return current.includes(m.id) ? [] : [m.id];
  const images = current.filter((id) => media.find((x) => x.id === id)?.kind === "image");
  if (tool.input === "single") return [m.id];
  if (images.includes(m.id)) return images.filter((id) => id !== m.id);
  const next = [...images, m.id];
  return tool.input === "pair" ? next.slice(-2) : next;
}

function adopt(tool: ToolDef, items: MediaItem[]): string[] {
  const video = items.find((m) => m.kind === "video");
  if (video && tool.acceptsVideo) return [video.id];
  const ids = items.filter((m) => m.kind === "image").map((m) => m.id);
  return tool.input === "single" ? ids.slice(0, 1) : tool.input === "pair" ? ids.slice(0, 2) : ids;
}

export function MediaPanel({ tool }: { tool: ToolDef }) {
  const media = useMedia().data ?? [];
  const input = useStudio((st) => st.tools[tool.id].input);
  const setInput = useStudio((st) => st.setInput);
  const selected = input.source === "files" ? input.mediaIds : [];
  const use = (ids: string[]) => setInput(tool.id, { source: "files", mediaIds: ids });

  const need = tool.input === "single" ? "1 image" : tool.input === "pair" ? "2 images" : `${tool.minFiles}+ photos`;
  const isVideo = selected.some((id) => media.find((m) => m.id === id)?.kind === "video");

  return (
    <>
      <div className={s.needs}>
        <span>Pick {need}{tool.acceptsVideo ? " or a video" : ""}</span>
        <span>{isVideo ? "Video" : `${selected.length} selected`}</span>
      </div>
      <MediaGrid
        tile={92}
        accept={tool.acceptsVideo ? "any" : "image"}
        selected={selected}
        onToggle={(m) => use(toggle(tool, selected, m, media))}
        onUseGroup={tool.input === "single" ? undefined : (items) => use(adopt(tool, items))}
        onUploaded={(items) => use(adopt(tool, items))}
      />
    </>
  );
}
