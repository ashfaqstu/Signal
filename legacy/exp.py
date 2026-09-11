"""Section 5 experiment: magnitude is boring, phase is everything.

See docs/01-THEORY.md section 5. Swap the magnitude and phase spectra of two
different images and look at what comes back: the reconstruction always looks
like whichever image donated the PHASE.

Run with no arguments to use two synthetic images:

    python exp.py

Or point it at two photographs of your own (any size, any format):

    python exp.py face.jpg building.jpg
"""

import sys

import numpy as np
import matplotlib.pyplot as plt
from PIL import Image


# ---------------------------------------------------------------------------
# Inputs. Both images MUST end up the same shape -- fft2 cannot mix spectra of
# different sizes. (core.io_utils.load_gray does this properly once M1 is done.)
# ---------------------------------------------------------------------------

def load_gray(path, size):
    """Decode a file to float64 grayscale in [0, 1], resampled to `size` = (H, W)."""
    img = Image.open(path).convert("L").resize((size[1], size[0]))
    return np.asarray(img, dtype=np.float64) / 255.0


def synth_face(H, W):
    """Smooth blobs: an ellipse with two eyes and a mouth."""
    y, x = np.mgrid[0:H, 0:W]
    cy, cx = H / 2, W / 2
    img = np.zeros((H, W))
    img[((y - cy) / (0.38 * H)) ** 2 + ((x - cx) / (0.30 * W)) ** 2 <= 1] = 0.6
    for ex in (cx - 0.12 * W, cx + 0.12 * W):
        img[(y - (cy - 0.10 * H)) ** 2 + (x - ex) ** 2 <= (0.045 * W) ** 2] = 0.05
    img[(np.abs(y - (cy + 0.17 * H)) <= 0.025 * H) & (np.abs(x - cx) <= 0.13 * W)] = 0.05
    return img


def synth_building(H, W):
    """Hard periodic structure: a grid of lit windows over a dark facade."""
    y, x = np.mgrid[0:H, 0:W]
    img = np.full((H, W), 0.25)
    img[((y % 32) < 18) & ((x % 24) < 14)] = 0.9
    img[y > 0.85 * H] = 0.15
    return img


def _n(a):
    """Stretch any float array to [0, 1] so imshow can display it."""
    lo, hi = a.min(), a.max()
    return (a - lo) / (hi - lo) if hi > lo else np.zeros_like(a)


# ---------------------------------------------------------------------------
# The experiment itself -- the ten lines from the theory doc
# ---------------------------------------------------------------------------

def main():
    H, W = 256, 256

    if len(sys.argv) == 3:
        img_a = load_gray(sys.argv[1], (H, W))
        img_b = load_gray(sys.argv[2], (H, W))
    else:
        img_a = synth_face(H, W)
        img_b = synth_building(H, W)

    A = np.fft.fft2(img_a)      # e.g. a photo of a face
    B = np.fft.fft2(img_b)      # e.g. a photo of a building

    mix1 = np.abs(A) * np.exp(1j * np.angle(B))   # magnitude of A, phase of B
    mix2 = np.abs(B) * np.exp(1j * np.angle(A))   # magnitude of B, phase of A

    rec1 = np.real(np.fft.ifft2(mix1))            # you will SEE the building
    rec2 = np.real(np.fft.ifft2(mix2))            # you will SEE the face

    panels = [
        (img_a, "A: face"),
        (img_b, "B: building"),
        (rec1, "|A| + phase(B)  ->  building"),
        (rec2, "|B| + phase(A)  ->  face"),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(8, 8))
    for ax, (arr, title) in zip(axes.ravel(), panels):
        ax.imshow(_n(arr), cmap="gray", vmin=0, vmax=1)
        ax.set_title(title, fontsize=10)
        ax.axis("off")
    fig.suptitle("Structure is phase (docs/01-THEORY.md section 5)")
    fig.tight_layout()
    fig.savefig("exp_phase_swap.png", dpi=120)
    print("wrote exp_phase_swap.png")
    plt.show()


if __name__ == "__main__":
    main()
