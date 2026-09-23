"""Theory / How It Works workspace service (spectrum walkthrough)."""

from __future__ import annotations

import numpy as np

import spectrasync as ss
from ..schemas import SpectrumParams, Readout, Marker
from ..encode import log_spectrum, phase_image
from ..media import MediaStore
from .align import ServiceResult
from .common import get_base_image


def run_spectrum(params: SpectrumParams, media: MediaStore) -> ServiceResult:
    base = get_base_image(params.base_id, media, max_side=320)
    ref = ss.even_square(base, max_side=320)
    mov = ss.fourier_shift(ref, params.dy, params.dx)

    R, F1, F2 = ss.cross_power_spectrum(ref, mov)
    r = ss.phase_correlation(ref, mov)

    aligned_mov = ss.apply_registration(mov, 0.0, 1.0, r.dy, r.dx)
    residual = ss.difference(ref, aligned_mov)

    # 20 deg, 1.15x warp for log-polar demonstration
    warped = ss.warp_similarity(ref, 20.0, 1.15)
    rs = ss.estimate_rotation_scale(ref, warped)

    f1_log = log_spectrum(F1)
    f2_log = log_spectrum(F2)
    phase_r = phase_image(R)
    corr_surface = np.fft.fftshift(r.corr)

    # Marker for correlation peak
    py, px = np.unravel_index(np.argmax(np.abs(corr_surface)), corr_surface.shape)
    markers = [
        Marker(layer="r(x,y)", type="crosshair", x=float(px), y=float(py))
    ]

    layers = [
        ("f₁ | f₂", "Theory", "image", np.hstack([ref, mov]), "inferno"),
        ("|F₁|", "Theory", "heatmap", f1_log, "inferno"),
        ("|F₂|", "Theory", "heatmap", f2_log, "inferno"),
        ("phase swap", "Theory", "image", ss.phase_swap(ref, mov), "inferno"),
        ("∠R", "Theory", "heatmap", phase_r, "twilight"),
        ("r(x,y)", "Theory", "heatmap", corr_surface, "inferno"),
        ("residual", "Theory", "image", residual, "inferno"),
        ("log-polar A", "Theory", "heatmap", rs.logpolar_ref, "inferno"),
        ("log-polar B", "Theory", "heatmap", rs.logpolar_mov, "inferno"),
        ("ρθ correlation", "Theory", "heatmap", np.fft.fftshift(rs.corr), "inferno"),
    ]

    readouts = [
        Readout(key="dy", label="dy", value=r.dy, unit="px", fmt="+.3f"),
        Readout(key="dx", label="dx", value=r.dx, unit="px", fmt="+.3f"),
        Readout(key="dy_true", label="dy true", value=params.dy, unit="px", fmt="+.2f", tone="muted"),
        Readout(key="dx_true", label="dx true", value=params.dx, unit="px", fmt="+.2f", tone="muted"),
    ]

    return ServiceResult(
        layers=layers,
        readouts=readouts,
        markers=markers,
        verdict=r.stats.verdict,
        payload=None,
    )
