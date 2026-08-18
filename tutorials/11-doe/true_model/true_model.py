"""Latex rubber film formulation — physics simulator for the DOE tutorial game.

Public API: `simulate(**natural_units) -> dict`.

Factors (natural units):
    latex_pct       5.0 to 20.0    hard constraint: <= 20 (infeasible otherwise)
    filler_phr             0.0 to 40.0
    crosslinker_phr        0.5 to  4.0
    plasticizer_phr        0.0 to 25.0
    cure_temp_c          100.0 to 160.0

Responses:
    tensile_mpa           dominantly linear in filler + crosslinker, with a strong
                          filler x crosslinker interaction. 2-level factorial detects.
    elongation_pct        quadratic in crosslinker (interior optimum near 2.25) AND
                          plasticizer (interior optimum near 12.5). Only CCD-style
                          axial points or center-point lack-of-fit can resolve.
    hardness_shore_a      realistic red herring; not the target of either round.

All response models operate on coded factors in [-1, +1] internally.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Factor ranges (natural units). These are the bounds shown to students.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FactorRange:
    name: str
    low: float
    high: float

    def to_coded(self, x: float) -> float:
        mid = 0.5 * (self.low + self.high)
        half = 0.5 * (self.high - self.low)
        return (x - mid) / half

    def from_coded(self, x_c: float) -> float:
        mid = 0.5 * (self.low + self.high)
        half = 0.5 * (self.high - self.low)
        return mid + x_c * half


RANGES = {
    "latex_pct":  FactorRange("latex_pct",  5.0,  20.0),
    "filler_phr":        FactorRange("filler_phr",        0.0,  40.0),
    "crosslinker_phr":   FactorRange("crosslinker_phr",   0.5,   4.0),
    "plasticizer_phr":   FactorRange("plasticizer_phr",   0.0,  25.0),
    "cure_temp_c":       FactorRange("cure_temp_c",     100.0, 160.0),
}

LATEX_HARD_CAP = 20.0  # exceeding this returns infeasible


# ---------------------------------------------------------------------------
# Response models (coded [-1,+1] units; noise sigmas below)
# ---------------------------------------------------------------------------

# Coefficients calibrated so that:
#   - tensile signal-to-noise > 3 for main effects at corners of 2^k design
#   - elongation curvature signal-to-noise > 3 at CCD axial points
#   - hardness is realistic but decoupled from round-1 and round-2 objectives
#
# Coded variables:  A=latex, B=filler, C=crosslinker, D=plasticizer, E=cure_temp

TENSILE = dict(
    intercept  = 8.0,
    A          = 0.10,
    B          = 3.00,  # dominant linear
    C          = 2.00,  # secondary linear
    D          = -0.20,
    E          = 0.20,
    BC         = 1.50,  # THE interaction (filler x crosslinker)
    noise_sd   = 0.60,
)

# Elongation peaks at interior points that DON'T sit on OFAT's coarse {-1, 0, +1} grid.
# This is what makes CCD's interior probes valuable and OFAT's grid-nearest strategy lose.
ELONGATION = dict(
    intercept       = 380.0,
    A_linear        =   3.0,
    E_linear        =   8.0,
    B_center        =  -0.5,   # peak filler:      natural  ~10 phr (mid-low)
    B_curvature     = -100.0,
    C_center        =  +0.5,   # peak crosslinker: natural   ~3.25 phr
    C_curvature     = -150.0,
    D_center        =  +0.5,   # peak plasticizer: natural  ~18.75 phr
    D_curvature     =  -80.0,
    BC              =  -10.0,
    noise_sd        =  15.0,
)

HARDNESS = dict(
    intercept  = 55.0,
    A          =  0.5,
    B          = 12.0,
    C          =  5.0,
    D          = -3.0,
    E          =  2.0,
    BC         =  3.0,
    noise_sd   =  2.5,
)


def _tensile(A, B, C, D, E, rng):
    m = TENSILE
    y = (m["intercept"] + m["A"]*A + m["B"]*B + m["C"]*C + m["D"]*D + m["E"]*E
         + m["BC"]*B*C)
    return y + rng.gauss(0.0, m["noise_sd"])


def _elongation(A, B, C, D, E, rng):
    m = ELONGATION
    y = (m["intercept"]
         + m["A_linear"]*A
         + m["E_linear"]*E
         + m["B_curvature"]*(B - m["B_center"])**2
         + m["C_curvature"]*(C - m["C_center"])**2
         + m["D_curvature"]*(D - m["D_center"])**2
         + m["BC"]*B*C)
    return y + rng.gauss(0.0, m["noise_sd"])


def _hardness(A, B, C, D, E, rng):
    m = HARDNESS
    y = (m["intercept"] + m["A"]*A + m["B"]*B + m["C"]*C + m["D"]*D + m["E"]*E
         + m["BC"]*B*C)
    return y + rng.gauss(0.0, m["noise_sd"])


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _in_range(name: str, x: float) -> str | None:
    r = RANGES[name]
    if x < r.low or x > r.high:
        return f"{name}={x} outside [{r.low}, {r.high}]"
    return None


def simulate(latex_pct: float,
             filler_phr: float,
             crosslinker_phr: float,
             plasticizer_phr: float,
             cure_temp_c: float,
             *, rng=None) -> dict:
    """Return a dict with the three responses plus feasibility flag.

    On infeasibility, `infeasible` is a reason string and all responses are NaN.
    `rng` should be a `random.Random` instance (or None to use a fresh one).
    """
    import random
    if rng is None:
        rng = random.Random()

    for nm, x in (("latex_pct", latex_pct),
                  ("filler_phr", filler_phr),
                  ("crosslinker_phr", crosslinker_phr),
                  ("plasticizer_phr", plasticizer_phr),
                  ("cure_temp_c", cure_temp_c)):
        problem = _in_range(nm, x)
        if problem:
            return dict(tensile_mpa=math.nan, elongation_pct=math.nan,
                        hardness_shore_a=math.nan, infeasible=problem)

    if latex_pct > LATEX_HARD_CAP:
        return dict(tensile_mpa=math.nan, elongation_pct=math.nan,
                    hardness_shore_a=math.nan,
                    infeasible=f"latex > {LATEX_HARD_CAP}% — mixture unstable")

    A = RANGES["latex_pct"].to_coded(latex_pct)
    B = RANGES["filler_phr"].to_coded(filler_phr)
    C = RANGES["crosslinker_phr"].to_coded(crosslinker_phr)
    D = RANGES["plasticizer_phr"].to_coded(plasticizer_phr)
    E = RANGES["cure_temp_c"].to_coded(cure_temp_c)

    return dict(
        tensile_mpa=_tensile(A, B, C, D, E, rng),
        elongation_pct=_elongation(A, B, C, D, E, rng),
        hardness_shore_a=_hardness(A, B, C, D, E, rng),
        infeasible=None,
    )


def simulate_coded(A: float, B: float, C: float, D: float, E: float, *, rng=None) -> dict:
    """Convenience wrapper — accept coded [-1,+1] factor levels directly."""
    return simulate(
        RANGES["latex_pct"].from_coded(A),
        RANGES["filler_phr"].from_coded(B),
        RANGES["crosslinker_phr"].from_coded(C),
        RANGES["plasticizer_phr"].from_coded(D),
        RANGES["cure_temp_c"].from_coded(E),
        rng=rng,
    )
