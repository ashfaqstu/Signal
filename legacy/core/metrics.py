"""Confidence of the estimate, and proof that the alignment worked.

Milestones M6/M7/M9 in docs/02-CORE-IMPLEMENTATION.md.

Numbers, not vibes. Report RMSE / PSNR / NCC BEFORE and AFTER alignment,
restricted to the valid mask -- a large PSNR jump is the single most
convincing line in the results table.
"""

import numpy as np


# ---------------------------------------------------------------------------
# Confidence: how much do we trust this peak?
# ---------------------------------------------------------------------------

def peak_metrics(corr, exclude=5):
    """Quality of the correlation peak.

    Roll the peak to the CENTRE of the array first, so the exclusion box
    cannot wrap around the array edge:
        py, px = unravel_index(argmax(corr), corr.shape)
        c = np.roll(corr, (H//2 - py, W//2 - px), axis=(0, 1))

    Then, with cy, cx = H//2, W//2, and `side` = every sample OUTSIDE a
    (2*exclude+1) square centred on (cy, cx).

    Returns
    -------
    peak  : float, c[cy, cx] -- the height of the delta. Scale-dependent, so
            it means little on its own; quote it as supporting evidence.
    psr   : float, (peak - side.mean()) / (side.std() + 1e-12) -- the
            peak-to-sidelobe ratio, i.e. how many noise standard deviations
            the peak stands above the floor.
    ratio : float, peak / (side.max() + 1e-12) -- peak over runner-up.

    A three-tuple of plain floats in that order (cast with float(), do not
    hand back 0-d numpy scalars -- they print badly in the CLI).

    Measured reference values (256x256 crops, our own runs):

        case                          peak    PSR    ratio   verdict
        clean overlapping crops       0.87    460    92      locked
        same pair + noise sigma 0.15  0.09     24     4.2    good
        featureless flat grey         0.024     6.2   1.08   no lock
        completely unrelated images   0.020     5.1   1.04   no lock

    RATIO IS THE BEST SINGLE DISCRIMINATOR: above ~2.0 trust the answer,
    below ~1.2 there is no lock at all. Use ratio for the accept/reject
    decision and show peak and PSR alongside it.
    """
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Alignment quality: before vs after
# ---------------------------------------------------------------------------

def rmse(a, b, mask=None):
    """Root mean squared error, optionally restricted to `mask` (bool array).

    d = (a - b)**2; average over d[mask] if a mask is given, else over
    everything; then sqrt.

    Returns
    -------
    float >= 0, in the same units as the pixels (so [0, 1] here). LOWER IS
    BETTER; 0.0 means identical. Cast to float() -- psnr() below tests it
    against 0 exactly.
    """
    raise NotImplementedError


def psnr(a, b, mask=None, peak=1.0):
    """Peak signal-to-noise ratio in dB: 20 * log10(peak / rmse).

    `peak` is 1.0 because our images live in [0, 1].

    Returns
    -------
    float, in decibels. HIGHER IS BETTER. Return float('inf') when rmse is
    exactly 0 rather than letting numpy warn about division by zero.

    This is the headline number of the report: quote it before and after
    alignment on the same mask. Typical successful run jumps by 10-20 dB.
    """
    raise NotImplementedError


def ncc(a, b, mask=None):
    """Normalised cross-correlation.

    Apply the mask first, then subtract each array's mean, then
        (a*b).sum() / (norm(a) * norm(b) + 1e-12)

    Returns
    -------
    float in [-1, 1]. 1.0 = perfectly aligned, 0.0 = unrelated, negative =
    inverted. Invariant to gain and bias, which makes it the fair
    before/after number when the two shots differ in exposure.
    """
    raise NotImplementedError


def shift_error(true_dy, true_dx, est_dy, est_dx):
    """Compare an estimate against known ground truth, for the error table.

    Returns
    -------
    err_dy : float, abs(est_dy - true_dy) in pixels
    err_dx : float, abs(est_dx - true_dx) in pixels
    err    : float, Euclidean sqrt(err_dy**2 + err_dx**2) -- the single
             number to put in the report's error column

    A three-tuple. Targets from docs/02: exactly 0.0 for circular pairs,
    <= 1 px for real crops, <= 0.05-0.2 px for the sub-pixel test.
    """
    raise NotImplementedError
