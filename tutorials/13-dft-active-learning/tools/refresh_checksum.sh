#!/usr/bin/env bash
# Regenerate predict.py.sha256 after an intentional edit to predict.py.
#
# Run this ONLY before handing the tutorial out. If you run it after students
# have started, every submission built against the old predict.py will be
# rejected as "modified".
set -euo pipefail
cd "$(dirname "$0")/.."

python3 - <<'PY'
import hashlib, pathlib
p = pathlib.Path("predict.py")
h = hashlib.sha256(p.read_bytes()).hexdigest()
pathlib.Path("predict.py.sha256").write_text(h + "  predict.py\n")
print(f"predict.py sha256 = {h}")
PY

python3 tests/test_logic.py
