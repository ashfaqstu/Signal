"""Execution and analytics endpoints for all workspaces."""

from __future__ import annotations

import tempfile
import time
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import FileResponse
import numpy as np

import spectrasync as ss
from ..layers import layer_store, run_store
from ..media import media_store
from ..schemas import (
    AlignParams,
    FrameRef,
    HighlightParams,
    LayerRef,
    PixelTimeseriesResponse,
    RemoveParams,
    RotateParams,
    RunResult,
    SpectrumParams,
    StackParams,
)
from ..services.align import run_align
from ..services.highlight import run_highlight
from ..services.remove import run_remove
from ..services.rotate import run_rotate
from ..services.spectrum import run_spectrum
from ..services.stack import run_stack

router = APIRouter(tags=["runs"])


def _handle_error(e: Exception) -> None:
    msg = str(e)
    if msg in ("need_two_images", "need_two_frames", "need_three_frames", "no_video_backend", "bad_media"):
        raise HTTPException(status_code=422, detail={"code": msg, "message": msg})
    if isinstance(e, RuntimeError) and "video backend" in msg.lower():
        raise HTTPException(status_code=422, detail={"code": "no_video_backend", "message": msg})
    raise HTTPException(status_code=422, detail={"code": "runtime_error", "message": msg})


@router.post("/run/{workspace}", response_model=RunResult)
def execute_run(
    workspace: str,
    body: dict[str, Any],
) -> RunResult:
    """Execute analysis for the specified workspace."""
    start_time = time.perf_counter()
    run_id = uuid.uuid4().hex[:12]

    try:
        if workspace == "align":
            params = AlignParams.model_validate(body)
            res = run_align(params, media_store)
        elif workspace == "rotate":
            params = RotateParams.model_validate(body)
            res = run_rotate(params, media_store)
        elif workspace == "stack":
            params = StackParams.model_validate(body)
            res = run_stack(params, media_store)
        elif workspace == "remove":
            params = RemoveParams.model_validate(body)
            res = run_remove(params, media_store)
        elif workspace == "highlight":
            params = HighlightParams.model_validate(body)
            res = run_highlight(params, media_store)
        elif workspace == "spectrum":
            params = SpectrumParams.model_validate(body)
            res = run_spectrum(params, media_store)
        else:
            raise HTTPException(status_code=404, detail=f"Unknown workspace: {workspace}")
    except HTTPException:
        raise
    except Exception as e:
        _handle_error(e)

    # Store layers and build layer references
    layer_refs: list[LayerRef] = []
    layer_ids: list[str] = []

    for name, group, kind, arr, cmap in res.layers:
        layer = layer_store.put(arr, kind=kind, name=name, group=group, cmap=cmap)
        layer_ids.append(layer.id)
        layer_refs.append(
            LayerRef(
                id=layer.id,
                name=name,
                group=group,
                kind=kind,
                width=layer.width,
                height=layer.height,
                url=f"/api/layers/{layer.id}.png",
            )
        )

    # Store frame layers for sequence workspaces
    frame_refs: list[FrameRef] = []
    for f in res.frames:
        idx = f["index"]
        name = f["name"]
        meta = f.get("meta", {})

        frame_layer_urls: dict[str, str] = {}
        if "array" in f:
            l = layer_store.put(f["array"], kind="image", name=f"{name}_frame", group="Frames")
            layer_ids.append(l.id)
            frame_layer_urls["frame"] = f"/api/layers/{l.id}.png"
        elif "layers_arr" in f:
            for l_name, l_arr in f["layers_arr"].items():
                l = layer_store.put(l_arr, kind="image", name=f"{name}_{l_name}", group="Frames")
                layer_ids.append(l.id)
                frame_layer_urls[l_name] = f"/api/layers/{l.id}.png"

        frame_refs.append(
            FrameRef(
                index=idx,
                name=name,
                layers=frame_layer_urls,
                meta=meta,
            )
        )

    elapsed_ms = int((time.perf_counter() - start_time) * 1000)

    # Save to run store
    run_store.put(run_id, res.payload, layer_ids)

    return RunResult(
        run_id=run_id,
        workspace=workspace,
        elapsed_ms=elapsed_ms,
        verdict=res.verdict,  # type: ignore
        readouts=res.readouts,
        layers=layer_refs,
        markers=res.markers,
        frames=frame_refs,
        charts=res.charts,
        table=res.table,
        flags=res.flags,
    )


@router.get("/runs/{run_id}/pixel", response_model=PixelTimeseriesResponse)
def get_pixel_timeseries(
    run_id: str,
    x: int = Query(..., description="Cropped x coordinate"),
    y: int = Query(..., description="Cropped y coordinate"),
) -> PixelTimeseriesResponse:
    """Retrieve time-series intensity and frequency spectrum for a specific pixel."""
    payload = run_store.get(run_id)
    if not payload or not isinstance(payload, dict) or "aligned" not in payload:
        raise HTTPException(status_code=404, detail="Run result or aligned sequence not found")

    aligned = payload["aligned"]
    y0, _, x0, _ = payload.get("valid_box", (0, 0, 0, 0))

    cy = int(y + y0)
    cx = int(x + x0)

    H, W = aligned[0].shape[:2]
    if cy < 0 or cy >= H or cx < 0 or cx >= W:
        raise HTTPException(status_code=400, detail="Pixel coordinates out of bounds")

    sig, freq, spec = ss.pixel_timeseries(aligned, cy, cx)

    return PixelTimeseriesResponse(
        signal=[float(v) for v in sig],
        median=float(np.median(sig)),
        freq=[round(float(f), 4) for f in freq],
        spectrum=[round(float(s), 4) for s in spec],
    )


@router.get("/runs/{run_id}/export")
def export_layer(
    run_id: str,
    layer: str = Query("Stacked", description="Layer name to export"),
    format: str = Query("png", description="File format"),
) -> Response:
    """Export a specific output layer as a PNG image file download."""
    entry = run_store.get_entry(run_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Run not found")

    target_layer_id = None
    for lid in entry.layer_ids:
        l = layer_store.get_layer(lid)
        if l and l.name.lower() == layer.lower():
            target_layer_id = lid
            break

    if not target_layer_id and entry.layer_ids:
        target_layer_id = entry.layer_ids[0]

    if not target_layer_id:
        raise HTTPException(status_code=404, detail=f"Layer '{layer}' not found")

    png_bytes = layer_store.get_bytes(target_layer_id)
    if not png_bytes:
        raise HTTPException(status_code=404, detail="Failed to encode layer")

    safe_name = layer.replace(" ", "_").lower()
    return Response(
        content=png_bytes,
        media_type="image/png",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_name}.png"',
        },
    )


@router.get("/runs/{run_id}/export-sequence")
def export_sequence(
    run_id: str,
    layer: str = Query("overlay", description="Layer name in sequence"),
    format: str = Query("mp4", description="Output format (mp4 or gif)"),
    fps: int = Query(12, description="Frames per second"),
) -> FileResponse:
    """Export sequence as a video (MP4) or GIF file download."""
    payload = run_store.get(run_id)
    if not payload or not isinstance(payload, dict):
        raise HTTPException(status_code=404, detail="Sequence not found in run")

    frames = payload.get("overlay_frames") or payload.get("aligned")
    if not frames:
        raise HTTPException(status_code=404, detail="No sequence frames found to export")

    tmp_dir = tempfile.gettempdir()
    if format.lower() == "gif":
        out_path = f"{tmp_dir}/spectrasync_export_{run_id}.gif"
        ss.write_gif(out_path, frames, fps=fps)
        media_type = "image/gif"
        filename = f"sequence_{run_id}.gif"
    else:
        out_path = f"{tmp_dir}/spectrasync_export_{run_id}.mp4"
        res_path = ss.write_video(out_path, frames, fps=fps)
        if res_path.endswith(".gif"):
            media_type = "image/gif"
            filename = f"sequence_{run_id}.gif"
        else:
            media_type = "video/mp4"
            filename = f"sequence_{run_id}.mp4"
        out_path = res_path

    return FileResponse(
        out_path,
        media_type=media_type,
        filename=filename,
    )
