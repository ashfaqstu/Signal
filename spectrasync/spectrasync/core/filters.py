"""Frequency-domain filters. Every one is a multiplication in the FFT domain.

This module is the syllabus backbone of the applied features: change detection,
mask cleanup and outline extraction are all filtering, done as multiplication
by a transfer function (convolution theorem) rather than as spatial loops.

Every builder returns a mask the same shape as the image, in UNSHIFTED
(np.fft) layout, so it multiplies a raw fft2 result directly.
"""

from __future__ import annotations

import numpy as np

from ..registry import Registry
from .preprocess import as_float

FILTERS = Registry("filter")


def radial_freq(shape):
    """Radial frequency in cycles/pixel, unshifted layout. 0 at the corner."""
    H, W = shape[0], shape[1]
    ky = np.fft.fftfreq(H).reshape(-1, 1)
    kx = np.fft.fftfreq(W).reshape(1, -1)
    return np.hypot(ky, kx)


@FILTERS.register("lowpass", doc="Gaussian low-pass; `cutoff` in cycles/pixel.")
def lowpass(shape, cutoff=0.1):
    return np.exp(-0.5 * (radial_freq(shape) / max(cutoff, 1e-9)) ** 2)


@FILTERS.register("highpass", doc="1 - Gaussian low-pass.")
def highpass(shape, cutoff=0.1):
    return 1.0 - lowpass(shape, cutoff)


@FILTERS.register("bandpass", doc="Difference of Gaussians; tuned to an object size.")
def bandpass(shape, low=0.02, high=0.20):
    """Keeps structure between two scales. Rejects lighting drift (below `low`)
    and sensor noise (above `high`) in one operation -- which is exactly what a
    change detector needs before thresholding."""
    return lowpass(shape, high) - lowpass(shape, low)


@FILTERS.register("ideal_lowpass", doc="Brick-wall disc. Shows ringing (Gibbs).")
def ideal_lowpass(shape, cutoff=0.1):
    return (radial_freq(shape) <= cutoff).astype(np.float64)


def apply_filter(img, mask):
    """Filter an image with a transfer function: IFFT( FFT(img) * mask )."""
    img = as_float(img)
    if img.ndim == 3:
        return np.stack([apply_filter(img[..., c], mask)
                         for c in range(img.shape[2])], axis=-1)
    return np.real(np.fft.ifft2(np.fft.fft2(img) * mask))


def gaussian_blur(img, sigma):
    """Gaussian blur as a frequency-domain multiplication.

    The kernel is real and symmetric, therefore ZERO PHASE: it attenuates
    magnitudes without touching phase. That is why blurring one image of a pair
    barely moves the phase-correlation estimate while collapsing the peak.
    """
    if sigma <= 0:
        return as_float(img)
    H, W = img.shape[0], img.shape[1]
    ky = np.fft.fftfreq(H).reshape(-1, 1)
    kx = np.fft.fftfreq(W).reshape(1, -1)
    return apply_filter(img, np.exp(-2.0 * (np.pi * sigma) ** 2 * (ky ** 2 + kx ** 2)))


def fft_convolve(img, kernel):
    """Circular convolution via the convolution theorem."""
    img = as_float(img)
    K = np.zeros_like(img)
    kh, kw = kernel.shape
    K[:kh, :kw] = kernel
    K = np.roll(K, (-(kh // 2), -(kw // 2)), axis=(0, 1))
    return np.real(np.fft.ifft2(np.fft.fft2(img) * np.fft.fft2(K)))


def fourier_gradient(img):
    """Spatial derivatives via the DIFFERENTIATION PROPERTY of the transform.

        d/dx f(x,y)  <=>  j2pi*u * F(u,v)

    Returns (gy, gx). Used to extract an outline as |grad(mask)| -- so the
    boundary of a detected object is a transform property, not a contour-tracing
    algorithm.
    """
    img = as_float(img)
    H, W = img.shape[:2]
    ky = np.fft.fftfreq(H).reshape(-1, 1)
    kx = np.fft.fftfreq(W).reshape(1, -1)
    F = np.fft.fft2(img)
    gy = np.real(np.fft.ifft2(F * (2j * np.pi * ky)))
    gx = np.real(np.fft.ifft2(F * (2j * np.pi * kx)))
    return gy, gx


def gradient_magnitude(img, smooth=0.0):
    """|grad(img)| computed in the frequency domain. Optional pre-smoothing
    tames the ringing that a hard binary input would otherwise produce."""
    if smooth > 0:
        img = gaussian_blur(img, smooth)
    gy, gx = fourier_gradient(img)
    return np.hypot(gy, gx)


def phase_swap(magnitude_of, phase_of):
    """Reconstruct an image from ONE image's magnitude and ANOTHER's phase.

    The classic demonstration that structure lives in the phase: the result
    looks like `phase_of`, not `magnitude_of`, even though every magnitude
    value came from the other image.
    """
    magnitude_of = as_float(magnitude_of)
    phase_of = as_float(phase_of)
    mixed = (np.abs(np.fft.fft2(magnitude_of))
             * np.exp(1j * np.angle(np.fft.fft2(phase_of))))
    return np.real(np.fft.ifft2(mixed))


def mellin_highpass(shape):
    """Reddy & Chatterji emphasis filter for the Fourier-Mellin stage.

        H = (1 - X) * (2 - X),  X = cos(pi*y) * cos(pi*x)  on [-0.5, 0.5]

    Applied to the CENTRED magnitude spectrum, it suppresses the enormous
    low-frequency blob that would otherwise dominate the log-polar correlation.
    Note the centred (fftshifted) layout -- unlike the filters above.
    """
    H, W = shape[0], shape[1]
    y = np.linspace(-0.5, 0.5, H).reshape(-1, 1)
    x = np.linspace(-0.5, 0.5, W).reshape(1, -1)
    X = np.cos(np.pi * y) * np.cos(np.pi * x)
    return (1.0 - X) * (2.0 - X)
