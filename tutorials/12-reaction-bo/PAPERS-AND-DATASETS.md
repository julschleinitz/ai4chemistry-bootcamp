# Tutorial 12 — Bayesian Optimization for Reaction Conditions: source papers & datasets

Four papers anchor this tutorial. All four report (or aggregate) reaction-condition datasets that are
public and reusable without re-running any wet-lab chemistry. Only one — Felton, Rittig & Lapkin's
*Summit* — ships an installable, general-purpose open-source codebase built specifically for
benchmarking BO strategies on these datasets, so it is the one summarized in full below and the one
the tutorial notebook's dataset loaders are modeled on (we vendor flat CSVs rather than the `summit`
package itself, to keep the Colab environment light — see notebook README).

## 1. Perera et al., *Science* 2018 — "A platform for automated nanomole-scale reaction screening and micromole-scale synthesis in flow"
- DOI: 10.1126/science.aap9112
- **Dataset**: 5,760 Suzuki–Miyaura couplings (7 substrate pairs × 12 ligands × 8 bases × 4 solvents,
  UPLC-MS yield), generated on a nanomole-scale flow platform at >1,500 reactions/24 h.
- No BO in the original paper — it's a screening/HTE platform paper — but this dataset became the
  most widely reused public benchmark for reaction-optimization algorithms (including in Summit,
  below) precisely because it is a full combinatorial grid, so any subset can be queried offline to
  simulate a closed-loop optimization without wet-lab access.
- Public data: mirrored in several ML-for-chemistry benchmark repos (e.g. `kjappelbaum/awesome-chemistry-datasets`) as a flat CSV.

## 2. Reizman & Jensen, *React. Chem. Eng.* 2016 — "Suzuki–Miyaura cross-coupling optimization enabled by automated feedback"
- DOI: 10.1039/C6RE00153J
- **Dataset**: closed-loop, automated-feedback optimization of a Suzuki coupling (ligand choice ×
  temperature × residence time × stoichiometry) using the SNOBFIT algorithm on a flow platform;
  four ligand sub-datasets, ~100 reactions total, all yields recorded and published.
- Smaller and noisier than Perera's grid, which makes it a useful "hard mode" — low-data,
  higher-variance — benchmark alongside it.

## 3. Shields et al., *Nature* 2021 — "Bayesian reaction optimization as a tool for chemical synthesis"
- DOI: 10.1038/s41586-021-03213-y
- **Dataset**: a palladium-catalyzed direct-arylation benchmark (~1,536 conditions: ligand × base ×
  solvent × concentration × temperature grid, all experimentally measured), plus two real-world
  optimizations (Mitsunobu esterification, deoxyfluorination) run *live* using the paper's own tool.
- **Code**: `EDBO` (Experimental Design via Bayesian Optimization), github.com/b-shields/edbo — open
  source, ships the direct-arylation descriptor matrices (Mordred + one-hot) pre-computed, plus the
  Mitsunobu/deoxyfluorination notebooks. This is the paper this bootcamp's existing
  `reaction-bo.html` page and notebook are conceptually closest to (GP surrogate + EI/UCB over a
  descriptor-encoded condition space).
- Headline finding: BO matched or beat expert chemists' own choices in a blinded game where
  chemists and a BO agent optimized the same benchmark, with BO more consistent (lower variance)
  round to round — directly motivates why we run 5 seeds and report std, not just best-case, in the
  tutorial's leaderboard.

## 4. Felton, Rittig & Lapkin, *Chemistry–Methods* 2021 — "Summit: Benchmarking Machine Learning Methods for Reaction Optimisation" — **paper with code, summarized below**
- DOI: 10.1002/cmtd.202000051 (preprint: chemrxiv.org/doi/10.26434/chemrxiv.12939806.v2)
- **Code**: github.com/sustainable-processes/summit — MIT-licensed, `pip install summit`, actively
  documented (readthedocs).

### Summary

Summit's core observation is that comparing reaction-optimization algorithms honestly is hard
because every paper runs its BO loop on different, mostly non-public wet-lab data, so results
aren't comparable across methods or even reproducible. Summit's fix is to fit fast, cheap
*emulator* models (a neural network trained on the underlying experimental dataset predicts yield/
selectivity as a function of conditions) that stand in for the real reaction, so any number of BO
strategies can be run against the exact same in silico "oracle" as many times, with as many seeds,
as needed — without consuming any more lab time. They built two new in silico benchmarks this way
directly from real experimental campaigns: a Pd-catalysed **C–N cross-coupling** (from 96 reactions
published by Baumgartner et al.; the emulator's cross-validated MAE is ~8% yield) choosing among 3
catalysts (t-BuXPhos, t-BuBrettPhos, AlPhos) × 4 bases (TEA, TMG, BTMG, DBU) plus continuous
residence time (1–30 min), temperature (30–100 °C) and base equivalents (1.0–2.5); and a
nucleophilic aromatic substitution (**SnAr**) benchmark. Categorical reagents (catalysts, bases,
ligands) are represented by physical-organic descriptors rather than bare one-hot labels — for the
C–N benchmark, the first two σ-moments from the COSMO-RS conductor-like screening model, which act
as continuous, transferable "universal" descriptors for any molecule — so a GP surrogate can
generalize across catalyst/base choices instead of treating each as an unrelated arm. They then
benchmarked seven optimization strategies (including several BO variants with different acquisition
functions, a genetic algorithm, SNOBFIT, and a design-of-experiments baseline) across these and the
Perera/Reizman-style benchmarks, at matched experiment budgets and repeated over multiple random
seeds. The main result: BO strategies consistently outperform the classical DoE and non-Bayesian
baselines commonly used in reaction optimization, but *which* acquisition function wins is
benchmark-dependent — no single strategy dominates everywhere, which is precisely the design-choice
tradeoff this tutorial asks students to explore themselves (Step 3–4 in the notebook) rather than
hard-coding one "correct" answer.

### Why this is the one the tutorial builds on
1. It is the only one of the four built explicitly as a *reusable benchmarking harness* — the
   others each report one dataset from one study.
2. It already validates the "run several BO strategies against a fixed emulator/lookup table, over
   multiple seeds, and compare AUC / max / variance" evaluation protocol that this tutorial's Step 7
   leaderboard reproduces almost verbatim.
3. Its categorical-descriptor treatment (COSMO-RS σ-moments) is a clean, teachable example of the
   "precomputed vs. retrieved descriptors" choice in Step 2 of the notebook, alongside one-hot and
   Mordred/RDKit descriptors from EDBO and Perera-style grids.

### References
- Perera, D. et al. *Science* 2018, 359(6374), 429–434. https://doi.org/10.1126/science.aap9112
- Reizman, B. J.; Jensen, K. F. *React. Chem. Eng.* 2016, 1, 658–666. https://doi.org/10.1039/C6RE00153J
- Shields, B. J. et al. *Nature* 2021, 590, 89–96. https://doi.org/10.1038/s41586-021-03213-y ·
  code: https://github.com/b-shields/edbo
- Felton, K. C.; Rittig, J. G.; Lapkin, A. A. *Chem. Methods* 2021, 1, 116–122.
  https://doi.org/10.1002/cmtd.202000051 · code: https://github.com/sustainable-processes/summit
