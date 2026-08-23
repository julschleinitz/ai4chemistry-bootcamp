# %% [markdown]
# # Figure L2 - FLARE, on-the-fly active learning of a force field
#
# Slide 40.  Vandermause, J.; Torrisi, S. B.; Batzner, S.; Xie, Y.; Sun, L.;
# Kolpak, A. M.; Kozinsky, B. "On-the-fly active learning of interpretable
# Bayesian force fields for atomistic rare events." *npj Comput. Mater.* **2020**,
# *6*, 20.  DOI 10.1038/s41524-020-0283-z
#
# **Licence: CC BY 4.0** - verbatim reproduction with attribution is permitted.
#
# Figure 3 panels **a** and **b** are the best on-the-fly AL teaching figure in the
# literature: a 10-ps MD trajectory of aluminium that starts in the FCC crystal and
# melts at t = 5 ps, with the DFT calls marked.  The audience *watches* the model hit
# unfamiliar physics and ask for help.
#
# The plots are **vector**, not embedded raster, so `pdfimages` returns only the atom
# renderings.  These crops are therefore rendered from the page at 400 dpi.

# %%
import os
import subprocess

from PIL import Image

PDF = "_shared/s41524-020-0283-z.pdf"
RAW = "_shared/_flare_pages"
OUT = "../figures"
DPI = 400
os.makedirs(RAW, exist_ok=True)
os.makedirs(OUT, exist_ok=True)
print("Pillow", Image.__version__)

# %%
# Figure 3 sits at the top of page 5.
page = os.path.join(RAW, "pg-05.png")
if not os.path.exists(page):
    subprocess.run(["pdftoppm", "-png", "-r", str(DPI), "-f", "5", "-l", "5",
                    PDF, os.path.join(RAW, "pg")], check=True)
im = Image.open(page).convert("RGB")
print("page 5 at %d dpi:" % DPI, im.size)

# %%
# Fractional crops (left, top, right, bottom) of the page, so they survive a
# change of render resolution.
CROPS = {
    # panels a + b: the temperature trace and the cumulative DFT calls
    "fig_L2_flare_onthefly": (0.040, 0.062, 0.628, 0.2155),
    # panel a alone, if the slide needs something tighter
    "fig_L2a_flare_temperature": (0.040, 0.062, 0.352, 0.2155),
}
W, H = im.size
for name, box in CROPS.items():
    px = (int(box[0] * W), int(box[1] * H), int(box[2] * W), int(box[3] * H))
    crop = im.crop(px)
    crop.save(os.path.join(OUT, name + ".png"), dpi=(DPI, DPI))
    print("%-34s -> %s" % (name, crop.size))

# %%
print("""
Reproduced verbatim under CC BY 4.0, with attribution on the slide.

What the panels show, for the speaker notes:
  a  instantaneous temperature over a 10-ps on-the-fly MD trajectory. Starts in the
     FCC crystal at 162 K, melts at t = 5 ps, reaching 5006 K. Black dots are DFT calls.
  b  cumulative number of DFT calls (solid) and the optimised noise uncertainty
     sigma_n (dotted). Both jump sharply at the melting transition - the model has
     left the chemistry it knows.

Separate result, from Fig. 4a (bulk vacancy diffusion in Al): most DFT calls happen
early, and after the first ~400 ps no further DFT calls are required. The whole
training run took 68.8 h on 32 cores, making FLARE over 300x faster than AIMD.
""")
