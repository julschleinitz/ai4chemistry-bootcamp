"""Shared drawing helpers for the bootcamp's Open Graph cards.

Layout is written in 1200x630 design units. Everything is drawn at
DESIGN x SUPERSAMPLE and resampled down to OUT_W x OUT_H, which antialiases
the hexagon artwork (PIL draws lines and ellipses without antialiasing) and
keeps the result sharp on 2x displays.
"""
import math
from PIL import Image, ImageDraw, ImageFont

DESIGN_W, DESIGN_H = 1200, 630   # layout coordinate space
OUT_W, OUT_H = 2400, 1260        # delivered pixel size (2x)
SUPERSAMPLE = 2                  # drawn at OUT * this, then resampled down
K = (OUT_W / DESIGN_W) * SUPERSAMPLE

BG = (10, 82, 66)
MINT = (93, 218, 180)
BODY = (214, 249, 239)
WHITE = (255, 255, 255)

HELV = "/System/Library/Fonts/Helvetica.ttc"


def font(size, bold=True):
    """Font at a design-unit size, scaled into drawing space."""
    return ImageFont.truetype(HELV, round(size * K), index=1 if bold else 0)


def px(v):
    return v * K


def new_canvas():
    img = Image.new("RGB", (round(px(DESIGN_W)), round(px(DESIGN_H))), BG)
    return img, ImageDraw.Draw(img)


def cap_offset(f):
    """Distance from PIL's text origin down to the top of a capital."""
    return f.getbbox("H")[1]


def text(d, xy, s, f, fill, cap_top=False):
    """Draw at design-unit coords; with cap_top=True, y is the cap height line."""
    x, y = px(xy[0]), px(xy[1])
    if cap_top:
        y -= cap_offset(f)
    d.text((x, y), s, font=f, fill=fill)
    return x + d.textlength(s, font=f)


def draw_tracked(d, xy, s, f, fill, tracking, cap_top=False):
    x, y = px(xy[0]), px(xy[1])
    if cap_top:
        y -= cap_offset(f)
    for ch in s:
        d.text((x, y), ch, font=f, fill=fill)
        x += d.textlength(ch, font=f) + px(tracking)


def wrap(d, s, f, maxw):
    """maxw is in design units."""
    limit = px(maxw)
    words, lines, cur = s.split(), [], ""
    for w_ in words:
        t = (cur + " " + w_).strip()
        if d.textlength(t, font=f) <= limit or not cur:
            cur = t
        else:
            lines.append(cur); cur = w_
    if cur:
        lines.append(cur)
    return lines


def fit(d, s, maxw, maxlines, hi, lo):
    """Largest bold design size that wraps s into <= maxlines lines."""
    for size in range(hi, lo - 1, -2):
        f = font(size)
        lines = wrap(d, s, f, maxw)
        if len(lines) <= maxlines:
            return size, f, lines
    f = font(lo)
    return lo, f, wrap(d, s, f, maxw)[:maxlines]


def hexagon(d, cx, cy, r, node_r=26, line_w=7, center_r=None, color=(22, 104, 85)):
    pts = [(px(cx) + px(r) * math.cos(math.radians(a)),
            px(cy) + px(r) * math.sin(math.radians(a)))
           for a in (-90, -30, 30, 90, 150, 210)]
    for i in range(6):
        d.line([pts[i], pts[(i + 1) % 6]], fill=color, width=round(px(line_w)))
    nr = px(node_r)
    for p in pts:
        d.ellipse([p[0] - nr, p[1] - nr, p[0] + nr, p[1] + nr], fill=color)
    cr = px(center_r if center_r is not None else node_r + 14)
    d.ellipse([px(cx) - cr, px(cy) - cr, px(cx) + cr, px(cy) + cr], fill=color)


def save(img, out):
    """Resample to delivery size and write. A 256-colour palette is visually
    lossless on artwork this flat and roughly halves the file size."""
    if img.size != (OUT_W, OUT_H):
        img = img.resize((OUT_W, OUT_H), Image.LANCZOS)
    img = img.quantize(colors=256, method=Image.MEDIANCUT, dither=Image.NONE)
    img.save(out, optimize=True)
    return out
