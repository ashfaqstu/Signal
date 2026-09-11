"""Core signal processing. Pure numpy: no file I/O, no matplotlib, no UI."""

from .correlation import (cross_power_spectrum, correlation_surface,
                          phase_correlation, phase_correlation_pyramid,
                          second_peak, unwrap_peak)
from .filters import (FILTERS, apply_filter, bandpass, fft_convolve,
                      fourier_gradient, gaussian_blur, gradient_magnitude,
                      highpass, ideal_lowpass, lowpass, mellin_highpass,
                      radial_freq)
from .logpolar import (logpolar, shift_to_rotation, shift_to_scale,
                       spectrum_for_mellin)
from .mellin import (PRESETS, estimate_rotation_scale,
                     estimate_rotation_scale_multi)
from .metrics import itf, ncc, peak_metrics, psnr, rmse, shift_error
from .preprocess import (add_noise, as_float, common_canvas, downsample2,
                         match_shapes, normalise, pad_to, remove_mean, to_even,
                         to_unit, upsample2)
from .register import (register_many, register_pair, register_similarity,
                       register_translation)
from .subpixel import SUBPIXEL
from .transform import (alignment_valid_mask, apply_registration,
                        bilinear_sample, centre_crop,
                        fourier_shift, rescale, rotate, unwarp_similarity,
                        valid_mask, warp_similarity)
from .windows import WINDOWS, window2d

#: The two functions named in the project spec.
func_translation = phase_correlation
func_rotation_and_scale = estimate_rotation_scale
