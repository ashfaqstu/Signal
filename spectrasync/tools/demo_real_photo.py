"""Run the two core SpectraSync functions on a real photograph and save a
one-page figure. Reproduce with:  python tools/demo_real_photo.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from spectrasync.io import load_gray, crop_pair
from spectrasync.core import (phase_correlation, register_similarity, cross_power_spectrum,
                              warp_similarity, ncc, psnr, centre_crop,
                              alignment_valid_mask, apply_registration)
from spectrasync.viz import use_paper_style, PALETTE, INK_CMAP, difference
from spectrasync.viz.paper_style import bare, caption

PHOTO = sys.argv[1] if len(sys.argv) > 1 else "data/raw/photo_a.jpg"
use_paper_style()
g = load_gray(PHOTO, max_side=900)

ref, mov = crop_pair(g, 17, -23, (400, 400))
t = phase_correlation(ref, mov)
R, F1, F2 = cross_power_spectrum(ref, mov)
aligned = apply_registration(mov, 0.0, 1.0, t.dy, t.dx)
vm = alignment_valid_mask(ref.shape, 0.0, 1.0, t.dy, t.dx)

base = centre_crop(g, 0.6)[:336, :336]
movrs = warp_similarity(base, 20.0, 1.20)
rs = register_similarity(base, movrs)
vrs = alignment_valid_mask(base.shape, rs.angle_deg, rs.scale, rs.dy, rs.dx)

fig = plt.figure(figsize=(15.5, 12.6))
fig.suptitle("SpectraSync on a real photograph  -  " + os.path.basename(PHOTO), y=0.985, fontsize=15)
gs = fig.add_gridspec(3, 4, hspace=0.28, wspace=0.12)

def im(r, c, a, title, cap=None, cmap=None):
    ax = fig.add_subplot(gs[r, c]); x = np.asarray(a)
    ax.imshow(np.clip(x, 0, 1) if x.ndim == 3 else x,
              cmap=cmap or ("gray" if x.ndim == 2 else None))
    bare(ax); ax.set_title(title, pad=4, fontsize=10)
    if cap: caption(ax, cap)
    return ax

im(0,0, ref, "reference crop")
im(0,1, mov, "moved crop  (true +17, -23 px)")
im(0,2, difference(ref,mov)*vm, "difference BEFORE", "PSNR %.1f dB" % psnr(ref,mov,vm))
im(0,3, difference(ref,aligned)*vm, "difference AFTER", "PSNR %.1f dB  (valid region only)" % psnr(ref,aligned,vm))

im(1,0, np.log1p(np.abs(np.fft.fftshift(F1))), "log |F1|", "magnitude spectrum", INK_CMAP)
im(1,1, np.log1p(np.abs(np.fft.fftshift(F2))), "log |F2|", "identical - the shift is in the PHASE", INK_CMAP)
ax = fig.add_subplot(gs[1,2]); ax.imshow(np.angle(np.fft.fftshift(R)), cmap="twilight")
bare(ax); ax.set_title("angle(R) - phase fringes", pad=4, fontsize=10)
caption(ax, "tilt and spacing encode the shift")
ax = fig.add_subplot(gs[1,3], projection="3d")
cs = np.fft.fftshift(t.corr); H, W = cs.shape; st = max(1, H//110)
Y, X = np.mgrid[0:H:st, 0:W:st]
ax.plot_surface(X, Y, cs[::st, ::st], cmap=INK_CMAP, linewidth=0)
ax.set_xticks([]); ax.set_yticks([]); ax.set_zticks([])
ax.set_facecolor(PALETTE["paper"]); ax.set_title("correlation surface", pad=4, fontsize=10)

im(2,0, base, "reference")
im(2,1, movrs, "rotated +20 deg, scaled 1.20x")
im(2,2, rs.aligned, "after Fourier-Mellin registration")
im(2,3, difference(base, rs.aligned)*vrs, "residual (valid region)",
   "NCC %.3f -> %.3f" % (ncc(base,movrs,vrs), ncc(base,rs.aligned,vrs)))

txt = ("TRANSLATION     est (%+.3f, %+.3f) px    error %.3f px    peak ratio %.1f (%s)    PSNR %.1f -> %.1f dB\n"
       "FOURIER-MELLIN  est %+.2f deg / %.4fx    true +20.00 deg / 1.2000x    "
       "err %.3f deg / %.2f%%    PSNR %.1f -> %.1f dB") % (
    t.dy, t.dx, max(abs(t.dy-17), abs(t.dx+23)), t.stats.ratio, t.stats.verdict,
    psnr(ref,mov,vm), psnr(ref,aligned,vm),
    rs.angle_deg, rs.scale, abs(rs.angle_deg-20), 100*abs(rs.scale-1.2)/1.2,
    psnr(base,movrs,vrs), psnr(base,rs.aligned,vrs))
fig.text(0.5, 0.012, txt, ha="center", va="bottom", fontsize=11,
         color=PALETTE["red_ink"], family="monospace")
out = "outputs/real_photo_demo.png"
fig.savefig(out, bbox_inches="tight", facecolor=PALETTE["paper"])
print(txt); print("\nsaved", out)
