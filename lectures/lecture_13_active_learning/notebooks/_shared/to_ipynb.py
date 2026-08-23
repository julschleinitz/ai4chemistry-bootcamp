"""Convert the percent-format .py notebooks in this directory to .ipynb.

Cells are split on `# %%` markers; `# %% [markdown]` blocks become markdown cells
with the leading `# ` stripped.  No jupytext dependency.
"""
import glob
import json
import os


def convert(path):
    src = open(path).read()
    cells, cur, kind = [], [], "code"

    def flush():
        if not cur:
            return
        text = "\n".join(cur).strip("\n")
        if not text.strip():
            return
        if kind == "markdown":
            text = "\n".join(l[2:] if l.startswith("# ") else l.lstrip("#")
                             for l in text.split("\n"))
            cells.append(dict(cell_type="markdown", metadata={},
                              source=text.splitlines(keepends=True)))
        else:
            cells.append(dict(cell_type="code", metadata={}, execution_count=None,
                              outputs=[], source=text.splitlines(keepends=True)))

    for line in src.split("\n"):
        if line.startswith("# %%"):
            flush()
            cur, kind = [], "markdown" if "[markdown]" in line else "code"
        else:
            cur.append(line)
    flush()

    nb = dict(cells=cells, metadata=dict(
        kernelspec=dict(display_name="Python 3", language="python", name="python3"),
        language_info=dict(name="python", version="3.10")),
        nbformat=4, nbformat_minor=5)
    out = path[:-3] + ".ipynb"
    json.dump(nb, open(out, "w"), indent=1)
    return out, len(cells)


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(here)
    for p in sorted(glob.glob(os.path.join(root, "fig_*.py"))):
        out, n = convert(p)
        print("%-42s -> %-44s %d cells" % (os.path.basename(p), os.path.basename(out), n))
