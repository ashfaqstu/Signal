"""Result objects.

Every estimator returns a dataclass, never a bare tuple. Adding a field later
does not break callers, and UI code reads `result.angle_deg` instead of `r[3]`.
All of them are plain frozen dataclasses -- no behaviour, no inheritance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np


@dataclass
class PeakStats:
    """Quality of a correlation peak. See legacy/docs/01-THEORY.md section 13."""
    peak: float          # height of the correlation maximum
    psr: float           # (peak - sidelobe mean) / sidelobe std
    ratio: float         # peak / best competing peak  <- the useful one
    polarity: float = 1.0   # sign of the peak; -1 means inverted contrast

    @property
    def verdict(self):
        if self.ratio >= 2.0:
            return "locked"
        if self.ratio >= 1.2:
            return "marginal"
        return "no lock"


@dataclass
class TranslationResult:
    """Output of func_translation (phase correlation)."""
    dy: float
    dx: float
    stats: PeakStats
    corr: Optional[np.ndarray] = field(default=None, repr=False)

    @property
    def shift(self):
        return (self.dy, self.dx)

    @property
    def magnitude(self):
        return float(np.hypot(self.dy, self.dx))

    @property
    def direction_deg(self):
        return float(np.degrees(np.arctan2(self.dy, self.dx)))


@dataclass
class RotationScaleResult:
    """Output of func_rotation_and_scale (Fourier-Mellin)."""
    angle_deg: float
    scale: float
    stats: PeakStats
    logpolar_ref: Optional[np.ndarray] = field(default=None, repr=False)
    logpolar_mov: Optional[np.ndarray] = field(default=None, repr=False)
    corr: Optional[np.ndarray] = field(default=None, repr=False)
    settings: dict = field(default_factory=dict)


@dataclass
class RegistrationResult:
    """Full similarity registration: rotation, scale and translation.

    Alignment order is fixed and matters:
        1. un-rotate / un-scale `mov` about the image centre
        2. then shift by (-dy, -dx)
    `dy, dx` are therefore measured in the UN-ROTATED frame.
    """
    angle_deg: float
    scale: float
    dy: float
    dx: float
    stats: PeakStats
    aligned: Optional[np.ndarray] = field(default=None, repr=False)
    rs: Optional[RotationScaleResult] = field(default=None, repr=False)
    translation: Optional[TranslationResult] = field(default=None, repr=False)

    @property
    def is_translation_only(self):
        return abs(self.angle_deg) < 1e-9 and abs(self.scale - 1.0) < 1e-9


@dataclass
class StackResult:
    """Output of the align + temporal-reduce engine (all three applied features)."""
    output: np.ndarray                       # the reduced image
    aligned: list = field(default_factory=list, repr=False)
    shifts: list = field(default_factory=list)   # one (dy, dx) per input frame
    reducer: str = "median"
    n_frames: int = 0
    stats: dict = field(default_factory=dict)


@dataclass
class DetectionResult:
    """Output of the change detector / highlighter."""
    mask: np.ndarray = field(repr=False)
    outline: np.ndarray = field(repr=False)
    overlay: Optional[np.ndarray] = field(default=None, repr=False)
    boxes: list = field(default_factory=list)     # (y0, x0, y1, x1) per blob
    score: Optional[np.ndarray] = field(default=None, repr=False)
    threshold: float = 0.0
