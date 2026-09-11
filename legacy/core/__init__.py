"""Core package for the frequency-domain image aligner.

Modules
-------
io_utils          load / save / grayscale / float conversion + test-pair makers
preprocess        windowing, mean removal, normalisation, downsampling
phase_correlation the heart of the project: the shift estimator
transform         Fourier-domain sub-pixel shifting + border handling
metrics           peak confidence, RMSE, PSNR, NCC
viz               overlays (anaglyph, checkerboard, diff, blend)

Conventions fixed for the whole project (see docs/01-THEORY.md):
    mov[y, x] = ref[y - dy, x - dx]
    +dy = content moved DOWN, +dx = content moved RIGHT
    numpy indexes as [row, col] = [y, x]
    everything is float64 in [0, 1] internally
"""
