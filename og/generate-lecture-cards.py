#!/usr/bin/env python3
"""Generate per-lecture Open Graph cards in the bootcamp's visual style.

Usage (from the repo root):
    python3 og/generate-lecture-cards.py og/lecture-cards.json og/lectures

Edit og/lecture-cards.json to change a card's number, title, subtitle or
instructor, then re-run. Output is 1200x630 PNG, one per lecture page.
"""
import math, os, sys
from PIL import Image, ImageDraw, ImageFont

W, H = 1200, 630
BG = (10, 82, 66)
MINT = (93, 218, 180)
BODY = (214, 249, 239)
WHITE = (255, 255, 255)
HEX_LINE = (22, 104, 85)

HELV = "/System/Library/Fonts/Helvetica.ttc"
def font(size, bold=True):
    return ImageFont.truetype(HELV, size, index=1 if bold else 0)

def tw(d, text, f, tracking=0):
    w = d.textlength(text, font=f)
    return w + tracking * max(len(text) - 1, 0)

def draw_tracked(d, xy, text, f, fill, tracking):
    x, y = xy
    for ch in text:
        d.text((x, y), ch, font=f, fill=fill)
        x += d.textlength(ch, font=f) + tracking

def wrap(d, text, f, maxw):
    words, lines, cur = text.split(), [], ""
    for w_ in words:
        t = (cur + " " + w_).strip()
        if d.textlength(t, font=f) <= maxw or not cur:
            cur = t
        else:
            lines.append(cur); cur = w_
    if cur: lines.append(cur)
    return lines

def fit(d, text, maxw, maxlines, hi, lo):
    """Largest bold size that wraps text into <= maxlines lines."""
    for size in range(hi, lo - 1, -2):
        f = font(size)
        lines = wrap(d, text, f, maxw)
        if len(lines) <= maxlines:
            return f, lines
    f = font(lo)
    return f, wrap(d, text, f, maxw)[:maxlines]

def hexagon(d, cx, cy, r, node_r=26):
    pts = [(cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a)))
           for a in (-90, -30, 30, 90, 150, 210)]
    for i in range(6):
        d.line([pts[i], pts[(i + 1) % 6]], fill=HEX_LINE, width=7)
    for p in pts:
        d.ellipse([p[0] - node_r, p[1] - node_r, p[0] + node_r, p[1] + node_r], fill=HEX_LINE)
    cr = node_r + 14
    d.ellipse([cx - cr, cy - cr, cx + cr, cy + cr], fill=HEX_LINE)

def card(out, number, title, subtitle, instructor):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    hexagon(d, 955, 315, 180)

    x = 90
    maxw = 690

    f_eye = font(23)
    f_t, lines = fit(d, title, maxw, 3, 58, 36)
    f_s = font(26, bold=False)
    slines = wrap(d, subtitle, f_s, maxw)[:3]

    lh = int(f_t.size * 1.22)
    block = 34 + 20 + len(lines) * lh + 18 + 5 + 34 + len(slines) * 36
    y = 96 + max(0, (396 - block) // 2)

    # eyebrow
    draw_tracked(d, (x, y), number.upper(), f_eye, MINT, 3.2)
    y += 54

    # title
    for ln in lines:
        d.text((x, y), ln, font=f_t, fill=WHITE)
        y += lh

    # rule
    y += 18
    d.line([(x, y), (x + 72, y)], fill=MINT, width=5)
    y += 34

    # subtitle
    for ln in slines:
        d.text((x, y), ln, font=f_s, fill=BODY)
        y += 36

    # footer
    f_i = font(23, bold=False)
    d.text((x, 512), instructor, font=f_i, fill=BODY)
    f_f = font(21)
    draw_tracked(d, (x, 556), "AI4CHEMICAL SCIENCES BOOTCAMP · CALTECH", f_f, MINT, 2.0)

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
