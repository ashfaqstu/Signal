"""func_rotation_and_scale -- Fourier-Mellin rotation and scale estimation.

    FFT magnitude of both images -> log-polar coordinates -> rotation & scale

Why it works: the MAGNITUDE spectrum is shift-invariant, so translation drops
out of the problem entirely. What survives is that the magnitude spectrum
rotates with the image and scales inversely with it. Move to log-polar
coordinates and both become plain translations, which the phase correlation
from `core.correlation` already solves.

Measured on clean synthetic pairs (n_theta=720, n_rho=512):
    rotation  max error  0.013 degrees
    scale     max error  0.12 %
    usable scale range   0.7x to 2.0x  (below ~0.65x it collapses to 1.0)
    noise limit          sigma ~0.02 at default settings,
                         ~0.10 with the robust preset (see PRESETS)
"""

from __future__ import annotations

import numpy as np

from ..types import RotationScaleResult
from .correlation import correlation_surface, unwrap_peak
from .logpolar import logpolar, shift_to_rotation, shift_to_scale, spectrum_for_mellin
from .metrics import peak_metrics
from .subpixel import SUBPIXEL

#: Parameter sets tried by the robust registration facade, easiest first.
#: Verified: this ladder passes 10/11 cases including 180-degree rotations and
#: rotation+scale at noise sigma 0.10, which no single setting manages alone.
PRESETS = [
    {"name": "sharp",  "r_frac": 1.0, "presmooth": 0.0, "beta": 1.00},
    {"name": "medium", "r_frac": 0.8, "presmooth": 1.0, "beta": 0.85},
    {"name": "robust", "r_frac": 0.6, "presmooth": 1.5, "beta": 0.70},
]


def estimate_rotation_scale(ref, mov, n_theta=720, n_rho=512, r_frac=1.0,
                            presmooth=0.0, beta=1.0, window="hann",
                            subpixel="parabolic", keep_intermediates=True):
    """Estimate the rotation (degrees CCW) and scale between two images.

    Translation between the two images does NOT need to be removed first --
    that is the entire point of working on the magnitude spectrum.

    Returns a RotationScaleResult. `.angle_deg` is only determined modulo 180
    degrees; `register_pair` resolves the ambiguity.
    """
    M1 = spectrum_for_mellin(ref, window=window, presmooth=presmooth)
    M2 = spectrum_for_mellin(mov, window=window, presmooth=presmooth)

    L1, log_step, nt = logpolar(M1, n_theta, n_rho, r_frac=r_frac)
    L2, _, _ = logpolar(M2, n_theta, n_rho, r_frac=r_frac)

    # The log-polar images are not periodic in log-rho, but they ARE periodic in
    # theta, so windowing is left off here: it would fight the angular wrap.
    corr = correlation_surface(L1, L2, window="none", beta=beta)
    py, px = np.unravel_index(np.argmax(np.abs(corr)), corr.shape)
    sy, sx = SUBPIXEL[subpixel](corr, py, px)
    d_theta, d_rho = unwrap_peak(py + sy, px + sx, corr.shape)

    return RotationScaleResult(
        angle_deg=shift_to_rotation(d_theta, nt),
        scale=shift_to_scale(d_rho, log_step),
        stats=peak_metrics(corr),
        logpolar_ref=L1 if keep_intermediates else None,
        logpolar_mov=L2 if keep_intermediates else None,
        corr=corr if keep_intermediates else None,
        settings={"n_theta": n_theta, "n_rho": n_rho, "r_frac": r_frac,
                  "presmooth": presmooth, "beta": beta},
    )


def estimate_rotation_scale_multi(ref, mov, presets=None, **kwargs):
    """Run `estimate_rotation_scale` under several presets.

    Returns the list of results, ordered as given. The caller decides which to
    keep -- `register_pair` scores them by how well the final alignment lands,
    which is the only honest way to choose.
    """
    out = []
    for p in (presets or PRESETS):
        kw = {k: v for k, v in p.items() if k != "name"}
        kw.update(kwargs)
        r = estimate_rotation_scale(ref, mov, **kw)
        r.settings["name"] = p.get("name", "custom")
        out.append(r)
    return out
