#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Build the student bundle. Run from inside instructor/.
#
#   ./run_all.sh smoke     300 molecules, ~2 min -- proves the whole path works
#   ./run_all.sh full      all 8,528 -- ~15 min, almost all of it API paging
#
# There is no GPU step and no quantum chemistry: the labels are the published
# DFT descriptors from Haas et al., Digital Discovery 2025, 4, 222, fetched from
# the MolSSI Descriptor Libraries API. Their authors spent the CPU hours.
#
# API responses are cached per chunk under ../data/api_cache/, so re-runs are
# free and an interrupted run resumes. Delete that directory to force a refetch.
# ---------------------------------------------------------------------------
set -euo pipefail

MODE="${1:-smoke}"

case "$MODE" in
  smoke) LIMIT="--limit 300"; NDEV=40;   NTEST=40   ;;
  full)  LIMIT="";            NDEV=1000; NTEST=1000 ;;
  *) echo "usage: $0 [smoke|full]" >&2; exit 2 ;;
esac

echo "== mode=$MODE =="

echo; echo "== 00 confirm the upstream schema has not changed =="
python 01_fetch_dft_labels.py --verify-header

echo; echo "== 01 fetch the published DFT labels =="
python 01_fetch_dft_labels.py $LIMIT

echo; echo "== 02 splits + seal + student bundle =="
python 02_make_splits.py --n-dev "$NDEV" --n-test "$NTEST"

echo; echo "== 03 logic tests =="
python ../tests/test_logic.py

echo
echo "== done =="
echo "student bundle:  ../data/student/"
echo "hidden test set: ../data/instructor/test_hidden.csv   (keep this private)"
echo
echo "Students do not need a zip -- the notebook fetches the bundle from GitHub."
echo "Just commit data/student/ before class:"
echo "  git add ../data/student && git commit -m 'tutorial 13 student bundle'"
echo
echo "Score submissions during the session:"
echo "  cd ../leaderboard && python score_submissions.py \\"
echo "      --submissions <drive folder> --audit"
