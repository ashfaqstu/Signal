"""Geometric transforms: sub-pixel shifting, similarity warping, resampling.

`fourier_shift` is the shift theorem run FORWARDS -- the same equation that
measures the motion also renders it. `warp_similarity` needs real resampling,
so bilinear interpolation is written out here rather than pulled from scipy.
"""

from __future__ import annotations

import numpy as np

from .preprocess import as_float


def bilinear_sample(img, ys, xs):
    """Sample `img` at fractional coordinates (ys, xs) with edge clamping.

    Works channel-wise for (H, W, C) input. This is the only interpolator in
    the project, so any resampling artefact has exactly one place to look.
    """
    img = as_float(img)
    H, W = img.shape[:2]
    y0 = np.floor(ys).astype(int)
    x0 = np.floor(xs).astype(int)
    wy = ys - y0
    wx = xs - x0
    y0c, y1c = np.clip(y0, 0, H - 1), np.clip(y0 + 1, 0, H - 1)
    x0c, x1c = np.clip(x0, 0, W - 1), np.clip(x0 + 1, 0, W - 1)
    if img.ndim == 3:
        wy = wy[..., None]
        wx = wx[..., None]
    return ((1 - wy) * (1 - wx) * img[y0c, x0c]
            + (1 - wy) * wx * img[y0c, x1c]
            + wy * (1 - wx) * img[y1c, x0c]
            + wy * wx * img[y1c, x1c])


def fourier_shift(img, dy, dx):
    """Translate by (dy, dx) pixels, fractional allowed, via the shift theorem.

        g = IFFT( FFT(f) * exp(-j2pi(k*dy/H + l*dx/W)) )

    Content moves by (+dy, +dx). The shift is CIRCULAR -- content wraps around
    the borders and can ring slightly at strong edges. Use `valid_mask` to blank
    the wrapped strip before display or metrics.
    """
    img = as_float(img)
    H, W = img.shape[:2]
    ky = np.fft.fftfreq(H).reshape(-1, 1)
    kx = np.fft.fftfreq(W).reshape(1, -1)
    ramp = np.exp(-2j * np.pi * (ky * dy + kx * dx))
    if img.ndim == 2:
        return np.real(np.fft.ifft2(np.fft.fft2(img) * ramp))
    return np.stack(
        [np.real(np.fft.ifft2(np.fft.fft2(img[..., c]) * ramp))
         for c in range(img.shape[2])], axis=-1)


def warp_similarity(img, angle_deg=0.0, scale=1.0, dy=0.0, dx=0.0):
    """Rotate CCW about the image centre, scale, then translate.

    Implemented by inverse mapping: for every output pixel, work out where it
    came from in the input and sample there. That is the only way to get an
    output with no holes.

    This is the exact inverse-pair of `unwarp_similarity`, which is what makes
    the registration facade's "undo the rotation and scale" step exact.
    """
    img = as_float(img)
    H, W = img.shape[:2]
    cy, cx = (H - 1) / 2.0, (W - 1) / 2.0
    th = np.deg2rad(angle_deg)
    c, s = np.cos(th), np.sin(th)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
    y = yy - cy - dy
    x = xx - cx - dx
    ys = (c * y - s * x) / scale + cy
    xs = (s * y + c * x) / scale + cx
    return bilinear_sample(img, ys, xs)


def unwarp_similarity(img, angle_deg=0.0, scale=1.0):
    """Undo a rotation and scale about the centre (translation handled after)."""
    return warp_similarity(img, -angle_deg, 1.0 / scale)


def rotate(img, angle_deg):
    """Rotate CCW about the centre. Convenience wrapper."""
    return warp_similarity(img, angle_deg=angle_deg)


def rescale(img, scale):
    """Scale about the centre, output shape unchanged. Convenience wrapper."""
    return warp_similarity(img, scale=scale)


def valid_mask(shape, dy, dx):
    """True where `fourier_shift(img, dy, dx)` holds real data, not wrapped content.

    NOTE the direction. This describes the result of shifting BY (dy, dx).
    Alignment shifts by the NEGATIVE of the estimate, so pairing this with a
    raw estimate blanks the wrong two edges -- measured cost on a real photo:
    a reported 18.9 dB instead of the true 88.8 dB. Use `alignment_valid_mask`
    for anything that went through `apply_registration`.
    """
    H, W = shape[0], shape[1]
    m = np.ones((H, W), dtype=bool)
    iy = int(np.ceil(abs(dy))) + 1
    ix = int(np.ceil(abs(dx))) + 1
    if dy > 0:
        m[:iy, :] = False
    elif dy < 0:
        m[H - iy:, :] = False
    if dx > 0:
        m[:, :ix] = False
    elif dx < 0:
        m[:, W - ix:] = False
    return m


def centre_crop(img, frac=0.75):
    """Central crop -- the region that stays valid through any modest warp."""
    H, W = img.shape[:2]
    h, w = int(H * frac), int(W * frac)
    y0, x0 = (H - h) // 2, (W - w) // 2
    return img[y0:y0 + h, x0:x0 + w]


def valid_box(mask):
    """An axis-aligned box (y0, y1, x0, x1) lying entirely inside `mask`.

    Greedy: keep trimming whichever edge has the largest fraction of invalid
    pixels. For a translation-only stack the common valid region IS a rectangle
    and this finds it exactly; with rotation it returns a large inscribed box.
    Crop with img[y0:y1, x0:x1].
    """
    m = np.asarray(mask, dtype=bool)
    y0, y1, x0, x1 = 0, m.shape[0], 0, m.shape[1]
    while y1 > y0 and x1 > x0:
        sub = m[y0:y1, x0:x1]
        if sub.all():
            return y0, y1, x0, x1
        bad = [(~sub[0]).mean(), (~sub[-1]).mean(),
               (~sub[:, 0]).mean(), (~sub[:, -1]).mean()]
        k = int(np.argmax(bad))
        if k == 0:
            y0 += 1
        elif k == 1:
            y1 -= 1
        elif k == 2:
            x0 += 1
        else:
            x1 -= 1
    return 0, 0, 0, 0


def border_mask(shape, margin):
    """Boolean mask, True everywhere except within `margin` px of an edge.

    The standard "ignore the border" mask for measuring a synthetic shift or
    warp: content near the edge is unreliable there (a circular shift wraps
    it, a rotation/scale can sample outside the source image). `margin=0`
    returns an all-True mask.
    """
    H, W = int(shape[0]), int(shape[1])
    margin = max(0, int(margin))
    m = np.zeros((H, W), dtype=bool)
    m[margin:H - margin, margin:W - margin] = True
    return m


def mask_from_box(shape, box):
    """Boolean mask, True inside the axis-aligned box (y0, y1, x0, x1).

    The display/measurement counterpart of `valid_box`: turn the box it
    returns back into a mask the same shape as the image, for slicing or for
    combining with another mask via `&`.
    """
    H, W = int(shape[0]), int(shape[1])
    y0, y1, x0, x1 = box
    m = np.zeros((H, W), dtype=bool)
    m[y0:y1, x0:x1] = True
    return m


def apply_registration(mov, angle_deg, scale, dy, dx):
    """Bring `mov` onto the reference using a full similarity estimate.

    ORDER MATTERS and is fixed project-wide:
        1. un-rotate / un-scale about the centre
        2. then shift by (-dy, -dx)
    `dy, dx` are measured in the UN-ROTATED frame, which is exactly what the
    registration facade reports.
    """
    out = mov
    if abs(angle_deg) > 1e-12 or abs(scale - 1.0) > 1e-12:
        out = unwarp_similarity(out, angle_deg, scale)
    if abs(dy) > 1e-12 or abs(dx) > 1e-12:
        out = fourier_shift(out, -dy, -dx)
    return out


def alignment_valid_mask(shape, angle_deg=0.0, scale=1.0, dy=0.0, dx=0.0,
                         erode=1):
    """True where `apply_registration(mov, angle, scale, dy, dx)` holds real data.

    Two sources of invalid pixels, handled separately because they behave
    differently:

    1. the un-warp samples OUTSIDE the source image (rotation / scale), found
       from the sampling coordinates rather than from pixel values;
    2. the sub-pixel shift is CIRCULAR, so a band of width |dy| x |dx| wraps
       around from the opposite edge.

    The shift is applied after the warp, so the warp mask is translated too --
    with zero fill, not a wrap.
    """
    H, W = int(shape[0]), int(shape[1])
    m = np.ones((H, W), dtype=bool)

    if abs(angle_deg) > 1e-12 or abs(scale - 1.0) > 1e-12:
        cy, cx = (H - 1) / 2.0, (W - 1) / 2.0
        th = np.deg2rad(-angle_deg)          # unwarp_similarity negates
        inv_s = 1.0 / (1.0 / scale)          # ... and inverts the scale
        c, sn = np.cos(th), np.sin(th)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
        y, x = yy - cy, xx - cx
        ys = (c * y - sn * x) * inv_s + cy
        xs = (sn * y + c * x) * inv_s + cx
        m &= (ys >= 0) & (ys <= H - 1) & (xs >= 0) & (xs <= W - 1)

    iy, ix = int(np.floor(-dy)), int(np.floor(-dx))
    if iy or ix:                              # translate the warp mask, zero fill
        shifted = np.zeros_like(m)
        ys0, ys1 = max(0, iy), min(H, H + iy)
        xs0, xs1 = max(0, ix), min(W, W + ix)
        shifted[ys0:ys1, xs0:xs1] = m[ys0 - iy:ys1 - iy, xs0 - ix:xs1 - ix]
        m = shifted
    m &= valid_mask((H, W), -dy, -dx)         # the circular-wrap band

    for _ in range(int(erode)):
        m &= (np.roll(m, 1, 0) & np.roll(m, -1, 0)
              & np.roll(m, 1, 1) & np.roll(m, -1, 1))
    return m
