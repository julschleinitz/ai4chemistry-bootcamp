#!/usr/bin/env python3
"""
Fill in (or clear) the leaderboard placeholders. Run from the tutorial folder.

Three files hold Google-specific values, and two of them are notebook JSON, which
is unpleasant to edit by hand. This does all three and verifies the result.

    # see what is currently configured
    python tools/configure_leaderboard.py --check

    # configure
    python tools/configure_leaderboard.py \
        --endpoint 'https://script.google.com/macros/s/AKfycb.../exec' \
        --published-id '2PACX-1vQ...'

    # put the placeholders back (e.g. before publishing the repo)
    python tools/configure_leaderboard.py --reset

THE TWO VALUES ARE NOT THE SAME THING, and mixing them up is the usual mistake:

  --endpoint      the Apps Script **Web App URL**, from Deploy -> New deployment.
                  Looks like https://script.google.com/macros/s/AKfycb.../exec
                  The NOTEBOOK POSTs to this.

  --published-id  the **published** id, from File -> Share -> Publish to web.
                  Looks like 2PACX-1vQ... and appears only after publishing.
                  It is NOT the spreadsheet id from the /d/<id>/edit URL.
                  The TUTORIAL PAGE reads the sheet through this.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NOTEBOOKS = [ROOT / "dft-active-learning.ipynb",
             ROOT / "dft-active-learning_solutions.ipynb"]
PAGE = ROOT.parent / "dft-active-learning.html"

PH_ENDPOINT = "PASTE_WEB_APP_URL_HERE"
PH_PUBLISHED = "PASTE_PUBLISHED_ID_HERE"

NB_VAR = "LEADERBOARD_ENDPOINT_URL"
PAGE_VAR = "LEADERBOARD_PUBLISHED_ID"
GID_VAR = "LEADERBOARD_GID"

GREEN, RED, YELLOW, RESET = "\033[32m", "\033[31m", "\033[33m", "\033[0m"


def validate(endpoint: str | None, published: str | None) -> list[str]:
    errs = []
    if endpoint is not None:
        if not endpoint.startswith("https://script.google.com/macros/s/"):
            errs.append("--endpoint should start with "
                        "https://script.google.com/macros/s/ — you may have pasted "
                        "the Sheet URL instead of the Apps Script Web App URL")
        elif not endpoint.rstrip("/").endswith("/exec"):
            errs.append("--endpoint should end with /exec (a /dev URL only works "
                        "for you, not for students)")
    if published is not None:
        if published.startswith("http"):
            errs.append("--published-id should be just the id, not a URL")
        elif not published.startswith("2PACX"):
            errs.append("--published-id should start with 2PACX — the id from the "
                        "Publish-to-web link, NOT the spreadsheet id in /d/<id>/edit")
    return errs


def nb_current(path: Path) -> str | None:
    nb = json.loads(path.read_text(encoding="utf-8"))
    for cell in nb["cells"]:
        if cell["cell_type"] != "code":
            continue
        for line in cell["source"]:
            m = re.match(rf'\s*{NB_VAR}\s*=\s*["\'](.*)["\']', line)
            if m:
                return m.group(1)
    return None


def nb_set(path: Path, value: str) -> bool:
    nb = json.loads(path.read_text(encoding="utf-8"))
    hit = False
    for cell in nb["cells"]:
        if cell["cell_type"] != "code":
            continue
        for i, line in enumerate(cell["source"]):
            if re.match(rf'\s*{NB_VAR}\s*=\s*["\']', line):
                nl = "\n" if line.endswith("\n") else ""
                cell["source"][i] = f'{NB_VAR} = "{value}"{nl}'
                hit = True
    if hit:
        path.write_text(json.dumps(nb, indent=1, ensure_ascii=False),
                        encoding="utf-8")
    return hit


def page_current() -> tuple[str | None, str | None]:
    s = PAGE.read_text(encoding="utf-8")
    pub = re.search(rf"var {PAGE_VAR} = '([^']*)'", s)
    gid = re.search(rf"var {GID_VAR} = '([^']*)'", s)
    return (pub.group(1) if pub else None, gid.group(1) if gid else None)


def page_set(published: str, gid: str | None) -> bool:
    s = PAGE.read_text(encoding="utf-8")
    new, n = re.subn(rf"(var {PAGE_VAR} = ')[^']*(')",
                     lambda m: m.group(1) + published + m.group(2), s)
    if gid is not None:
        new, _ = re.subn(rf"(var {GID_VAR} = ')[^']*(')",
                         lambda m: m.group(1) + gid + m.group(2), new)
    if n:
        PAGE.write_text(new, encoding="utf-8")
    return bool(n)


def report() -> int:
    print(f"\nleaderboard configuration in {ROOT.name}/\n")
    unconfigured = 0
    for nb in NOTEBOOKS:
        if not nb.exists():
            print(f"  {RED}missing{RESET}  {nb.name}")
            unconfigured += 1
            continue
        cur = nb_current(nb)
        if cur is None:
            print(f"  {RED}no {NB_VAR}{RESET}  {nb.name}")
            unconfigured += 1
        elif cur.startswith("PASTE_"):
            print(f"  {YELLOW}placeholder{RESET}  {nb.name}  ({NB_VAR})")
            unconfigured += 1
        else:
            print(f"  {GREEN}set{RESET}          {nb.name}  -> {cur[:56]}…")
    pub, gid = page_current()
    if pub is None:
        print(f"  {RED}no {PAGE_VAR}{RESET}  {PAGE.name}")
        unconfigured += 1
    elif pub.startswith("PASTE_"):
        print(f"  {YELLOW}placeholder{RESET}  {PAGE.name}  ({PAGE_VAR})")
        unconfigured += 1
    else:
        print(f"  {GREEN}set{RESET}          {PAGE.name}  -> {pub[:40]}… (gid {gid})")

    print()
    if unconfigured:
        print(f"{YELLOW}{unconfigured} item(s) still on placeholders.{RESET} "
              "The tutorial still works: the notebook saves the payload locally "
              "and the page shows a 'not configured' notice.")
        print("\nConfigure with:\n  python tools/configure_leaderboard.py \\\n"
              "      --endpoint 'https://script.google.com/macros/s/AKfycb.../exec' \\\n"
              "      --published-id '2PACX-1v...'")
    else:
        print(f"{GREEN}fully configured.{RESET} Post one run from the notebook and "
              "hit Refresh on the tutorial page to confirm end to end.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--endpoint", help="Apps Script Web App URL (.../exec)")
    ap.add_argument("--published-id", help="published sheet id, starts with 2PACX")
    ap.add_argument("--gid", default=None, help="sheet tab gid (default: leave as is)")
    ap.add_argument("--check", action="store_true", help="report and exit")
    ap.add_argument("--reset", action="store_true", help="restore the placeholders")
    ap.add_argument("--force", action="store_true",
                    help="apply even if the values look wrong")
    args = ap.parse_args()

    if args.check or not (args.endpoint or args.published_id or args.reset):
        return report()

    if args.reset:
        args.endpoint, args.published_id = PH_ENDPOINT, PH_PUBLISHED
        print("restoring placeholders")
    else:
        errs = validate(args.endpoint, args.published_id)
        if errs:
            print(f"{RED}refusing to apply:{RESET}")
            for e in errs:
                print(f"  - {e}")
            if not args.force:
                print("\n(--force overrides, but check the values first)")
                return 1
            print(f"{YELLOW}--force given, applying anyway{RESET}")

    if args.endpoint:
        for nb in NOTEBOOKS:
            if not nb.exists():
                print(f"  skip {nb.name} (missing)")
                continue
            ok = nb_set(nb, args.endpoint)
            print(f"  {'set ' if ok else 'FAIL'} {NB_VAR} in {nb.name}")
            if not ok:
                return 1
    if args.published_id:
        ok = page_set(args.published_id, args.gid)
        print(f"  {'set ' if ok else 'FAIL'} {PAGE_VAR} in {PAGE.name}")
        if not ok:
            return 1

    # a notebook we just rewrote must still be valid JSON with parseable cells
    import ast
    for nb in NOTEBOOKS:
        if not nb.exists():
            continue
        data = json.loads(nb.read_text(encoding="utf-8"))
        for n, cell in enumerate(data["cells"]):
            if cell["cell_type"] != "code":
                continue
            src = "\n".join(cell["source"])
            if any(l.strip().startswith(("!", "%")) for l in cell["source"]):
                continue
            try:
                ast.parse(src)
            except SyntaxError as exc:
                print(f"{RED}BUG: {nb.name} cell {n} no longer parses: {exc}{RESET}")
                return 1
    print(f"  {GREEN}notebooks still parse{RESET}")

    return report()


if __name__ == "__main__":
    sys.exit(main())
