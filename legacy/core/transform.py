"""Fourier-domain shifting and border handling.

Milestone M6/M7 in docs/02-CORE-IMPLEMENTATION.md.

The shift theorem run BACKWARDS: multiplying a spectrum by a phase ramp
translates the image, and because the ramp is defined for any real offset,
the translation may be FRACTIONAL. This is the only honest way to make a
sub-pixel ground-truth pair -- no interpolation kernel is involved.
"""

import numpy as np


def fourier_shift(img, dy, dx):
    """Translate `img` by (dy, dx) pixels -- fractional allowed.

    Circular: content that leaves one border re-enters at the opposite one.

    Steps:
      - ky = np.fft.fftfreq(H).reshape(-1, 1)   # cycles per pixel, column vec
      - kx = np.fft.fftfreq(W).reshape(1, -1)   # row vector -> broadcasts to (H, W)
      - ramp = exp(-2j*pi*(ky*dy + kx*dx))
      - out = real(ifft2(fft2(img) * ramp))

    Accept both (H, W) grayscale and (H, W, 3) colour: for colour, apply the
    SAME ramp to each channel and stack along the last axis.

    Returns
    -------
    ndarray, SAME shape as `img`, float64 and REAL -- take .real after the
    inverse transform, do not hand a complex array to the caller. Values may
    fall slightly outside the input range (Gibbs ringing overshoot); clip
    only at display time, never before a metric.

    Verified round-trip: shifting by (6.4, -3.9) then by (-6.4, 3.9)
    reproduces the interior to ~1e-2. The residual is ringing from the
    wrapped border leaking inward -- which is exactly why valid_mask exists.
    """
    raise NotImplementedError


def valid_mask(shape, dy, dx):
    """True where a shifted image holds real data rather than wrapped content.

    Blank the border strip before display or before computing any metric,
    otherwise the wrapped band poisons RMSE / PSNR / NCC.

    Steps: start from an all-True (H, W) bool array; the strip is
    ceil(|dy|)+1 rows tall and ceil(|dx|)+1 columns wide. A POSITIVE dy moved
    content down, so the invalid rows are at the TOP; a negative dy invalidates
    the BOTTOM. Same logic left/right for dx.

    Parameters
    ----------
    shape : (H, W) or (H, W, 3) -- only the first two entries are used

    Returns
    -------
    ndarray, shape (H, W), dtype BOOL. True = trustworthy pixel. Index with
    it directly (`a[mask]`) or pass it to the metrics functions. Note the +1
    of margin on each strip: the ringing reaches one pixel further than the
    shift itself.
    """
    raise NotImplementedError


def align(ref, mov, dy, dx):
    """Bring `mov` onto `ref`. Note the MINUS signs.

    `mov` sits (dy, dx) away from `ref`, so undoing it means shifting by
    (-dy, -dx). `ref` is only there for its shape -- it is never modified.

    Returns
    -------
    aligned : ndarray, same shape and dtype as `mov`, = fourier_shift(mov, -dy, -dx).
              This is the array to compare against `ref`.
    mask    : ndarray (H, W) bool, = valid_mask(mov.shape, dy, dx). Pass it
              into every metric and every overlay so the wrapped border never
              counts.

    A two-tuple: `aligned, mask = align(ref, mov, dy, dx)`.
    """
    raise NotImplementedError


def integer_shift(img, dy, dx):
    """Whole-pixel translation via np.roll -- the exact, cheap special case.

    Useful as a sanity check against fourier_shift: for integer (dy, dx) the
    two must agree to floating-point precision.

    Returns
    -------
    ndarray, same shape and dtype as `img`. Exact, with no ringing and no
    interpolation -- but only defined for whole-pixel offsets, so cast or
    round (dy, dx) to int before rolling.
    """
    raise NotImplementedError
