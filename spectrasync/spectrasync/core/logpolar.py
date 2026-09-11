"""Log-polar resampling -- the coordinate change that makes Fourier-Mellin work.

In log-polar coordinates (log rho, theta):

    a ROTATION of the image becomes a SHIFT along theta
    a SCALING  of the image becomes a SHIFT along log rho

So once both magnitude spectra are resampled onto a log-polar grid, rotation and
scale are recovered by the SAME phase-correlation function used for translation.
That is the whole trick.

Only HALF the angular range is used (0 to pi). The magnitude spectrum of a real
image is centrosymmetric, so theta and theta+180 are indistinguishable here --
the ambiguity is resolved later by the registration facade.
"""

from __future__ import annotations

import numpy as np

from .transform import bilinear_sample


def logpolar(img, n_theta=720, n_rho=512, r_min=1.0, r_frac=1.0):
    """Resample a CENTRED image onto a log-polar grid.

    Parameters
    ----------
    n_theta : angular bins over [0, pi). Sets the rotation resolution:
              180 / n_theta degrees per bin.
    n_rho   : log-radius bins. Sets the scale resolution.
    r_frac  : fraction of the maximum radius to use. Below 1.0 this discards the
              outermost (highest-frequency, noisiest) ring of the spectrum,
              which buys noise robustness at the cost of scale range.

    Returns (logpolar_image, log_step, n_theta) where `log_step` is the natural
    log of the radius ratio per bin -- needed to convert a shift back to a scale.
    """
    img = np.asarray(img, dtype=np.float64)
    H, W = img.shape[:2]
    cy, cx = H / 2.0, W / 2.0
    r_max = min(cy, cx) * float(r_frac)
    if r_max <= r_min:
        raise ValueError("r_frac is too small for this image size")

    log_step = np.log(r_max / r_min) / n_rho
    theta = np.linspace(0.0, np.pi, n_theta, endpoint=False).reshape(-1, 1)
    rho = r_min * np.exp(np.arange(n_rho) * log_step).reshape(1, -1)

    ys = cy + rho * np.sin(theta)
    xs = cx + rho * np.cos(theta)
    return bilinear_sample(img, ys, xs), float(log_step), int(n_theta)


def shift_to_rotation(d_theta, n_theta):
    """Convert a log-polar row shift into degrees.

    Calibrated empirically against known warps: the sign is DIRECT (a rotation
    of +12 degrees produces a +12 degree estimate).
    """
    return float(d_theta) * (180.0 / float(n_theta))


def shift_to_scale(d_rho, log_step):
    """Convert a log-polar column shift into a scale factor.

    The sign is INVERTED: magnifying an image by s shrinks its magnitude
    spectrum by 1/s, so the log-radius shift is -log(s). Verified against known
    warps (a true scale of 1.20 gives a raw estimate of 0.83 before inversion).
    """
    return float(np.exp(-float(d_rho) * float(log_step)))


def spectrum_for_mellin(img, window="hann", presmooth=0.0, log_scale=True):
    """The centred, emphasised magnitude spectrum that goes into `logpolar`.

    Steps: optional pre-smoothing (noise control) -> window -> |FFT| -> fftshift
    -> log1p compression -> Reddy & Chatterji high-pass emphasis.
    """
    from .filters import gaussian_blur, mellin_highpass
    from .windows import window2d

    a = np.asarray(img, dtype=np.float64)
    if presmooth and presmooth > 0:
        a = gaussian_blur(a, presmooth)
    a = a - a.mean()
    if window and window != "none":
        a = a * window2d(a.shape, window)
    mag = np.abs(np.fft.fftshift(np.fft.fft2(a)))
    if log_scale:
        mag = np.log1p(mag)
    return mag * mellin_highpass(a.shape)
