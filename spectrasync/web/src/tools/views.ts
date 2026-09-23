import type { LayerRef, Marker, RunResult } from "../api/types";
import type { ToolDef, View } from "./types";

export function findLayer(r: RunResult, name: string | string[]): LayerRef | undefined {
  const names = Array.isArray(name) ? name : [name];
  for (const n of names) {
    const l = r.layers.find((x) => x.name === n);
    if (l) return l;
  }
  return undefined;
}

export function gridLayers(r: RunResult, view: Extract<View, { type: "grid" }>): LayerRef[] {
  if (view.group) return r.layers.filter((l) => l.group === view.group);
  return (view.layers ?? []).map((n) => findLayer(r, n)).filter((l): l is LayerRef => Boolean(l));
}

/** Views that have something to show for this result. */
export function availableViews(tool: ToolDef, r: RunResult | undefined): View[] {
  if (!r) return tool.views;
  return tool.views.filter((v) => {
    switch (v.type) {
      case "compare":
        return Boolean(findLayer(r, v.before) && findLayer(r, v.after));
      case "single":
        return Boolean(findLayer(r, v.layer));
      case "grid":
        return gridLayers(r, v).length > 0;
      case "frame":
        return r.frames.some((f) => f.layers[v.frameLayer]);
      case "frameCompare":
        return r.frames.some((f) => f.layers[v.before] && f.layers[v.after]);
    }
  });
}

export function markersFor(r: RunResult, layerName: string): Marker[] {
  return r.markers.filter((m) => m.layer === layerName);
}

/** The single most representative image of a result, for thumbnails. */
export function heroUrl(tool: ToolDef, r: RunResult): string | null {
  for (const v of availableViews(tool, r)) {
    if (v.type === "compare") return findLayer(r, v.after)?.url ?? null;
    if (v.type === "single") return findLayer(r, v.layer)?.url ?? null;
    if (v.type === "frame" || v.type === "frameCompare") {
      const key = v.type === "frame" ? v.frameLayer : v.after;
      const f = r.frames[Math.floor(r.frames.length / 2)];
      return f?.layers[key] ?? null;
    }
    if (v.type === "grid") return gridLayers(r, v)[0]?.url ?? null;
  }
  return null;
}

/** A small JPEG data URL, so history thumbnails outlive the server's run cache. */
export async function thumbnail(url: string, max = 320): Promise<string | null> {
  try {
    const img = new Image();
    img.src = url;
    await img.decode();
    const k = Math.min(1, max / Math.max(img.naturalWidth, img.naturalHeight));
    const c = document.createElement("canvas");
    c.width = Math.round(img.naturalWidth * k);
    c.height = Math.round(img.naturalHeight * k);
    c.getContext("2d")!.drawImage(img, 0, 0, c.width, c.height);
    return c.toDataURL("image/jpeg", 0.8);
  } catch {
    return null;
  }
}
