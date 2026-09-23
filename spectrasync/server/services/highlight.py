"""Highlight workspace service (moving object detection and outlining)."""

from __future__ import annotations

import numpy as np

import spectrasync as ss
from ..schemas import HighlightParams, Readout, Marker
from ..media import MediaStore
from .align import ServiceResult
from .common import get_base_image, load_sequence

SAMPLE_SET = "new_image/1/*.jpg"


def run_highlight(params: HighlightParams, media: MediaStore) -> ServiceResult:
    if params.source == "synthetic":
        base = get_base_image(params.base_id, media)
        img = ss.even_square(base, max_side=384)
        src = ss.SyntheticSource(
            img,
            n=params.n,
            max_shift=3.0,
            noise=params.noise,
            mover=ss.moving_disc(radius=params.radius, value=0.03),
            seed=3,
        )
        frames = src.frames()
        reducer, mode = "shorth", "translation"
    elif params.source == "video":
        raw_frames = media.load_video(
            params.media_id or "",
            max_frames=params.frames,
            step=params.step,
            max_side=384,
            gray=not params.colour,
        )
        frames = [ss.even_square(f, 384) for f in raw_frames]
        reducer, mode = params.reducer, "translation"
    else:  # photos
        frames, _ = load_sequence(
            params.media_ids,
            media,
            max_side=params.max_side,
            gray=not params.colour,
            sample_glob=SAMPLE_SET,
            min_count=3,
        )
        reducer, mode = params.reducer, params.mode

    res = ss.remove_moving_objects(frames, reducer=reducer, mode=mode)

    H, W = res.output.shape[:2]
    box = res.stats["valid_box"] if params.source == "photos" else (0, H, 0, W)
    y0, y1, x0, x1 = box
    valid = ss.mask_from_box((H, W), box)

    view = lambda a: a[y0:y1, x0:x1]

    band = {"low": params.low, "high": params.high} if params.detector == "bandpass" else {}
    detections, background = ss.highlight_sequence(
        res.aligned,
        background=res.output,
        detector=params.detector,
        k=params.k,
        smooth=params.smooth,
        min_area=params.min_area,
        valid=valid,
        **band,
    )

    layers = [
        ("Plate", "Result", "image", view(background), "inferno")
    ]

    markers: list[Marker] = []
    frame_dicts = []

    for i, det in enumerate(detections):
        score_view = view(det.score)
        max_s = score_view.max()
        norm_score = score_view / max(max_s, 1e-9)

        meta: dict[str, Any] = {
            "objects": len(det.boxes),
            "threshold": float(det.threshold),
            "coverage": round(float(100.0 * view(det.mask).mean()), 2),
        }
        if det.boxes:
            by0, bx0, by1, bx1 = det.boxes[0]
            meta["largest"] = f"{(by0 + by1) // 2 - y0}, {(bx0 + bx1) // 2 - x0}"
            meta["size"] = f"{by1 - by0}×{bx1 - bx0}"

        for (by0, bx0, by1, bx1) in det.boxes:
            markers.append(
                Marker(
                    layer=f"overlay#{i}",
                    type="box",
                    x=float(bx0 - x0),
                    y=float(by0 - y0),
                    w=float(bx1 - bx0),
                    h=float(by1 - by0),
                )
            )

        frame_dicts.append({
            "index": i,
            "name": f"frame_{i}",
            "layers_arr": {
                "photo": view(res.aligned[i]),
                "overlay": view(det.overlay),
                "mask": view(det.mask.astype(float)),
                "score": norm_score,
                "outline": view(det.outline),
            },
            "meta": meta,
        })

    total_objects = sum(len(d.boxes) for d in detections)
    readouts = [
        Readout(key="total_objects", label="total objects", value=total_objects, fmt="d")
    ]

    payload = {
        "detections": detections,
        "overlay_frames": [view(d.overlay) for d in detections],
        "background": view(background),
    }

    return ServiceResult(
        layers=layers,
        readouts=readouts,
        markers=markers,
        frames=frame_dicts,
        payload=payload,
    )
