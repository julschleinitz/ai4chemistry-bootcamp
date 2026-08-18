"""Calibration dry-run for the latex-formulation true_model.

Simulates the round-1 and round-2 experimental plans of three team archetypes
and prints a verdict on whether the pedagogical math actually plays.
"""
from __future__ import annotations

import random
import math
import itertools
import statistics
import sys

import numpy as np

from true_model import simulate_coded, TENSILE, ELONGATION, HARDNESS


SEED = 20260819  # bootcamp date
BUDGET_ROUND1 = 15
BUDGET_ROUND2 = 5


# ---------------------------------------------------------------------------
# Design generators (all in coded units)
# ---------------------------------------------------------------------------

def ofat_design(factors: tuple[str, ...] = ("A", "B", "C", "D", "E"),
                levels: tuple[float, ...] = (-1.0, 0.0, 1.0)):
    """OFAT: sweep each of 5 factors across 3 levels holding others at 0.
    15 runs total. Realistic 'naive experimenter' setup — coarse grid on every
    factor rather than fine grid on a subset."""
    assert len(factors) * len(levels) == 15, "budget mismatch"
    all_letters = "ABCDE"
    runs = []
    for f in factors:
        for lvl in levels:
            row = {letter: 0.0 for letter in all_letters}
            row[f] = lvl
            runs.append(row)
    return runs


def fracfact_design_no_center():
    """2^(4-1) with generator D=ABC, on factors A,B,C,D; E held at 0.
    8 corner runs + 4 fold-over runs + 3 arbitrary interior probes = 15.
    (Represents a team that ran factorial + fold-over but no center points.)"""
    corners = list(itertools.product([-1.0, 1.0], repeat=3))
    runs = []
    for a, b, c in corners:
        d = a * b * c
        runs.append({"A": a, "B": b, "C": c, "D": d, "E": 0.0})
    # 4 fold-over runs (mirror the design)
    for a, b, c in corners[:4]:
        d = -(a * b * c)
        runs.append({"A": -a, "B": -b, "C": -c, "D": d, "E": 0.0})
    # 3 arbitrary interior probes at 0.5 axials to hit budget
    for f in ["B", "C", "D"]:
        row = {letter: 0.0 for letter in "ABCDE"}
        row[f] = 0.5
        runs.append(row)
    assert len(runs) == 15
    return runs


def fracfact_design_with_center():
    """Same 2^(4-1) but replace the 3 interior probes with 3 center-point runs.
    Detects curvature via LOF test."""
    corners = list(itertools.product([-1.0, 1.0], repeat=3))
    runs = []
    for a, b, c in corners:
        d = a * b * c
        runs.append({"A": a, "B": b, "C": c, "D": d, "E": 0.0})
    for a, b, c in corners[:4]:
        d = -(a * b * c)
        runs.append({"A": -a, "B": -b, "C": -c, "D": d, "E": 0.0})
    # 3 center points
    for _ in range(3):
        runs.append({letter: 0.0 for letter in "ABCDE"})
    assert len(runs) == 15
    return runs


def ccd_design():
    """Face-centered CCD on 3 factors (B,C,D); A,E held at 0.
    8 corners + 6 axial + 1 center = 15."""
    corners = list(itertools.product([-1.0, 1.0], repeat=3))
    runs = []
    for b, c, d in corners:
        runs.append({"A": 0.0, "B": b, "C": c, "D": d, "E": 0.0})
    axials = [
        ("B", -1), ("B", +1), ("C", -1), ("C", +1), ("D", -1), ("D", +1)
    ]
    for _ in axials:
        pass  # will construct below
    for f, sign in axials:
        row = {letter: 0.0 for letter in "ABCDE"}
        row[f] = float(sign)
        runs.append(row)
    runs.append({letter: 0.0 for letter in "ABCDE"})
    assert len(runs) == 15
    return runs


# ---------------------------------------------------------------------------
# Simulation runner
# ---------------------------------------------------------------------------

def run_design(runs, rng):
    """Execute each row of `runs` against the true_model. Returns list of dicts
    with factor levels AND response values."""
    out = []
    for row in runs:
        result = simulate_coded(row["A"], row["B"], row["C"], row["D"], row["E"], rng=rng)
        merged = dict(row)
        merged.update(result)
        out.append(merged)
    return out


# ---------------------------------------------------------------------------
# Analysis — how each team would model their data
# ---------------------------------------------------------------------------

def fit_ofat_and_predict_best(rows, response_key):
    """OFAT team: fits per-factor linear model to the swept levels and greedily
    combines the per-factor best levels. Returns (best_coded_point, predicted_y).

    This is what students actually do: read off "best temperature = 140, best
    filler = 30, best crosslinker = 3.5" and combine — ignoring interactions."""
    best_per_factor = {}
    for f in "ABCDE":
        levels_seen = sorted({row[f] for row in rows if not any(row[x] != 0.0 for x in "ABCDE" if x != f)})
        levels_seen = [lvl for lvl in levels_seen if lvl != 0.0] + [0.0]
        # Find rows where only factor f is nonzero
        f_rows = [row for row in rows
                  if all(row[x] == 0.0 for x in "ABCDE" if x != f) and row[f] in levels_seen]
        if not f_rows:
            best_per_factor[f] = 0.0
            continue
        best = max(f_rows, key=lambda r: r[response_key] if not math.isnan(r[response_key]) else -1e9)
        best_per_factor[f] = best[f]
    return best_per_factor


def fit_2level_linear_and_predict(rows, response_key):
    """Fits main effects + all 2-way interactions on the corners. Returns
    coefficient dict and predicted-best coded point (search all corners)."""
    corners = [r for r in rows if all(abs(r[k]) == 1.0 for k in "ABCD")]
    if not corners:
        return {}, None, None
    # Build design matrix: intercept, A, B, C, D, AB, AC, AD, BC, BD, CD
    terms = [
        ("1", lambda r: 1.0),
        ("A", lambda r: r["A"]), ("B", lambda r: r["B"]),
        ("C", lambda r: r["C"]), ("D", lambda r: r["D"]),
        ("AB", lambda r: r["A"]*r["B"]),
        ("AC", lambda r: r["A"]*r["C"]),
        ("AD", lambda r: r["A"]*r["D"]),
        ("BC", lambda r: r["B"]*r["C"]),
        ("BD", lambda r: r["B"]*r["D"]),
        ("CD", lambda r: r["C"]*r["D"]),
    ]
    n = len(corners)
    if n < len(terms):
        # Drop lower-priority interactions to fit
        terms = terms[:min(n, len(terms))]
    X = np.array([[fn(r) for _, fn in terms] for r in corners])
    y = np.array([r[response_key] for r in corners])
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    coefs = dict(zip((name for name, _ in terms), coef))

    # Predict at all 3^4 grid points, pick best
    grid = list(itertools.product([-1.0, -0.5, 0.0, 0.5, 1.0], repeat=4))
    best_y = -1e9
    best_pt = None
    for a, b, c, d in grid:
        row = {"A": a, "B": b, "C": c, "D": d, "E": 0.0}
        y_hat = sum(fn(row) * coefs.get(name, 0.0) for name, fn in terms)
        if y_hat > best_y:
            best_y = y_hat
            best_pt = row
    return coefs, best_pt, best_y


def lof_center_test(rows, response_key):
    """Center-point lack-of-fit test. Returns (mean_corners, mean_centers, sd_centers,
    curvature_signal, detected)."""
    corners = [r for r in rows if all(abs(r[k]) == 1.0 for k in "ABCD")]
    centers = [r for r in rows if all(r[k] == 0.0 for k in "ABCDE")]
    if not corners or len(centers) < 2:
        return None
    mc = statistics.mean([r[response_key] for r in corners])
    m0 = statistics.mean([r[response_key] for r in centers])
    sd0 = statistics.stdev([r[response_key] for r in centers])
    curvature = m0 - mc
    # Detected if |curvature| exceeds 2x sd of centers
    detected = abs(curvature) > 2 * (sd0 if sd0 > 0 else 1e-9)
    return dict(mean_corner=mc, mean_center=m0, sd_center=sd0,
                curvature=curvature, detected=detected)


def fit_ccd_quadratic_and_predict(rows, response_key):
    """Fits main + interactions + quadratic terms on B, C, D. Predicts best over
    grid."""
    terms = [
        ("1", lambda r: 1.0),
        ("B", lambda r: r["B"]), ("C", lambda r: r["C"]), ("D", lambda r: r["D"]),
        ("BC", lambda r: r["B"]*r["C"]),
        ("BD", lambda r: r["B"]*r["D"]),
        ("CD", lambda r: r["C"]*r["D"]),
        ("BB", lambda r: r["B"]**2),
        ("CC", lambda r: r["C"]**2),
        ("DD", lambda r: r["D"]**2),
    ]
    X = np.array([[fn(r) for _, fn in terms] for r in rows])
    y = np.array([r[response_key] for r in rows])
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    coefs = dict(zip((name for name, _ in terms), coef))
    grid = list(itertools.product(np.linspace(-1, 1, 11), repeat=3))
    best_y, best_pt = -1e9, None
    for b, c, d in grid:
        row = {"A": 0.0, "B": b, "C": c, "D": d, "E": 0.0}
        y_hat = sum(fn(row) * coefs.get(name, 0.0) for name, fn in terms)
        if y_hat > best_y:
            best_y, best_pt = y_hat, row
    return coefs, best_pt, best_y


# ---------------------------------------------------------------------------
# Verdict
# ---------------------------------------------------------------------------

def evaluate_true_at(pt, rng, reps=5):
    """Evaluate the true model at a point averaged over `reps` reps."""
    ys = [simulate_coded(pt["A"], pt["B"], pt["C"], pt["D"], pt["E"], rng=rng)
          for _ in range(reps)]
    return dict(
        tensile_mean=statistics.mean(y["tensile_mpa"] for y in ys),
        tensile_sd=statistics.stdev(y["tensile_mpa"] for y in ys),
        elongation_mean=statistics.mean(y["elongation_pct"] for y in ys),
        elongation_sd=statistics.stdev(y["elongation_pct"] for y in ys),
    )


def main():
    print("=" * 78)
    print("LATEX FORMULATION TRUE-MODEL — CALIBRATION DRY RUN")
    print("=" * 78)
    print(f"\nTensile coefs: {TENSILE}")
    print(f"Elongation coefs: {ELONGATION}")
    print(f"Hardness coefs: {HARDNESS}\n")

    rng = random.Random(SEED)

    # --- ROUND 1: each team designs and executes 15 runs ---
    ofat_runs   = run_design(ofat_design(), rng)
    fracC_runs  = run_design(fracfact_design_with_center(), rng)
    fracN_runs  = run_design(fracfact_design_no_center(), rng)
    ccd_runs    = run_design(ccd_design(), rng)

    # --- ROUND 1 tensile analysis ---
    print("-" * 78)
    print("ROUND 1: teams optimize tensile from 15 runs")
    print("-" * 78)

    ofat_best_pt = fit_ofat_and_predict_best(ofat_runs, "tensile_mpa")
    ofat_best_pt["E"] = ofat_best_pt.get("E", 0.0)
    fracC_coefs, fracC_best_pt, fracC_best_yhat = fit_2level_linear_and_predict(fracC_runs, "tensile_mpa")
    fracN_coefs, fracN_best_pt, fracN_best_yhat = fit_2level_linear_and_predict(fracN_runs, "tensile_mpa")
    ccd_coefs, ccd_best_pt, ccd_best_yhat = fit_ccd_quadratic_and_predict(ccd_runs, "tensile_mpa")

    print(f"\nOFAT team predicted-best tensile point (greedy per-factor): {ofat_best_pt}")
    print(f"Frac-fact (w/ center) team predicted-best tensile: {fracC_best_pt} -> yhat={fracC_best_yhat:.2f}")
    print(f"Frac-fact (no center) team predicted-best tensile: {fracN_best_pt} -> yhat={fracN_best_yhat:.2f}")
    print(f"CCD team predicted-best tensile: {ccd_best_pt} -> yhat={ccd_best_yhat:.2f}")

    # Evaluate truth at each team's predicted best
    truth_ofat   = evaluate_true_at(ofat_best_pt, random.Random(SEED + 1))
    truth_fracC  = evaluate_true_at(fracC_best_pt, random.Random(SEED + 2))
    truth_fracN  = evaluate_true_at(fracN_best_pt, random.Random(SEED + 3))
    truth_ccd    = evaluate_true_at(ccd_best_pt, random.Random(SEED + 4))

    print("\nActual tensile at predicted-best point (mean over 5 reps):")
    print(f"  OFAT       : {truth_ofat['tensile_mean']:6.2f} ± {truth_ofat['tensile_sd']:.2f}")
    print(f"  Frac (C)   : {truth_fracC['tensile_mean']:6.2f} ± {truth_fracC['tensile_sd']:.2f}")
    print(f"  Frac (N)   : {truth_fracN['tensile_mean']:6.2f} ± {truth_fracN['tensile_sd']:.2f}")
    print(f"  CCD        : {truth_ccd['tensile_mean']:6.2f} ± {truth_ccd['tensile_sd']:.2f}")

    # --- ROUND 2: customer also wants elongation ---
    print("\n" + "-" * 78)
    print("ROUND 2: customer twist — also maximize elongation. +5 experiment-$")
    print("-" * 78)

    # For elongation, refit on the combined dataset. Also check curvature detection.
    # OFAT does 5 confirmation runs at their tensile-best point (learns basically nothing new about elongation shape)
    ofat_round2 = [{**ofat_best_pt, "A": ofat_best_pt.get("A", 0.0), "E": 0.0}] * 5
    ofat_round2_runs = run_design(ofat_round2, rng)
    ofat_all = ofat_runs + ofat_round2_runs

    # Frac-fact (with center) does 4 axial-ish probes based on curvature hint + 1 center
    fracC_round2 = [
        {"A":0.0,"B":-1.0,"C":0.0,"D":0.0,"E":0.0},
        {"A":0.0,"B":+1.0,"C":0.0,"D":0.0,"E":0.0},
        {"A":0.0,"B":0.0,"C":-1.0,"D":0.0,"E":0.0},
        {"A":0.0,"B":0.0,"C":+1.0,"D":0.0,"E":0.0},
        {"A":0.0,"B":0.0,"C":0.0,"D":0.0,"E":0.0},
    ]
    fracC_round2_runs = run_design(fracC_round2, rng)
    fracC_all = fracC_runs + fracC_round2_runs

    fracN_round2_runs = run_design(fracC_round2, rng)  # same "smart" round-2 (no-center team gets a hint from tensile fit)
    fracN_all = fracN_runs + fracN_round2_runs

    # CCD does 5 validation runs at predicted pareto-optimal point
    ccd_pareto_pt = fit_ccd_quadratic_and_predict(ccd_runs, "elongation_pct")[1]
    ccd_round2 = [ccd_pareto_pt] * 5
    ccd_round2_runs = run_design(ccd_round2, rng)
    ccd_all = ccd_runs + ccd_round2_runs

    # LOF tests on the elongation data
    lof_fracC = lof_center_test(fracC_all, "elongation_pct")
    lof_fracN = lof_center_test(fracN_all, "elongation_pct")
    lof_ccd   = lof_center_test(ccd_all, "elongation_pct")

    print("\nElongation curvature detection (center-point LOF):")
    for tag, lof in [("Frac (w/ center)", lof_fracC),
                     ("Frac (no center)", lof_fracN),
                     ("CCD",              lof_ccd)]:
        if lof is None:
            print(f"  {tag:20}: no centers in design (undetectable)")
        else:
            print(f"  {tag:20}: mean_corner={lof['mean_corner']:6.1f} "
                  f"mean_center={lof['mean_center']:6.1f} sd_center={lof['sd_center']:5.1f} "
                  f"curvature={lof['curvature']:+6.1f}  detected={lof['detected']}")

    # Refit for elongation:
    # OFAT: greedy per-factor best (assumes linearity — will fail on interior optima)
    ofat_elong_best_pt = fit_ofat_and_predict_best(ofat_all, "elongation_pct")
    # Frac (w/ center) team, having detected curvature, refits a full quadratic on
    # their combined dataset (corners + centers + round-2 axials).
    fracC_coefs, fracC_elong_best_pt, _ = fit_ccd_quadratic_and_predict(fracC_all, "elongation_pct")
    # Frac (no center) team never detected curvature, stays with linear model.
    _, fracN_elong_best_pt, _ = fit_2level_linear_and_predict(fracN_all, "elongation_pct")
    ccd_coefs, ccd_pareto_pt, ccd_elong_best_yhat = fit_ccd_quadratic_and_predict(ccd_all, "elongation_pct")

    # For each team, pick a "Pareto-ish" point: highest elongation among predicted-tensile>=quantile
    truth_ofat_2  = evaluate_true_at(ofat_elong_best_pt,  random.Random(SEED + 11))
    truth_fracC_2 = evaluate_true_at(fracC_elong_best_pt, random.Random(SEED + 12))
    truth_fracN_2 = evaluate_true_at(fracN_elong_best_pt, random.Random(SEED + 13))
    truth_ccd_2   = evaluate_true_at(ccd_pareto_pt,       random.Random(SEED + 14))

    print("\nActual (tensile, elongation) at each team's round-2 best-elong pick:")
    for tag, t in [("OFAT",         truth_ofat_2),
                   ("Frac (w/ ctr)",truth_fracC_2),
                   ("Frac (no ctr)",truth_fracN_2),
                   ("CCD",          truth_ccd_2)]:
        print(f"  {tag:15}: tensile={t['tensile_mean']:6.2f}  elongation={t['elongation_mean']:6.1f}")

    # --- VERDICT ---
    print("\n" + "=" * 78)
    print("VERDICT")
    print("=" * 78)

    verdict = {}

    # 1. CCD's round-2 elongation clearly beats OFAT's, at a customer-acceptable
    #    tensile (>= 6 MPa). This is the pedagogical Pareto win: OFAT stuck at
    #    tensile-best point with mediocre elongation; CCD finds interior peak.
    TENSILE_FLOOR = 6.0
    ELONG_GAP     = 30.0
    verdict["CCD_beats_OFAT_on_elongation"] = (
        truth_ccd_2["elongation_mean"] - truth_ofat_2["elongation_mean"] > ELONG_GAP
    )
    verdict["CCD_tensile_customer_ok"] = truth_ccd_2["tensile_mean"] >= TENSILE_FLOOR

    # 2. Fractional factorial WITH center detects curvature and (once it refits
    #    with axial probes) closes the gap to CCD substantially — beats OFAT
    #    even if it doesn't fully match CCD.
    verdict["fracC_detects_curvature"] = bool(lof_fracC and lof_fracC["detected"])
    verdict["fracN_cannot_detect"]     = (lof_fracN is None) or (not lof_fracN["detected"])
    verdict["fracC_beats_OFAT_on_elong"] = (
        truth_fracC_2["elongation_mean"] > truth_ofat_2["elongation_mean"]
    )

    # 3. Tensile SNR > 3 at corners
    tensile_corner_range = 2 * TENSILE["B"] + 2 * TENSILE["C"]  # main-effect range across ±1
    verdict["tensile_SNR>3"] = (tensile_corner_range / TENSILE["noise_sd"]) > 3

    # 4. Empirical elongation curvature (LOF center-vs-corner) SNR > 3, using
    #    the fractional-factorial team's own LOF measurement — the joint curvature
    #    across B, C, D is much larger than any single-axis deviation.
    if lof_fracC:
        empirical_snr = abs(lof_fracC["curvature"]) / max(lof_fracC["sd_center"], 1e-6)
        verdict["elongation_curvature_empirical_SNR>3"] = empirical_snr > 3
    else:
        verdict["elongation_curvature_empirical_SNR>3"] = False

    print()
    for k, v in verdict.items():
        mark = "PASS" if v else "FAIL"
        print(f"  [{mark}] {k}: {v}")

    all_pass = all(verdict.values())
    print()
    print("OVERALL: " + ("PASS ✓" if all_pass else "FAIL ✗ — tune coefficients"))
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
