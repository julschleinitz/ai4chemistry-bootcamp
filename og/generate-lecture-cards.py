#!/usr/bin/env python3
"""Generate per-lecture Open Graph cards in the bootcamp's visual style.

Usage (from the repo root):
    python3 og/generate-lecture-cards.py og/lecture-cards.json og/lectures

Edit og/lecture-cards.json to change a card's number, title, subtitle or
instructor, then re-run.

Layout is written in 1200x630 design units. Everything is drawn at
DESIGN x SUPERSAMPLE and then resampled down to OUT_W x OUT_H, which both
antialiases the hexagon artwork and keeps the output sharp on 2x displays
(social platforms render these well above 1200px wide).
"""
import math, os, sys
from PIL import Image, ImageDraw, ImageFont

DESIGN_W, DESIGN_H = 1200, 630   # layout coordinate space
OUT_W, OUT_H = 2400, 1260        # delivered pixel size (2x)
SUPERSAMPLE = 2                  # drawn at OUT * this, then resampled down
K = (OUT_W / DESIGN_W) * SUPERSAMPLE

BG = (10, 82, 66)
MINT = (93, 218, 180)
BODY = (214, 249, 239)
WHITE = (255, 255, 255)
HEX_LINE = (22, 104, 85)

HELV = "/System/Library/Fonts/Helvetica.ttc"


def font(size, bold=True):
    """Font at a design-unit size, scaled into drawing space."""
    return ImageFont.truetype(HELV, round(size * K), index=1 if bold else 0)


def px(v):
    return v * K


def draw_tracked(d, xy, text, f, fill, tracking):
    x, y = px(xy[0]), px(xy[1])
    for ch in text:
        d.text((x, y), ch, font=f, fill=fill)
        x += d.textlength(ch, font=f) + px(tracking)


def wrap(d, text, f, maxw):
    """maxw is in design units."""
    limit = px(maxw)
    words, lines, cur = text.split(), [], ""
    for w_ in words:
        t = (cur + " " + w_).strip()
        if d.textlength(t, font=f) <= limit or not cur:
            cur = t
        else:
            lines.append(cur); cur = w_
    if cur:
        lines.append(cur)
    return lines


def fit(d, text, maxw, maxlines, hi, lo):
    """Largest bold design size that wraps text into <= maxlines lines."""
    for size in range(hi, lo - 1, -2):
        f = font(size)
        lines = wrap(d, text, f, maxw)
        if len(lines) <= maxlines:
            return size, f, lines
    f = font(lo)
    return lo, f, wrap(d, text, f, maxw)[:maxlines]


def hexagon(d, cx, cy, r, node_r=26):
    pts = [(px(cx) + px(r) * math.cos(math.radians(a)),
            px(cy) + px(r) * math.sin(math.radians(a)))
           for a in (-90, -30, 30, 90, 150, 210)]
    for i in range(6):
        d.line([pts[i], pts[(i + 1) % 6]], fill=HEX_LINE, width=round(px(7)))
    nr = px(node_r)
    for p in pts:
        d.ellipse([p[0] - nr, p[1] - nr, p[0] + nr, p[1] + nr], fill=HEX_LINE)
    cr = px(node_r + 14)
    d.ellipse([px(cx) - cr, px(cy) - cr, px(cx) + cr, px(cy) + cr], fill=HEX_LINE)


def card(out, number, title, subtitle, instructor):
    img = Image.new("RGB", (round(px(DESIGN_W)), round(px(DESIGN_H))), BG)
    d = ImageDraw.Draw(img)
    hexagon(d, 955, 315, 180)

    x = 90
    maxw = 690

    f_eye = font(23)
    t_size, f_t, lines = fit(d, title, maxw, 3, 58, 36)
    f_s = font(26, bold=False)
    slines = wrap(d, subtitle, f_s, maxw)[:3]

    lh = t_size * 1.22
    block = 54 + len(lines) * lh + 18 + 34 + len(slines) * 36
    y = 96 + max(0, (396 - block) / 2)

    # eyebrow
    draw_tracked(d, (x, y), number.upper(), f_eye, MINT, 3.2)
    y += 54

    # title
    for ln in lines:
        d.text((px(x), px(y)), ln, font=f_t, fill=WHITE)
        y += lh

    # rule
    y += 18
    d.line([(px(x), px(y)), (px(x + 72), px(y))], fill=MINT, width=round(px(5)))
    y += 34

    # subtitle
    for ln in slines:
        d.text((px(x), px(y)), ln, font=f_s, fill=BODY)
        y += 36

    # footer
    d.text((px(x), px(512)), instructor, font=font(23, bold=False), fill=BODY)
    draw_tracked(d, (x, 556), "AI4CHEMICAL SCIENCES BOOTCAMP · CALTECH",
                 font(21), MINT, 2.0)

    if img.size != (OUT_W, OUT_H):
        img = img.resize((OUT_W, OUT_H), Image.LANCZOS)
    # flat artwork: a 256-colour palette is visually lossless here and
    # roughly halves the file size.
    img = img.quantize(colors=256, method=Image.MEDIANCUT, dither=Image.NONE)
    img.save(out, optimize=True)
    return out


if __name__ == "__main__":
    import json
    spec = json.load(open(sys.argv[1]))
    outdir = sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    for s in spec:
        p = os.path.join(outdir, s["slug"] + ".png")
        card(p, s["number"], s["title"], s["subtitle"], s["instructor"])
        print(p, os.path.getsize(p))
