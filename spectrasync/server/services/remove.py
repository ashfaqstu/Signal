"""Object removal workspace service (temporal median and filters)."""

from __future__ import annotations

import numpy as np

import spectrasync as ss
from ..schemas import RemoveParams, Readout, Marker, Chart, ChartSeries
from ..media import MediaStore
from .align import ServiceResult
from .common import get_base_image, load_sequence

SAMPLE_SET = "new_image/1/*.jpg"


def run_remove(params: RemoveParams, media: MediaStore) -> ServiceResult:
    truth, pad = None, 0

    if params.source == "synthetic":
        base = get_base_image(params.base_id, media)
        img = ss.even_square(base, max_side=384)
        src = ss.SyntheticSource(
            img,
            n=params.n,
            max_shift=params.shake,
            noise=params.noise,
            mover=ss.moving_disc(radius=params.radius, value=0.03),
            seed=2,
        )
        frames = src.frames()
        truth = ss.fourier_shift(img, src.truth[0]["dy"], src.truth[0]["dx"])
        pad, mode = max(12, int(params.shake) + 6), "translation"
    elif params.source == "video":
        raw_frames = media.load_video(
            params.media_id or "",
            max_frames=params.frames,
            step=params.step,
            max_side=384,
            gray=not params.colour,
        )
        frames = [ss.even_square(f, 384) for f in raw_frames]
        pad, mode = 16, "translation"
    else:  # photos
        frames, _ = load_sequence(
            params.media_ids,
            media,
            max_side=params.max_side,
            gray=not params.colour,
            sample_glob=SAMPLE_SET,
            min_count=3,
        )
        mode = params.mode

    res = ss.remove_moving_objects(frames, reducer=params.reducer, mode=mode)

    H, W = res.output.shape[:2]
    m = ss.border_mask((H, W), pad)
    y0, y1, x0, x1 = res.stats["valid_box"] if params.source == "photos" else (0, H, 0, W)

    view = lambda a: a[y0:y1, x0:x1]

    readouts: list[Readout] = []
    if truth is not None:
        occ = (np.abs(res.aligned[0] - truth) > 0.15) & m
        before = ss.psnr(truth, res.aligned[0], occ)
        after = ss.psnr(truth, res.output, occ)
        psnr_frame = ss.psnr(truth, res.output, m)
        readouts.extend([
            Readout(key="psnr_object", label="PSNR object", value=after, unit="dB", fmt=".1f", tone="ok"),
            Readout(key="from_psnr", label="from", value=before, unit="dB", fmt=".1f"),
            Readout(key="psnr_frame", label="PSNR frame", value=psnr_frame, unit="dB", fmt=".1f"),
            Readout(key="frames", label="frames", value=res.n_frames, fmt="d"),
        ])
    elif params.source == "photos":
        locked = res.stats.get("n_locked", res.n_frames)
        cov = 100.0 * (y1 - y0) * (x1 - x0) / max(H * W, 1)
        readouts.extend([
            Readout(key="frames", label="frames", value=res.n_frames, fmt="d"),
            Readout(key="locked", label="locked", value=f"{locked}/{res.n_frames}"),
            Readout(key="plate", label="plate", value=f"{x1 - x0}×{y1 - y0}"),
            Readout(key="coverage", label="coverage", value=cov, unit="%", fmt=".0f"),
        ])
    else:
        readouts.append(Readout(key="frames", label="frames", value=res.n_frames, fmt="d"))

    layers = [
        ("Frame 0", "Input", "image", view(res.aligned[0]), "inferno"),
        ("Mid frame", "Input", "image", view(res.aligned[len(res.aligned) // 2]), "inferno"),
        ("Plate", "Result", "image", view(res.output), "inferno"),
    ]

    if params.compare_filters:
        out_filters = ss.compare_temporal_filters(res.aligned)
        for name, img in out_filters.items():
            layers.append((name, "Filters", "image", view(img), "inferno"))

    # Pixel disturbance analysis
    region = ss.mask_from_box((H, W), (y0, y1, x0, x1))
    cy, cx = ss.most_disturbed_pixel(res.aligned, res.output, mask=region & m)
    sig, freq, spec = ss.pixel_timeseries(res.aligned, cy, cx)

    markers = [
        Marker(layer="Plate", type="crosshair", x=float(cx - x0), y=float(cy - y0))
    ]

    med_val = float(np.median(sig))
    pixel_series = [
        ChartSeries(name="intensity", values=[float(v) for v in sig], role="primary"),
        ChartSeries(name="median", values=[med_val] * len(sig), role="reference"),
    ]
    charts = [
        Chart(
            id="pixel_timeseries",
            kind="line",
            x=[float(i) for i in range(len(sig))],
            series=pixel_series,
        ),
        Chart(
            id="pixel_spectrum",
            kind="line",
            x=[round(float(f), 3) for f in freq],
            series=[ChartSeries(name="|FFT|", values=[float(s) for s in spec], role="primary")],
        ),
    ]

    shifts = res.shifts if hasattr(res, "shifts") and res.shifts else [(0.0, 0.0)] * len(res.aligned)
    confidences = res.stats.get("confidence", [None] * len(res.aligned))

    frame_dicts = []
    for i, arr in enumerate(res.aligned):
        dy, dx = shifts[i] if i < len(shifts) else (0.0, 0.0)
        conf = confidences[i] if i < len(confidences) else None
        frame_dicts.append({
            "index": i,
            "name": f"frame_{i}",
            "array": view(arr),
            "meta": {
                "dy": float(dy),
                "dx": float(dx),
                "confidence": float(conf) if conf is not None else None,
            },
        })

    payload = {
        "aligned": res.aligned,
        "valid_box": (y0, y1, x0, x1),
        "output": res.output,
    }

    return ServiceResult(
        layers=layers,
        readouts=readouts,
        markers=markers,
        charts=charts,
        frames=frame_dicts,
        payload=payload,
    )
