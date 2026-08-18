# True model — latex rubber film simulator

This directory holds the "physics" behind the DOE tutorial's formulation game.
Students see only the storefront that queries this model; the model itself and
the calibration record are kept here so we can prove the pedagogical math plays
before students touch anything.

## The system

**5 factors** (natural units, min → max):

| factor              | range          | notes                                    |
|---------------------|----------------|------------------------------------------|
| `latex_pct`         | 5 – 20 wt%     | hard cap at 20 (infeasible if exceeded)  |
| `filler_phr`        | 0 – 40         | parts per hundred rubber                 |
| `crosslinker_phr`   | 0.5 – 4.0      | curing agent loading                     |
| `plasticizer_phr`   | 0 – 25         |                                          |
| `cure_temp_c`       | 100 – 160 °C   |                                          |

**3 responses:**

- **`tensile_mpa`** — dominantly linear in filler + crosslinker with a strong
  `filler × crosslinker` interaction. A 2-level fractional-factorial detects
  main effects and the BC interaction cleanly.
- **`elongation_pct`** — quadratic in filler, crosslinker, AND plasticizer,
  each with an interior optimum that is *not* on any coarse 3-level OFAT grid
  point. Only center-point lack-of-fit or full response-surface designs
  (CCD, Box-Behnken) can resolve the peak location.
- **`hardness_shore_a`** — red herring. Realistic dependence on filler +
  crosslinker, not tied to either round-1 or round-2 objective.

Noise is additive Gaussian, sized so main effects are ~5σ but curvature is
~20σ only after all three quadratic factors are combined (single-factor
axial deviations are ~2.5σ — visible but not screaming).

## Files

- **[`true_model.py`](true_model.py)** — public API: `simulate(**natural)` and
  `simulate_coded(A, B, C, D, E)`. Coefficient dicts (`TENSILE`, `ELONGATION`,
  `HARDNESS`) are module-level so the storefront and the reveal-plot script can
  import them directly.
- **[`calibrate.py`](calibrate.py)** — the dry run. Simulates the round-1 and
  round-2 plans of four team archetypes (OFAT, fractional factorial without
  center points, fractional factorial *with* center points, and face-centered
  CCD), fits each team's model the way a student actually would, and checks a
  seven-item pass/fail verdict.

## Calibration verdict (current)

```
[PASS] CCD_beats_OFAT_on_elongation             # +58 units on elongation
[PASS] CCD_tensile_customer_ok                  # 7.1 MPa >= 6 MPa floor
[PASS] fracC_detects_curvature                  # LOF center-vs-corner detected
[PASS] fracN_cannot_detect                      # no center points → blind
[PASS] fracC_beats_OFAT_on_elong                # +69 units after axial follow-up
[PASS] tensile_SNR>3                            # 10 / 0.6 = 17
[PASS] elongation_curvature_empirical_SNR>3     # 325 / 18 = 18
```

## The pedagogical story that this simulator produces

**Round 1 — everyone maximizes tensile:** all four team archetypes land on
similar tensile-best formulations (~14.5 MPa). The story looks flat.

**Round 2 — customer also wants elongation:**

| team                       | tensile | elongation | verdict for the customer |
|----------------------------|---------|------------|--------------------------|
| OFAT                       | 8.3     | 307        | stuck at tensile-best point; blind to interior peak |
| Fractional (no center pts) | 5.6     | 311        | linear model, same failure mode |
| Fractional (w/ center pts) | 6.8     | 376        | detects curvature in round 1, axial follow-up in round 2 — nearly matches CCD |
| CCD                        | 7.1     | 366        | fits full quadratic surface, predicts Pareto point directly |

The deliberate takeaway: **your design decides what your data can say.** The
fractional-factorial team that included center points ends up nearly matching
CCD once they invest their round-2 top-up in axial probes. The one that didn't
looks identical to OFAT.

## How to rerun

```bash
source ../../../.venv/bin/activate     # from this directory
python calibrate.py                     # ~5 seconds; prints verdict
```

If you edit coefficients in `true_model.py`, rerun `calibrate.py` and confirm
all seven checks still PASS before touching anything downstream (storefront,
templates, reveal plots).

## If the verdict fails

- **`CCD_beats_OFAT_on_elongation` fails** → the interior elongation peak is
  too close to OFAT's grid. Shift the `*_center` values in `ELONGATION` further
  from 0 (e.g., 0.6 instead of 0.5), or steepen the `*_curvature` values.
- **`tensile_SNR>3` fails** → either main effects are too small or noise is too
  large. Increase `TENSILE["B"]`/`["C"]` or decrease `TENSILE["noise_sd"]`.
- **`fracC_detects_curvature` fails** → total curvature (sum across B, C, D) is
  smaller than 2× the center-point noise. Steepen curvature or reduce
  `ELONGATION["noise_sd"]`.
- **`elongation_curvature_empirical_SNR>3` fails** → same fix.

Tune conservatively — the goal is that these signals are visible against noise,
not that they overwhelm it. If effects become too obvious, students won't feel
the value of proper design.
