# %% [markdown]
# # Figures L1a-L1e - panels from Schleinitz et al., JACS 2025
#
# Slides 31-35.  Extracts the published figure panels from the article PDF at
# their native 300 dpi and crops the sub-panels the deck needs.
#
# **Licence: CC-BY-NC-ND 4.0.**  Verbatim reproduction with attribution is
# permitted; *derivatives are not*.  So these panels are cropped and rescaled
# only -- nothing is recoloured, relabelled or redrawn.  Every slide carries the
# full citation.
#
# Source: Schleinitz, J.; Carretero-Cerdan, A.; Gurajapu, A.; et al.
# *J. Am. Chem. Soc.* **2025**, *147*, 7476-7484.  DOI 10.1021/jacs.4c15902
#
# Embedded images in the PDF, at 300 dpi:
#
# | object | page | size | article figure |
# |---|---|---|---|
# | `im-002-011` | 2 | 2088x945  | Figure 1 (a,b,c) - the problem and the workflow |
# | `im-002-012` | 2 | 2092x711  | Figure 2 - data set and descriptor benchmarking |
# | `im-004-013` | 4 | 2088x1115 | Figure 3 (a,b) - learning curves + molecule selection |
# | `im-005-014` | 5 | 996x1082  | Figure 4 (a,b) - box plots + accurate-prediction counts |
# | `im-006-015` | 6 | 996x1793  | Figure 5 (a,b) - experimental targets + sclareolide |

# %%
import os
import subprocess
import sys

from PIL import Image

PDF = "_shared/ja4c15902.pdf"
RAW = "_shared/_jacs_raw"
OUT = "../figures"
os.makedirs(RAW, exist_ok=True)
os.makedirs(OUT, exist_ok=True)
print("Pillow", Image.__version__)

# %%
# extract the embedded images once (pdfimages ships with poppler-utils)
if not os.listdir(RAW):
    subprocess.run(["pdfimages", "-png", "-p", PDF, os.path.join(RAW, "im")], check=True)
imgs = {f.rsplit(".", 1)[0]: os.path.join(RAW, f) for f in sorted(os.listdir(RAW))}
for k in ("im-002-011", "im-002-012", "im-004-013", "im-005-014", "im-006-015"):
    print(k, Image.open(imgs[k]).size)

# %%
# Crops are given as fractions (left, top, right, bottom) of each source image,
# so they survive a change of extraction resolution.
CROPS = {
    # Figure 1c -- the workflow and the three acquisition functions.  Slide 31.
    "fig_L1a_workflow":        ("im-002-011", (0.000, 0.442, 1.000, 1.000)),
    # Figure 1b right -- distribution shift, small -> complex molecules.  Slide 32.
    "fig_L1b_distribution_shift": ("im-002-011", (0.632, 0.015, 1.000, 0.432)),
    # Figure 3b -- the first 10 molecules each AF selects.  Slide 32/33.
    "fig_L1c_molecule_selection": ("im-004-013", (0.000, 0.428, 1.000, 1.000)),
    # Figure 3a right -- the learning curves on cholestanoid 1.  Slide 33.
    "fig_L1d_learning_curves": ("im-004-013", (0.600, 0.022, 1.000, 0.462)),
    # Figure 4b -- 19 vs 27 vs 31 targets predicted accurately.  Slide 33.
    "fig_L1e_accuracy_counts": ("im-005-014", (0.000, 0.558, 1.000, 1.000)),
    # Figure 4a -- box plots, data set size saved vs random.  Slide 33.
    "fig_L1f_boxplots":        ("im-005-014", (0.000, 0.000, 1.000, 0.552)),
    # Figure 5a -- the five experimental targets.  Slide 34.
    "fig_L1g_experimental":    ("im-006-015", (0.000, 0.000, 1.000, 0.722)),
    # Figure 5b -- sclareolide, the one it gets wrong.  Slide 34.
    "fig_L1h_sclareolide":     ("im-006-015", (0.000, 0.726, 1.000, 1.000)),
}

for name, (src, box) in CROPS.items():
    im = Image.open(imgs[src]).convert("RGB")
    W, H = im.size
    px = (int(box[0] * W), int(box[1] * H), int(box[2] * W), int(box[3] * H))
    crop = im.crop(px)
    crop.save(os.path.join(OUT, name + ".png"), dpi=(300, 300))
    print("%-32s %-14s %s -> %s" % (name, src, (W, H), crop.size))

# %%
print("\nAll panels are verbatim crops. CC-BY-NC-ND 4.0 permits this with attribution;")
print("it does NOT permit derivatives, so do not recolour or relabel them.")
