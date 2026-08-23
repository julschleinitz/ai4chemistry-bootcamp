# %% [markdown]
# # Figure L3 - "Less is more" panels (Smith et al. 2018)
#
# Slide 39.  Smith, J. S.; Nebgen, B.; Lubbers, N.; Isayev, O.; Roitberg, A. E.
# "Less is more: Sampling chemical space with active learning."
# *J. Chem. Phys.* **2018**, *148*, 241733.  DOI 10.1063/1.5023802
#
# **Licence: NOT open access.**  Published by AIP Publishing, all rights reserved.
# These panels are reproduced for non-commercial teaching use in an openly released
# lecture, with full attribution.  That is normal academic practice for lecture
# material but it is *not* a licence grant -- see `lecture_13_CREDITS.md`.
#
# **Figure 2 is the one to use.**  It is the fully automated AL workflow, and it
# contains, in one picture, both things the slide needs to say:
#
# * the acquisition criterion, written on the figure as $\rho_i = \sigma(E_i)/\sqrt{N}$
#   with the test $\rho_i < \hat\rho$;
# * the **stopping rule** - the "Is percent($\rho_i > \hat\rho$) < 5% of sampled?"
#   decision diamond that terminates the loop.
#
# Figure 5 (COMP6 learning curves across six benchmarks) is extracted as a spare.
#
# The plots are **vector**, so `pdfimages` returns only the molecule renderings; these
# crops are rendered from the page at 400 dpi.

# %%
import os
import subprocess

from PIL import Image

PDF = "_shared/241733_1_online.pdf"
RAW = "_shared/_smith_pages"
OUT = "../figures"
DPI = 400
os.makedirs(RAW, exist_ok=True)
os.makedirs(OUT, exist_ok=True)
print("Pillow", Image.__version__)

# %%
# Figure 2 is at the top of page 5; Figure 5 spans the top of page 9.
for pg in (5, 9):
    out = os.path.join(RAW, "pg-%02d.png" % pg)
    if not os.path.exists(out):
        subprocess.run(["pdftoppm", "-png", "-r", str(DPI), "-f", str(pg), "-l", str(pg),
                        PDF, os.path.join(RAW, "pg")], check=True)
pages = {pg: Image.open(os.path.join(RAW, "pg-%02d.png" % pg)).convert("RGB")
         for pg in (5, 9)}
for pg, im in pages.items():
    print("page %d at %d dpi:" % (pg, DPI), im.size)

# %%
# Fractional crops (left, top, right, bottom), so they survive a resolution change.
# The vertical bounds were MEASURED, not guessed: the blank bands separating the
# running head, the figure and the caption were located by row-wise ink density on
# the rendered page, which is why they look over-precise.
CROPS = {
    # Fig. 2 - the fully automated AL workflow, with the criterion and the stopping rule
    "fig_L3_smith_workflow": (5, (0.030, 0.0605, 0.974, 0.3805)),
    # Fig. 5 - COMP6 learning curves, six benchmarks (spare)
    "fig_L3b_smith_comp6": (9, (0.030, 0.0605, 0.974, 0.3925)),
}
for name, (pg, box) in CROPS.items():
    im = pages[pg]
    W, H = im.size
    px = (int(box[0] * W), int(box[1] * H), int(box[2] * W), int(box[3] * H))
    crop = im.crop(px)
    crop.save(os.path.join(OUT, name + ".png"), dpi=(DPI, DPI))
    print("%-28s page %d -> %s  (aspect %.2f)"
          % (name, pg, crop.size, crop.size[0] / crop.size[1]))

# %%
print("""
For the speaker notes - what is written ON Fig. 2, which is why it is worth showing:

  (a) initial data set reduction:  train ANI on the training set, compute dE_i for
      remaining non-training data, add 2% of the data where dE_i > 0.1 kcal/mol,
      loop until termination
  (b) new configuration search:  train 5x ANI models, sample new configurations
      (GDB, ChEMBL21, ...), compute rho_i = sigma(E_i)/sqrt(N), add points with
      rho_i < rho-hat to the conformer sampling set
  (c) new conformation search:  generate new conformers, train 5x ANI models on the
      new training set, add rho_i < rho-hat to the training set

  The END CYCLE diamond is the stopping rule:
      "Is percent(rho_i > rho-hat) < 5% of sampled?"   Yes -> stop.  No -> restart.

This is the slide where a chemist can see an entire active-learning campaign, its
acquisition criterion and its termination condition, in one figure.
""")
