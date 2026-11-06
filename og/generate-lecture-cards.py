#!/usr/bin/env python3
"""Generate per-lecture Open Graph cards in the bootcamp's visual style.

Usage (from the repo root):
    python3 og/generate-lecture-cards.py og/lecture-cards.json og/lectures

Edit og/lecture-cards.json to change a card's number, title, subtitle or
instructor, then re-run. Shared drawing helpers live in og/cardkit.py; the
site-wide card is built by og/generate-site-card.py.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cardkit as ck


def card(out, number, title, subtitle, instructor):
    img, d = ck.new_canvas()
    ck.hexagon(d, 955, 315, 180)

    x, maxw = 90, 690

    f_eye = ck.font(23)
    t_size, f_t, lines = ck.fit(d, title, maxw, 3, 58, 36)
    f_s = ck.font(26, bold=False)
    slines = ck.wrap(d, subtitle, f_s, maxw)[:3]

    lh = t_size * 1.22
    block = 54 + len(lines) * lh + 18 + 34 + len(slines) * 36
    y = 96 + max(0, (396 - block) / 2)

    ck.draw_tracked(d, (x, y), number.upper(), f_eye, ck.MINT, 3.2)
    y += 54

    for ln in lines:
        ck.text(d, (x, y), ln, f_t, ck.WHITE)
        y += lh

    y += 18
    d.line([(ck.px(x), ck.px(y)), (ck.px(x + 72), ck.px(y))],
           fill=ck.MINT, width=round(ck.px(5)))
    y += 34

    for ln in slines:
        ck.text(d, (x, y), ln, f_s, ck.BODY)
        y += 36

    ck.text(d, (x, 512), instructor, ck.font(23, bold=False), ck.BODY)
    ck.draw_tracked(d, (x, 556), "AI4CHEMICAL SCIENCES BOOTCAMP · CALTECH",
                    ck.font(21), ck.MINT, 2.0)

    return ck.save(img, out)


if __name__ == "__main__":
    import json
    spec = json.load(open(sys.argv[1]))
    outdir = sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    for s in spec:
        p = os.path.join(outdir, s["slug"] + ".png")
        card(p, s["number"], s["title"], s["subtitle"], s["instructor"])
        print(p, os.path.getsize(p))
