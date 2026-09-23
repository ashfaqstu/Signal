"""Turn each photo in a folder into a burst of noisy frames, for the Stacking page.

    python tools/make_noisy_set.py                      # new_image/2 -> new_image/2_noisy
    python tools/make_noisy_set.py SRC DST --n 8 --sigma 0.08 --shake 6

For every source photo this writes DST/set_<k>/noisy_01.jpg ... noisy_<n>.jpg:
the same scene, each frame with its own Gaussian noise and a small random
hand-held shift. Stack one set's frames in the app to get a clean image back.

Ground truth goes next to the frames, OUTSIDE the set folders so selecting a
whole set never picks it up by accident:
    DST/_clean/set_<k>.png   the noise-free frame in frame 1's coordinates
    DST/truth.csv            per-frame shift and sigma

Frames are saved at `--size` (longest side) because the app downscales to its
working size: saving at full camera resolution would let the downscale average
the noise away before the stack ever sees it.
"""

import argparse
import csv
import glob
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image  # noqa: E402

from spectrasync.io.images import load_rgb, save_png  # noqa: E402


def save_jpg(path, arr, quality=95):
    a = np.clip(arr, 0.0, 1.0)
    Image.fromarray((a * 255.0).round().astype(np.uint8)).save(path, quality=quality)


def make_set(src, out_dir, n, sigma, shake, size, rng):
    """Integer-pixel crops of one photo at random offsets, plus noise.

    Cropping (instead of a circular FFT shift) means new content really does
    enter at the edges, exactly like a hand-held burst.
    """
    img = load_rgb(src, max_side=size)
    H, W = img.shape[:2]
    h, w = H - 2 * shake, W - 2 * shake
    os.makedirs(out_dir, exist_ok=True)
    rows = []
    offsets = [(0, 0)] + [tuple(rng.integers(-shake, shake + 1, 2)) for _ in range(n - 1)]
    for i, (oy, ox) in enumerate(offsets, 1):
        clean = img[shake + oy:shake + oy + h, shake + ox:shake + ox + w]
        noisy = clean + rng.normal(0.0, sigma, clean.shape)
        save_jpg(os.path.join(out_dir, f"noisy_{i:02d}.jpg"), noisy)
        if i == 1:
            reference = clean
        # content of frame i sits at frame-1 position minus the offset
        rows.append({"frame": f"noisy_{i:02d}.jpg", "dy": -int(oy), "dx": -int(ox),
                     "sigma": sigma})
    return reference, rows


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("src", nargs="?", default="new_image/2")
    ap.add_argument("dst", nargs="?", default="new_image/2_noisy")
    ap.add_argument("--n", type=int, default=8, help="frames per set")
    ap.add_argument("--sigma", type=float, default=0.08,
                    help="Gaussian noise std, on a 0..1 intensity scale")
    ap.add_argument("--shake", type=int, default=6, help="max hand-held shift (px)")
    ap.add_argument("--size", type=int, default=800, help="longest side of the output")
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()

    paths = sorted(glob.glob(os.path.join(a.src, "*.jpg"))
                   + glob.glob(os.path.join(a.src, "*.png")))
    if not paths:
        sys.exit(f"no .jpg/.png images in {a.src}")
    rng = np.random.default_rng(a.seed)
    all_rows = []
    for k, p in enumerate(paths, 1):
        name = f"set_{k}"
        ref, rows = make_set(p, os.path.join(a.dst, name), a.n, a.sigma,
                             a.shake, a.size, rng)
        save_png(os.path.join(a.dst, "_clean", f"{name}.png"), ref)
        all_rows += [{"set": name, "source": os.path.basename(p), **r} for r in rows]
        print(f"{name}: {a.n} frames from {os.path.basename(p)}, "
              f"{ref.shape[1]}x{ref.shape[0]} px, sigma {a.sigma}")
    with open(os.path.join(a.dst, "truth.csv"), "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(all_rows[0]))
        wr.writeheader()
        wr.writerows(all_rows)
    print(f"wrote {a.dst}/  (ground truth in {a.dst}/_clean and truth.csv)")


if __name__ == "__main__":
    main()
