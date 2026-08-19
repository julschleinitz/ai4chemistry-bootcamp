"""Write every lecture-12 figure notebook, then execute it.

    python3 build_and_run.py            # build + run everything
    python3 build_and_run.py fig_05     # build + run one, by name fragment

Executing the notebooks' own code cells is what guarantees the PNGs in the deck
are exactly what the notebooks produce.
"""
import sys
import os
import pathlib

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE / "_shared"))

import nbbuild                      # noqa: E402
import specs_a, specs_b, specs_c, specs_d, specs_e   # noqa: E402

SPECS = specs_a.ALL + specs_b.ALL + specs_c.ALL + specs_d.ALL + specs_e.ALL


def main(pattern=None):
    os.chdir(HERE)
    built = []
    for fname, title, intro, cells in SPECS:
        if pattern and pattern not in fname:
            continue
        nbbuild.notebook(str(HERE / fname), title, intro, cells)
        built.append(fname)

    print("\n" + "=" * 66)
    for fname in built:
        print("running", fname)
        try:
            nbbuild.run(str(HERE / fname), cwd=str(HERE))
            print("   ok\n")
        except Exception as exc:
            import traceback
            traceback.print_exc()
            print(f"   FAILED: {type(exc).__name__}: {exc}\n")
    print("=" * 66)
    print(f"{len(built)} notebooks built and executed")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
