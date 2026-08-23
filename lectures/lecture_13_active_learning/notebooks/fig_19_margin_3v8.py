# %% [markdown]
# # Figure 19 - margin sampling on a 3-vs-8 classifier
#
# Section 3.2.  The point of margin sampling is that it aims at the *boundary
# between the top two candidates*, so it buys the examples the model genuinely
# cannot call.  Digits make that visible in a way abstract descriptors do not.
#
# **No MNIST download.**  The glyphs are rendered here with matplotlib at varying
# stroke weight, slant, scale and noise, so the notebook is self-contained and
# reproducible.  Crucially the pool also contains explicit **blends**
# $\alpha\cdot 3 + (1-\alpha)\cdot 8$, which is not a gimmick: those blends are
# precisely the images Baum & Lang's learner generated in 1992 when it was allowed
# to synthesise its own queries, and they are what margin sampling goes for
# here.
#
# Pipeline: render -> flatten -> PCA (numpy SVD) -> logistic regression ->
# margin = $|p(3) - p(8)|$, small margin = query me.

# %%
import sys; sys.path.insert(0, "_shared")
import numpy as np
import matplotlib.pyplot as plt
import style
from alsim import LogReg
style.use(); style.versions()

# %%
# PX=28 with a 22 pt glyph leaves only ~0.8% of pixels inked and the classifier
# tops out near 78%. At 48 px with a 34 pt glyph it reaches ~100% on the clean
# digits, which is what makes the blends the genuinely ambiguous ones.
PX = 48
FONTSIZE = 34


def render(ch, weight="normal", style_="normal", scale=1.0, dx=0.0, dy=0.0):
    """Render a character to a PX x PX greyscale array in [0, 1]."""
    # figsize=1in at dpi=PX gives exactly PX x PX pixels -- do not use a
    # fractional figsize, matplotlib rounds it and the buffer stops being square.
    fig = plt.figure(figsize=(1, 1), dpi=PX)
    fig.patch.set_facecolor("white")
    fig.text(0.5 + dx, 0.42 + dy, ch, ha="center", va="center",
             fontsize=FONTSIZE * scale, color="black",
             fontweight=weight, style=style_)
    # Draw to the Agg canvas and read the RGBA buffer directly. Going through
    # savefig would apply rcParams["savefig.bbox"]="tight" (set by style.use()),
    # which crops a mostly-empty canvas to a small non-square buffer -- and
    # passing bbox_inches=None does NOT disable that, it falls back to the rcParam.
    fig.canvas.draw()
    a = np.asarray(fig.canvas.buffer_rgba())
    plt.close(fig)
    g = a[..., :3].mean(-1) / 255.0
    return 1.0 - g          # ink = 1


rng = np.random.default_rng(3)
imgs, lab, kind = [], [], []

for ch, y in (("3", 0), ("8", 1)):
    for _ in range(90):
        im = render(ch,
                    weight=rng.choice(["light", "normal", "bold"]),
                    style_=rng.choice(["normal", "italic"]),
                    scale=rng.uniform(0.94, 1.06),
                    dx=rng.normal(0, 0.018), dy=rng.normal(0, 0.018))
        im = np.clip(im + rng.normal(0, 0.02, im.shape), 0, 1)
        imgs.append(im); lab.append(y); kind.append("clean")

# the ambiguous ones: literal blends of a 3 and an 8
base3, base8 = render("3"), render("8")
for _ in range(28):
    a = rng.uniform(0.44, 0.56)
    # Threshold AFTER blending. A raw alpha-average of two glyphs reads as a
    # ghost -- a faint 3 laid over an 8 -- rather than as a single ambiguous
    # character. Re-thresholding restores a crisp stroke, so the image looks
    # like one glyph you genuinely cannot name.
    blend = a * base3 + (1 - a) * base8
    im = (blend > 0.42).astype(float)
    im = np.clip(im + rng.normal(0, 0.035, im.shape), 0, 1)
    imgs.append(im); lab.append(int(a < 0.5)); kind.append("blend")

Ximg = np.stack(imgs); y = np.array(lab); kind = np.array(kind)
print("pool: %d images (%d clean, %d blends), %dx%d"
      % (len(Ximg), (kind == "clean").sum(), (kind == "blend").sum(), PX, PX))

# %%
# PCA by SVD, then a logistic classifier on the leading components
F = Ximg.reshape(len(Ximg), -1)
NPC = 25
# Fit the PCA basis on the CLEAN digits only, then project everything onto it.
# If the basis is fitted on the whole pool it shifts whenever I change how the
# blends are made, and the clean-digit accuracy moves for reasons that have
# nothing to do with the digits.
clean = kind == "clean"
mean_ = F[clean].mean(0)
_, _, Vt = np.linalg.svd(F[clean] - mean_, full_matrices=False)
Z = (F - mean_) @ Vt[:NPC].T
Z = Z / np.abs(Z[clean]).max(0)

Phi = np.column_stack([np.ones(len(Z)), Z])
# Train ONLY on the clean, already-labelled digits, then score the whole pool.
# That is the actual active-learning setting: the blends are unlabelled candidates,
# so letting them into the fit would be cheating and would blunt the classifier.
tr = kind == "clean"
clf = LogReg(lam=1e-3, steps=3000, lr=2.0).fit(Phi[tr], y[tr].astype(float))
p8 = clf.prob(Phi)
margin = np.abs(2 * p8 - 1.0)            # 1 = confident, 0 = a coin flip

acc_clean = ((p8 > 0.5) == (y > 0.5))[kind == "clean"].mean()
acc = ((p8 > 0.5) == (y > 0.5)).mean()
print("accuracy on the CLEAN digits: %.2f" % acc_clean)
assert acc_clean > 0.95, "the classifier must actually be able to read digits"
K = 8
pick = np.argsort(margin)[:K]
print("classifier accuracy on the pool: %.2f" % acc)
print("margin sampling picks %d of %d from the blends (%.0f%%)"
      % ((kind[pick] == "blend").sum(), K, 100 * (kind[pick] == "blend").mean()))
# With lightly-jittered clean digits (classifier at 100% on them), all eight
# picks are blends. If you widen the jitter, degraded real digits start
# appearing in the picks too -- which is also correct behaviour, just a busier
# figure. Margin finds whatever is undecidable, however it got that way.
assert (kind[pick] == "blend").mean() >= 0.75, "blends should dominate the picks"

# %%
fig = plt.figure(figsize=(11.0, 4.6))
gs = fig.add_gridspec(2, 2, width_ratios=[1.35, 1], height_ratios=[1, 1],
                      wspace=0.16, hspace=0.28)
ax = fig.add_subplot(gs[:, 0])

for cls, col, name in ((0, style.TER, "“3”"), (1, style.ACCENT, "“8”")):
    m = (y == cls) & (kind == "clean")
    ax.scatter(Z[m, 0], Z[m, 1], s=20, c=col, alpha=0.55, lw=0, label=name)
m = kind == "blend"
ax.scatter(Z[m, 0], Z[m, 1], s=42, marker="D", c=style.INK, alpha=0.85, lw=0,
           label="3/8 blends")
ax.scatter(Z[pick, 0], Z[pick, 1], s=150, facecolors="none",
           edgecolors=style.EMPH, linewidths=2.0, zorder=8,
           label="margin picks these %d" % K)
ax.set_xlabel("PC 1"); ax.set_ylabel("PC 2")
ax.set_title("the pool, in its first two principal components", fontsize=11.5, pad=8)
ax.legend(loc="best", fontsize=8.5)

# the picked images themselves, and a confident one for contrast
axg = fig.add_subplot(gs[0, 1])
axg.imshow(np.hstack([Ximg[i] for i in pick[:6]]), cmap="Greys", vmin=0, vmax=1)
axg.set_title("what margin sampling asks you to label", fontsize=11,
              color=style.EMPH, fontweight="bold", pad=6)
axg.axis("off")

conf = np.argsort(-margin)[:6]
axc = fig.add_subplot(gs[1, 1])
axc.imshow(np.hstack([Ximg[i] for i in conf]), cmap="Greys", vmin=0, vmax=1)
axc.set_title("what it skips — already decided", fontsize=11, color=style.MUTED, pad=6)
axc.axis("off")

fig.text(0.5, -0.045,
         "margin $=|p(3)-p(8)|$;  glyphs rendered in this notebook, not MNIST.  "
         "Every queried image is a 3/8 blend — the same objects Baum & Lang's learner "
         "synthesised in 1992 when allowed to invent its own queries.",
         ha="center", fontsize=9, color=style.MUTED, style="italic")
style.save(fig, "fig_19_margin_3v8")
