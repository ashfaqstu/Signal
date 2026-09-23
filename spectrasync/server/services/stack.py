"""Stacking workspace service (multi-frame noise reduction)."""

from __future__ import annotations

import os
from pathlib import Path
import numpy as np

import spectrasync as ss
from ..schemas import StackParams, Readout, Marker, Chart, ChartSeries, Table
from ..media import MediaStore
from .align import ServiceResult
from .common import get_base_image, load_sequence
from .. import config

SAMPLE_SET = "new_image/2_noisy/set_1/*.jpg"
SAMPLE_CLEAN = "new_image/2_noisy/_clean/set_1.png"
COMPARE = ["mean", "median", "sigma_clip", "trimmed_mean", "fourier_snr"]


def run_stack(params: StackParams, media: MediaStore) -> ServiceResult:
    clean_al = None
    clean = None

    if params.source == "synthetic":
        base = get_base_image(params.base_id, media)
        img = ss.even_square(base, max_side=384)
        src = ss.SyntheticSource(
            img,
            n=params.n,
            max_shift=params.shift,
            noise=params.noise,
            seed=1,
        )
        frames = src.frames()
        truth = ss.fourier_shift(img, src.truth[0]["dy"], src.truth[0]["dx"])
        pad = max(12, int(params.shift) + 6)
        m = ss.border_mask(img.shape, pad)

        res = ss.stack(frames, reducer=params.reducer, align=params.align)
        clean_al = truth
        raw = res.aligned[0]
        single = ss.psnr(truth, raw, m)
        got = ss.psnr(truth, res.output, m)
        n_raw = ss.estimate_noise(raw, m)
        n_out = ss.estimate_noise(res.output, m)
        view = lambda a: a
    elif params.source == "video":
        frames = media.load_video(
            params.media_id or "",
            max_frames=params.frames,
            step=params.step,
            max_side=params.max_side,
            gray=not params.colour,
        )
        res = ss.stack(frames, reducer=params.reducer, align=params.align)
        H, W = res.output.shape[:2]
        y0, y1, x0, x1 = res.stats["valid_box"]
        box = ss.mask_from_box((H, W), (y0, y1, x0, x1))
        view = lambda a: a[y0:y1, x0:x1]
        m = box
        raw = res.aligned[0]
        n_raw = ss.estimate_noise(raw, m)
        n_out = ss.estimate_noise(res.output, m)
        single, got = None, None
    else:  # photos
        frames, names = load_sequence(
            params.media_ids,
            media,
            max_side=params.max_side,
            gray=not params.colour,
            sample_glob=SAMPLE_SET,
            min_count=2,
        )

        clean_path = None
        if params.clean_id:
            m_clean = media.get(params.clean_id)
            if m_clean and m_clean.path.exists():
                clean_path = str(m_clean.path)
        elif not params.media_ids:
            fallback_clean = config.ROOT / SAMPLE_CLEAN
            if fallback_clean.exists():
                clean_path = str(fallback_clean)

        if clean_path:
            clean = (ss.load_rgb if params.colour else ss.load_gray)(clean_path, max_side=params.max_side)

        res = ss.stack(frames, reducer=params.reducer, align=params.align)
        H, W = res.output.shape[:2]
        y0, y1, x0, x1 = res.stats["valid_box"]
        box = ss.mask_from_box((H, W), (y0, y1, x0, x1))
        view = lambda a: a[y0:y1, x0:x1]

        m = box
        if clean is not None:
            clean_al, m = ss.align_reference_to_output(res.output, clean, valid=box)

        raw = res.aligned[0]
        n_raw = ss.estimate_noise(raw, m)
        n_out = ss.estimate_noise(res.output, m)

        if clean_al is not None:
            single = ss.psnr(clean_al, raw, m)
            got = ss.psnr(clean_al, res.output, m)
        else:
            single, got = None, None

    locked = res.stats.get("n_locked")
    theory_gain = ss.theoretical_gain_db(res.n_frames, params.reducer)

    readouts: list[Readout] = [
        Readout(key="frames", label="frames", value=res.n_frames, fmt="d"),
        Readout(key="locked", label="locked", value=f"{locked}/{res.n_frames}" if locked is not None else "-"),
        Readout(key="theory", label="theory", value=theory_gain, unit="dB", fmt="+.2f"),
    ]

    if clean_al is not None and got is not None and single is not None:
        readouts.extend([
            Readout(key="psnr", label="PSNR", value=got, unit="dB", fmt=".2f"),
            Readout(key="from_psnr", label="from", value=single, unit="dB", fmt=".2f"),
            Readout(key="gain", label="gain", value=got - single, unit="dB", fmt="+.2f", tone="ok"),
        ])
    else:
        readouts.extend([
            Readout(key="sigma_out", label="σ out", value=n_out, fmt=".3f"),
            Readout(key="sigma_raw", label="σ raw", value=n_raw, fmt=".3f"),
            Readout(key="sigma_ratio", label="σ ratio", value=n_raw / max(n_out, 1e-9), unit="×", fmt=".1f"),
        ])

    raw_view = view(raw)
    stacked_view = view(res.output)
    if clean_al is not None:
        residual_view = view(np.abs(ss.to_gray(res.output) - ss.to_gray(clean_al)) * m)
        residual_name = "Residual"
    else:
        residual_view = view(np.abs(ss.to_gray(raw) - ss.to_gray(res.output)))
        residual_name = "Removed"

    layers = [
        ("Raw", "Input", "image", raw_view, "inferno"),
        ("Stacked", "Result", "image", stacked_view, "inferno"),
        (residual_name, "Analysis", "image", residual_view, "inferno"),
    ]

    # Comparison across reducers
    charts = []
    table = None
    if params.compare:
        rows_data = []
        table_rows = []
        theory_vals = []
        gain_vals = []
        reducer_names = []

        for name in COMPARE:
            out = ss.reduce(res.aligned, name)
            layers.append((name, "Reducers", "image", view(out), "inferno"))

            t_gain = round(ss.theoretical_gain_db(res.n_frames, name), 2)
            noise_est = round(ss.estimate_noise(out, m), 4)
            theory_vals.append(t_gain)
            reducer_names.append(name)

            if clean_al is not None and single is not None:
                p = ss.psnr(clean_al, out, m)
                g = round(p - single, 2)
                gain_vals.append(g)
                table_rows.append([name, noise_est, t_gain, round(p, 2), g])
            else:
                table_rows.append([name, noise_est, t_gain])

        table_cols = ["reducer", "noise σ", "theory (dB)"]
        if clean_al is not None:
            table_cols.extend(["PSNR (dB)", "gain (dB)"])

        table = Table(columns=table_cols, rows=table_rows)

        series = [ChartSeries(name="theory dB", values=theory_vals, role="reference")]
        if gain_vals:
            series.insert(0, ChartSeries(name="gain dB", values=gain_vals, role="primary"))

        charts.append(Chart(id="reducer_comparison", kind="bar", x=reducer_names, series=series))

    # Frame references for timeline / filmstrip
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
                "locked": bool(conf >= 1.5) if conf is not None else False,
            },
        })

    return ServiceResult(
        layers=layers,
        readouts=readouts,
        charts=charts,
        table=table,
        frames=frame_dicts,
        verdict="locked" if (locked is not None and locked > 0) else None,
        payload=res,
    )
