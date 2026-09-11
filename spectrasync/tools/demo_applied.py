"""The three applied features on a real photograph, one page.
Reproduce with:  python tools/demo_applied.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import spectrasync as ss
from spectrasync.viz.paper_style import bare, caption

ss.use_paper_style()
g = ss.load_gray("data/raw/photo_b.jpg", max_side=640)[:400, :640]
H, W = g.shape
interior = np.zeros((H, W), bool); interior[45:-45, 45:-45] = True

# F1 stacking
N = 16
src1 = ss.SyntheticSource(g, n=N, max_shift=5.0, noise=0.12, seed=1)
f1 = src1.frames(); t0 = src1.truth[0]
truth1 = ss.fourier_shift(g, t0["dy"], t0["dx"])
rows = ss.compare_reducers(f1, truth=truth1, mask=interior)
best = {r["reducer"]: (r, im) for r, im in rows}
single1 = ss.psnr(truth1, f1[0], interior)

# F2 removal + F3 highlight
src2 = ss.SyntheticSource(g, n=12, max_shift=4.0, noise=0.01,
                          mover=ss.moving_disc(radius=26, value=0.03), seed=2)
f2 = src2.frames(); t2 = src2.truth[0]
truth2 = ss.fourier_shift(g, t2["dy"], t2["dx"])
res = ss.remove_moving_objects(f2, reducer="median")
det = ss.highlight(res.aligned[6], res.output, detector="bandpass", k=3.0)
cmp = ss.compare_temporal_filters(res.aligned)

fig = plt.figure(figsize=(16.0, 12.0))
fig.suptitle("SpectraSync applied features  -  one align+reduce engine, three uses", y=0.985, fontsize=15)
gs = fig.add_gridspec(3, 4, hspace=0.30, wspace=0.10)

def im(r, c, a, title, cap=None, cmap=None):
    ax = fig.add_subplot(gs[r, c]); x = np.asarray(a)
    ax.imshow(np.clip(x, 0, 1) if x.ndim == 3 else x,
              cmap=cmap or ("gray" if x.ndim == 2 else None))
    bare(ax); ax.set_title(title, pad=4, fontsize=10)
    if cap: caption(ax, cap)
    return ax

# row 1 -- stacking
im(0,0, f1[0], "1 noisy frame (sigma 0.12)", "PSNR %.1f dB" % single1)
im(0,1, best["median"][1], "median of %d  (spec method)" % N,
   "PSNR %.1f dB   +%.1f" % (best["median"][0]["psnr"], best["median"][0]["psnr"]-single1))
im(0,2, best["mean"][1], "mean of %d" % N,
   "PSNR %.1f dB   +%.1f  (theory +%.1f)" % (best["mean"][0]["psnr"],
        best["mean"][0]["psnr"]-single1, ss.theoretical_gain_db(N,"mean")))
ax = fig.add_subplot(gs[0,3])
ns = [2,4,8,16,32]
mm, md = [], []
for n in ns:
    s = ss.SyntheticSource(g, n=n, max_shift=5.0, noise=0.12, seed=1)
    fr = s.frames(); tt = ss.fourier_shift(g, s.truth[0]["dy"], s.truth[0]["dx"])
    al,_ = ss.align_frames(fr); b = ss.psnr(tt, fr[0], interior)
    mm.append(ss.psnr(tt, ss.reduce(al,"mean"), interior)-b)
    md.append(ss.psnr(tt, ss.reduce(al,"median"), interior)-b)
ax.plot(ns, [ss.theoretical_gain_db(n,"mean") for n in ns], "--", color=ss.PALETTE["rule"], label="theory 10log10(N)")
ax.plot(ns, mm, "o-", color=ss.PALETTE["ink"], label="mean")
ax.plot(ns, md, "s-", color=ss.PALETTE["red_ink"], label="median")
ax.set_xscale("log", base=2); ax.set_xticks(ns); ax.set_xticklabels(ns)
ax.set_xlabel("frames stacked"); ax.set_ylabel("PSNR gain (dB)"); ax.legend(fontsize=8)
ax.set_title("measured vs theory", pad=4, fontsize=10); ax.grid(True)

# row 2 -- object removal
im(1,0, res.aligned[0], "frame 0 (object present)")
im(1,1, res.aligned[6], "frame 6 (object moved)")
im(1,2, res.output, "median plate = object removed",
   "PSNR %.1f dB vs clean" % ss.psnr(truth2, res.output, interior))
im(1,3, np.abs(res.output-truth2)*interior, "residual vs clean original",
   "max error %.3f" % np.abs(res.output-truth2)[interior].max())

# row 3 -- linear vs nonlinear, and the highlight
im(2,0, cmp["mean (linear, LTI)"], "temporal MEAN (linear)",
   "ghost remains - %.1f dB" % ss.psnr(truth2, cmp["mean (linear, LTI)"], interior))
im(2,1, cmp["median (nonlinear)"], "temporal MEDIAN (nonlinear)",
   "clean - %.1f dB" % ss.psnr(truth2, cmp["median (nonlinear)"], interior))
im(2,2, det.score/max(det.score.max(),1e-9), "band-passed change score",
   "threshold = mean + 3 sigma", ss.INK_CMAP)
ax = im(2,3, det.overlay, "outline via Fourier derivative",
        "%d blob(s); box %s" % (len(det.boxes), det.boxes[0] if det.boxes else "-"))
for (y0,x0,y1,x1) in det.boxes[:3]:
    ax.add_patch(plt.Rectangle((x0,y0), x1-x0, y1-y0, fill=False,
                               color=ss.PALETTE["red_ink"], lw=1.4))

txt = ("STACKING  N=16: single %.1f dB -> mean %.1f (+%.1f, theory +%.1f) | median %.1f (+%.1f)\n"
       "REMOVAL   median plate %.1f dB vs clean; inside the object region %.1f -> %.1f dB\n"
       "LINEAR vs NONLINEAR  mean %.1f dB = temporal low-pass %.1f dB  <  median %.1f dB   "
       "(no LTI filter can reject an impulse)") % (
    single1, best["mean"][0]["psnr"], best["mean"][0]["psnr"]-single1, ss.theoretical_gain_db(N,"mean"),
    best["median"][0]["psnr"], best["median"][0]["psnr"]-single1,
    ss.psnr(truth2,res.output,interior),
    ss.psnr(truth2,res.aligned[0], (np.abs(ss.as_float(res.aligned[0])-truth2)>0.15)&interior),
    ss.psnr(truth2,res.output, (np.abs(ss.as_float(res.aligned[0])-truth2)>0.15)&interior),
    ss.psnr(truth2,cmp["mean (linear, LTI)"],interior),
    ss.psnr(truth2,cmp["temporal low-pass (linear, LTI)"],interior),
    ss.psnr(truth2,cmp["median (nonlinear)"],interior))
fig.text(0.5, 0.010, txt, ha="center", va="bottom", fontsize=10.5,
         color=ss.PALETTE["red_ink"], family="monospace")
fig.savefig("outputs/applied_features_demo.png", bbox_inches="tight", facecolor=ss.PALETTE["paper"])
print(txt); print("\nsaved outputs/applied_features_demo.png")
