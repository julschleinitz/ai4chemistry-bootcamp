"""Write .ipynb files without nbformat, and execute their code cells.

Executing the notebook's own code cells (rather than a parallel script) is what
guarantees the figure in the deck is exactly what the notebook produces.
"""
import json
import os

HEADER = """import sys, pathlib
sys.path.insert(0, str(pathlib.Path.cwd().parent / "_shared"))
sys.path.insert(0, str(pathlib.Path.cwd() / "_shared"))
import numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import style, gp as gpmod, landscape as land, doe as doemod
style.use_deck_style()
OUT = "../lecture_12_figures/generated"
"""


def notebook(path, title, intro, cells):
    """cells: list of (markdown_or_None, code_or_None)."""
    nb = {"cells": [], "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python",
                       "name": "python3"},
        "language_info": {"name": "python", "version": "3.10"}},
        "nbformat": 4, "nbformat_minor": 5}

    def md(src):
        nb["cells"].append({"cell_type": "markdown", "metadata": {},
                            "source": src.splitlines(keepends=True)})

    def code(src):
        nb["cells"].append({"cell_type": "code", "execution_count": None,
                            "metadata": {}, "outputs": [],
                            "source": src.rstrip("\n").splitlines(keepends=True)})

    md(f"# {title}\n\n{intro}\n")
    code(HEADER)
    for m, c in cells:
        if m:
            md(m)
        if c:
            code(c)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf8") as fh:
        json.dump(nb, fh, indent=1, ensure_ascii=False)
    print("wrote", path)


def run(path, cwd=None):
    """Execute every code cell of a notebook in one namespace."""
    nb = json.load(open(path, encoding="utf8"))
    src = "\n".join("".join(c["source"]) for c in nb["cells"]
                    if c["cell_type"] == "code")
    old = os.getcwd()
    if cwd:
        os.chdir(cwd)
    ns = {"__name__": "__main__"}
    try:
        exec(compile(src, path, "exec"), ns)
    finally:
        os.chdir(old)
    return ns
