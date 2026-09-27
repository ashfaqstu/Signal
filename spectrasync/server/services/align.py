"""Translation workspace service (phase correlation)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import numpy as np

import spectrasync as ss
from ..schemas import AlignParams, Readout, Marker, Chart, Table
from ..encode import log_spectrum, phase_image
from ..media import MediaStore
from .common import get_base_image, load_pair, frame_pair_from_video


@dataclass
class ServiceResult:
    layers: list[tuple[str, str, str, np.ndarray, str]]  # name, group, kind, array, cmap
    readouts: list[Readout]
    markers: list[Marker] = field(default_factory=list)
    frames: list[dict[str, Any]] = field(default_factory=list)
    charts: list[Chart] = field(default_factory=list)
    table: Table | None = None
    verdict: str | None = None
    flags: list[str] = field(default_factory=list)
    payload: Any = None


def run_align(params: AlignParams, media: MediaStore) -> ServiceResult:
    """Measure on luma, show in colour -- the same UX as the rotate service."""
    truth = None

    if params.source == "synthetic":
        base = get_base_image(params.base_id, media, fallback="media/01_translation/base.jpg",
                              colour=True)
        ref_c = ss.even_square(base, max_side=min(params.max_side, 512))
        mov_c = ss.fourier_shift(ref_c, params.dy, params.dx)
        if params.noise > 0:
            ref_c = ss.add_noise(ref_c, params.noise)
            mov_c = ss.add_noise(mov_c, params.noise)
        truth = (params.dy, params.dx)
    elif params.source == "video":
        ref_c, mov_c, _ = frame_pair_from_video(
            params.media_id,
            params.a_index,
            params.b_index,
            media,
            max_side=params.max_side,
            gray=False,
        )
    else:  # pair
        ref_c, mov_c, _ = load_pair(
            params.a_id,
            params.b_id,
            media,
            max_side=params.max_side,
            gray=False,
            sample_glob="media/01_translation/pair/*.jpg",
        )

    ref, mov = ss.to_gray(ref_c), ss.to_gray(mov_c)
    mask = ss.lowpass(ref.shape, params.lowpass) if params.lowpass > 0 else None
    r = ss.phase_correlation(
        ref,
        mov,
        window=params.window,
        subpixel=params.subpixel,
        beta=params.beta,
        spectral_mask=mask,
    )

    aligned_c = ss.apply_registration(mov_c, 0.0, 1.0, r.dy, r.dx)
    aligned = ss.to_gray(aligned_c)
    valid = ss.alignment_valid_mask(ref.shape, 0.0, 1.0, r.dy, r.dx)
    vm = valid[..., None] if aligned_c.ndim == 3 else valid
    b_restored = np.where(vm, aligned_c, 0.0)

    ov_fn = ss.OVERLAYS[params.overlay] if params.overlay in ss.OVERLAYS else ss.OVERLAYS["anaglyph"]
    kw = (
        {"tile": params.tile}
        if params.overlay == "checkerboard"
        else ({"alpha": params.alpha} if params.overlay == "blend" else {})
    )
    overlay_before = ov_fn(ref, mov, **kw)
    overlay_img = ov_fn(ref, aligned, **kw) * (valid[..., None] if params.overlay == "anaglyph" else valid)
    psnr_before = ss.psnr(ref, mov, valid)
    psnr_after = ss.psnr(ref, aligned, valid)

    R, F1, F2 = ss.cross_power_spectrum(ref, mov, window=params.window, beta=params.beta)
    f1_log = log_spectrum(F1)
    f2_log = log_spectrum(F2)
    r_phase = phase_image(R)
    corr_surface = np.fft.fftshift(r.corr)

    # Argmax marker on correlation surface
    py, px = np.unravel_index(np.argmax(np.abs(corr_surface)), corr_surface.shape)
    markers = [
        Marker(layer="r(x,y)", type="crosshair", x=float(px), y=float(py), w=0, h=0)
    ]

    readouts: list[Readout] = [
        Readout(key="dy", label="dy", value=r.dy, unit="px", fmt="+.3f"),
        Readout(key="dx", label="dx", value=r.dx, unit="px", fmt="+.3f"),
        Readout(key="peak", label="peak", value=r.stats.peak, fmt=".3f"),
        Readout(key="psr", label="PSR", value=r.stats.psr, fmt=".1f"),
        Readout(key="ratio", label="ratio", value=r.stats.ratio, fmt=".2f"),
        Readout(key="psnr_before", label="PSNR before", value=psnr_before, unit="dB", fmt=".1f"),
        Readout(key="psnr_after", label="PSNR after", value=psnr_after, unit="dB", fmt=".1f"),
    ]

    if truth:
        readouts.extend([
            Readout(key="dy_true", label="dy true", value=truth[0], unit="px", fmt="+.2f", tone="muted"),
            Readout(key="dx_true", label="dx true", value=truth[1], unit="px", fmt="+.2f", tone="muted"),
            Readout(key="err_dy", label="err dy", value=abs(r.dy - truth[0]), unit="px", fmt=".3f"),
            Readout(key="err_dx", label="err dx", value=abs(r.dx - truth[1]), unit="px", fmt=".3f"),
        ])

    flags = ["inverted_contrast"] if r.stats.polarity < 0 else []

    layers = [
        ("A", "Input", "image", ref_c, "inferno"),
        ("B", "Input", "image", mov_c, "inferno"),
        ("B restored", "Result", "image", b_restored, "inferno"),
        ("Overlay before", "Analysis", "image", overlay_before, "inferno"),
        ("Overlay", "Analysis", "image", overlay_img, "inferno"),
        ("|F₁|", "Frequency", "heatmap", f1_log, "inferno"),
        ("|F₂|", "Frequency", "heatmap", f2_log, "inferno"),
        ("∠R", "Frequency", "heatmap", r_phase, "twilight"),
        ("r(x,y)", "Frequency", "heatmap", corr_surface, "inferno"),
    ]

    return ServiceResult(
        layers=layers,
        readouts=readouts,
        markers=markers,
        verdict=r.stats.verdict,
        flags=flags,
        payload=None,
    )
