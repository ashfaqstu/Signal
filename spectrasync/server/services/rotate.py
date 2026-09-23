"""Rotation & scale workspace service (Fourier-Mellin transform)."""

from __future__ import annotations

import numpy as np

import spectrasync as ss
from ..schemas import RotateParams, Readout, Marker
from ..media import MediaStore
from .align import ServiceResult
from .common import get_base_image, load_sequence, frame_pair_from_video

SAMPLE_PAIR = "new_image/3/*.jpg"


def run_rotate(params: RotateParams, media: MediaStore) -> ServiceResult:
    truth = None

    if params.source == "pair":
        photos, _ = load_sequence(
            [params.a_id or "", params.b_id or ""],
            media,
            max_side=params.max_side,
            gray=False,
            sample_glob=SAMPLE_PAIR,
            min_count=2,
        )
        ref_c, mov_c = (ss.to_even(p) for p in photos[:2])
        ref_full, mov_full = ss.to_gray(ref_c), ss.to_gray(mov_c)
        ref, mov = ss.centre_square(ref_full), ss.centre_square(mov_full)
    elif params.source == "video":
        ref_c, mov_c, _ = frame_pair_from_video(
            params.media_id,
            params.a_index,
            params.b_index,
            media,
            max_side=params.max_side,
            gray=False,
        )
        ref_c, mov_c = ss.to_even(ref_c), ss.to_even(mov_c)
        ref_full, mov_full = ss.to_gray(ref_c), ss.to_gray(mov_c)
        ref, mov = ss.centre_square(ref_full), ss.centre_square(mov_full)
    else:  # synthetic
        base = get_base_image(params.base_id, media)
        ref = ss.even_square(base, max_side=384)
        mov = ss.warp_similarity(ref, params.angle, params.scale, params.dy, params.dx)
        if params.noise > 0:
            mov = ss.add_noise(mov, params.noise)
        ref_c, mov_c, ref_full, mov_full = ref, mov, ref, mov
        truth = (params.angle, params.scale)

    presets = None if params.robust else [ss.PRESETS[0]]
    r = ss.register_similarity(
        ref,
        mov,
        presets=presets,
        n_theta=params.n_theta,
        n_rho=params.n_rho,
    )

    ang = (r.angle_deg + 180.0) % 360.0 - 180.0
    aligned = ss.apply_registration(mov_c, r.angle_deg, r.scale, r.dy, r.dx)
    valid = ss.alignment_valid_mask(ref_full.shape, r.angle_deg, r.scale, r.dy, r.dx)
    aligned_g = ss.to_gray(aligned)

    vm = valid[..., None] if aligned.ndim == 3 else valid
    b_restored = np.where(vm, aligned, 0.0)

    ov_fn = ss.OVERLAYS[params.overlay] if params.overlay in ss.OVERLAYS else ss.OVERLAYS["anaglyph"]
    ov_before = ov_fn(ref_full, mov_full)
    ov_after = ov_fn(ref_full, aligned_g) * (valid[..., None] if params.overlay == "anaglyph" else valid)

    ncc_before = ss.ncc(ref_full, mov_full, valid)
    ncc_after = ss.ncc(ref_full, aligned_g, valid)

    rs = ss.estimate_rotation_scale(ref, mov, n_theta=params.n_theta, n_rho=params.n_rho)
    lp_a = rs.logpolar_ref
    lp_b = rs.logpolar_mov
    rho_theta_corr = np.fft.fftshift(rs.corr)

    readouts: list[Readout] = [
        Readout(key="rotation", label="rotation", value=ang, unit="°", fmt="+.2f"),
        Readout(key="scale", label="scale", value=r.scale, unit="×", fmt=".4f"),
        Readout(key="dy", label="dy", value=r.dy, unit="px", fmt="+.1f"),
        Readout(key="dx", label="dx", value=r.dx, unit="px", fmt="+.1f"),
        Readout(key="peak", label="peak", value=r.stats.peak, fmt=".3f"),
        Readout(key="psr", label="PSR", value=r.stats.psr, fmt=".1f"),
        Readout(key="ratio", label="ratio", value=r.stats.ratio, fmt=".2f"),
        Readout(key="ncc_before", label="NCC before", value=ncc_before, fmt=".3f"),
        Readout(key="ncc_after", label="NCC after", value=ncc_after, fmt=".3f"),
    ]

    if truth:
        a_err = ss.angle_error_deg(ang, truth[0])
        s_err = ss.percent_error(r.scale, truth[1])
        readouts.extend([
            Readout(key="err_deg", label="err °", value=a_err, unit="°", fmt=".3f"),
            Readout(key="err_scale", label="err scale", value=s_err, unit="%", fmt=".2f"),
        ])

    layers = [
        ("A", "Input", "image", ref_c, "inferno"),
        ("B", "Input", "image", mov_c, "inferno"),
        ("B restored", "Result", "image", b_restored, "inferno"),
        ("Overlay before", "Analysis", "image", ov_before, "inferno"),
        ("Overlay after", "Analysis", "image", ov_after, "inferno"),
        ("log-polar A", "Frequency", "heatmap", lp_a, "inferno"),
        ("log-polar B", "Frequency", "heatmap", lp_b, "inferno"),
        ("ρθ correlation", "Frequency", "heatmap", rho_theta_corr, "inferno"),
    ]

    return ServiceResult(
        layers=layers,
        readouts=readouts,
        verdict=r.stats.verdict,
        payload=None,
    )
