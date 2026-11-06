#!/usr/bin/env python3
"""Regenerate the site-wide Open Graph card (og-image.png).

Usage (from the repo root):
    python3 og/generate-site-card.py og-image.png

This reproduces the original 1200x630 card at 2400x1260. The layout numbers
below were measured off that original so the rebuilt card is the same design,
not a redraw: title cap-tops at y=159 and y=245, accent rule at y=340, body
lines at y=385 and y=432, the Caltech mark at y=504, and the hexagon centred
on (934.5, 314.5) with r=185.

Counts in SUBHEAD must match what the site actually publishes.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cardkit as ck

TITLE = [("AI", ck.WHITE), ("4", ck.MINT), ("Chemical Sciences", ck.WHITE)]
TITLE2 = "Bootcamp"
TAGLINE = "Machine learning and AI for chemistry"
SUBHEAD = "14 lectures · 13 hands-on Colab tutorials"
MARK = "CALTECH"

HEX_COLOR = (15, 110, 86)   # as measured on the original card
X = 90


def build(out):
    img, d = ck.new_canvas()
    ck.hexagon(d, 934.5, 314.5, 185, node_r=26, line_w=7, center_r=34.5,
               color=HEX_COLOR)

    f_title = ck.font(58)
    x = ck.px(X)
    y = ck.px(159) - ck.cap_offset(f_title)
    for s, colour in TITLE:
        d.text((x, y), s, font=f_title, fill=colour)
        x += d.textlength(s, font=f_title)
    ck.text(d, (X, 245), TITLE2, f_title, ck.WHITE, cap_top=True)

    d.line([(ck.px(X), ck.px(342)), (ck.px(X + 70), ck.px(342))],
           fill=ck.MINT, width=round(ck.px(5)))

    f_body = ck.font(31, bold=False)
    ck.text(d, (X, 385), TAGLINE, f_body, ck.BODY, cap_top=True)
    ck.text(d, (X, 432), SUBHEAD, f_body, ck.BODY, cap_top=True)

    ck.draw_tracked(d, (X, 504), MARK, ck.font(25), ck.MINT, 1.0, cap_top=True)

    return ck.save(img, out)


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "og-image.png"
    build(out)
    print(out, os.path.getsize(out))
