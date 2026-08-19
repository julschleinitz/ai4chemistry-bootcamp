# Tutorial — Active Learning on Carboxylic Acid DFT Descriptors

**AI4Chemical Sciences Bootcamp, Caltech · 90 min · follows Lecture 13 (Active Learning)**
J. Schleinitz

---

## 0. One-paragraph statement of the exercise

Students are given a pool of **8,528 commercially available carboxylic acids** whose
conformer-ensemble **DFT** descriptors (**156 numbers per molecule**) already exist — computed
by Haas *et al.* at a cost of over a million CPU hours. The descriptors are *hidden*. Students
may buy them for **at most 600 molecules**, one batch of 50 at a time, and must train a Chemprop
D-MPNN that predicts all 156 for a **hidden test set they never see**. They choose the model, the
seed set, and the acquisition function. They submit a checkpoint plus a fixed `predict.py`; the
instructor scores every submission on the hidden test set and publishes a leaderboard ranked on
**accuracy *and* uncertainty calibration**.

The tutorial is the lecture's argument made operational: *the model is the deliverable, so buy
the labels that make the model good everywhere.*

---

## 1. Why this dataset

> Haas, B. C.; Hardy, M. A.; Sowndarya S. V., S.; Adams, K.; Coley, C. W.; Paton, R. S.;
> Sigman, M. S. **"Rapid prediction of conformationally-dependent DFT-level descriptors using
> graph neural networks for carboxylic acids and alkyl amines."** *Digital Discovery* **2025**,
> *4*, 222–233. DOI [10.1039/D4DD00284A](https://doi.org/10.1039/D4DD00284A) · **CC BY 4.0**
> Data: FigShare [10.6084/m9.figshare.25213742](https://doi.org/10.6084/m9.figshare.25213742)
> API: <https://descriptor-libraries.molssi.org/api/acids/>

8,528 carboxylic acids, 71,324 conformers, 275 ensemble DFT descriptors. **We use their labels
verbatim.** Nothing in this tutorial recomputes chemistry.

Four reasons this is the right dataset, and you should say all four:

1. **The oracle is expensive, and honestly so.** The paper reports **over 1,000,000 CPU hours**
   for the acid library — about **117 CPU-hours per molecule**. A 600-label budget is roughly
   **70,000 CPU-hours**, eight CPU-years. Section (a) prints that number before students spend
   anything. No hand-waving about a "simulated" cost.
2. **It is real DFT, at a level a chemist recognises.** M06-2X/def2-TZVP single points on
   B3LYP-D3(BJ)/6-31G(d,p) geometries, Maestro conformer ensembles, GoodVibes quasi-harmonic
   Gibbs energies, Boltzmann-weighted at 298.15 K over a 5 kcal/mol window. Gas phase.
3. **There is a published benchmark to land the plane on.** Their own GNN, trained on 7,290
   molecules, reports per-descriptor test MAEs. Students trained on ≤600 can compare directly
   (with a caveat — see §5).
4. **The chemistry is broad.** Carboxylic acids are the most common acid handle in medicinal
   chemistry, the substrate class for decarboxylative and amide couplings, chiral-acid ligands
   in catalysis, and MOF linkers. One dataset, four audiences.

**Instructor compute: about fifteen minutes, no GPU.** That is the headline change from any
plan that recomputes descriptors — the authors already spent the CPU hours, published under
CC BY, and MolSSI serves the result over an open API.

### Licensing

CC BY 4.0. Attribution is required and appears in `01_fetch_dft_labels.py`, `targets.json`, the
student README, and sections (a) and (e) of the notebook.

**Do not source acids from Enamine directly.** Enamine's Terms of Use §15.2 prohibits "using,
processing, analyzing, modelling, or incorporating any Enamine Data into any computational
system, including but not limited to AI/ML Systems, traditional cheminformatics tools,
predictive modelling platforms, quantitative structure–activity relationship (QSAR) models...
whether for training, development, testing, benchmarking, or any other purpose whatsoever," and
§3.2 prohibits redistribution. Haas *et al.* drew their acids from the Enamine catalogue but
published the resulting dataset CC BY; our chain of title runs through their publication. That
is the defensible position.

---

## 2. Where the labels come from, mechanically

`instructor/01_fetch_dft_labels.py` pages the MolSSI batch export:

```
/api/acids/molecules/data/export/batch?molecule_ids=Ac1,Ac2&data_type=dft&return_type=csv
```

Molecule ids are `Ac1` … `Ac8528`, contiguous. Responses are cached per 100-molecule chunk under
`data/api_cache/`, so a re-run costs nothing and an interrupted run resumes.

**Three things that will bite anyone who touches this code**, all verified against the live API:

1. **`data_type=dft`, not `dft_data`** — even though `/molecules/data_types` reports
   `{"available_types":["dft_data"]}`. The wrong value returns an empty body, not an error.
2. **The CSV is suffix-major.** `molecule_id, smiles`, then all 55 `_min` columns, then all 55
   `_max`, then `_boltz`, `_low_e`, `_boltz_stdev`. 277 columns. It is *not* property-major.
   `descriptor_spec.API_COLUMN_ORDER` reproduces it exactly, and
   `tests/test_logic.py` asserts a byte-for-byte match against a captured header.
3. **`min` and `max` occur inside base names.** The hemisphere descriptors are called
   `%Vbur_C1_min_hemisphere_3Å` and `%Vbur_C1_max_hemisphere_5Å`, so
   `%Vbur_C1_min_hemisphere_3Å_min` is a real column. Any regex or `str.replace("_min","")`
   corrupts twenty of them. Parsing goes through `descriptor_spec.split_target()`, which peels
   exactly one suffix, longest first. There is a test that fails if a naive strip *would have*
   worked, so the trap can never be quietly optimised away.

There is also a naming inconsistency upstream that we reproduce rather than tidy, because the
column name is the join key: the plain radius scan writes `3.0Å` (one decimal, always) while the
hemispheres write `3Å` (no `.0`). The Ångström sign is U+00C5, not U+212B.

`--verify-header` re-checks the upstream schema against the spec and exits non-zero on a
mismatch. `run_all.sh` calls it first, so an upstream change surfaces as a clear error rather
than silently shifted columns.

Offline fallback: `--xlsx ~/Downloads/Acid_Library.xlsx` (113 MB, from the FigShare deposit).
The script sniffs the workbook's sheets for the one carrying the target columns. Conformer-level
properties exist *only* in that workbook; the API serves molecule-level aggregates plus
per-conformer XYZ geometries, which is all this tutorial needs.

---

## 3. The label: 39 base properties × 4 aggregations = 156 targets

The published set is 55 bases × 5 aggregations = 275. We make two changes, both in
`descriptor_spec.py` and both reversible from that one file.

### Change 1 — drop `_boltz_stdev` (5 aggregations → 4)

Scored aggregations are the four that say *where* a descriptor sits:

| suffix | meaning |
|---|---|
| `_min` | minimum over the conformer ensemble |
| `_max` | maximum over the ensemble |
| `_low_e` | value at the lowest-energy conformer |
| `_boltz` | Boltzmann-weighted average, 298.15 K, quasi-harmonic Gibbs, 5 kcal/mol window |

`_boltz_stdev` still ships to students in the free dev set as **39 unscored extra columns**. It
is the authors' own measure of conformational spread, and section (a) uses it for the
"how conformational is this descriptor?" analysis — a better number than any proxy we could
compute.

### Change 2 — trim the buried-volume radius scan (55 bases → 39)

The published set has %Vbur at nine radii on C1, nine on C4, and five each for the C1 max and
min hemispheres: **28 of 55 bases**. More than half the score would have been one smooth,
highly redundant radius scan, and a team could have won by fitting it alone. We keep three
radii per series (3, 4, 5 Å) → 12 buried-volume bases.

Buried volume is still the largest family at **12/39 = 31% of the targets**, which is honest:
it is what the Sigman workflow measures most of. `score_submissions.py --family-balanced`
averages the eight families first, if you want to rank without that weighting; both numbers are
always printed.

### The 39 base properties

Atom labels are the paper's own, for the (R)₃C4–C1O2O3H5 group: **C1** carboxyl carbon,
**O2** carbonyl oxygen, **O3** hydroxyl oxygen, **H5** acidic hydrogen, **C4** α-carbon.

| family | n | members |
|---|---|---|
| `vbur` | 12 | `%Vbur_C1_{3.0,4.0,5.0}Å`, `%Vbur_C4_{3.0,4.0,5.0}Å`, `%Vbur_C1_{max,min}_hemisphere_{3,4,5}Å` |
| `charge` | 5 | `NBO_charge_{C1,C4,H5,O2,O3}` — NBO natural population analysis |
| `fmo` | 5 | `HOMO`, `LUMO`, `η` (hardness), `μ` (chemical potential), `ω` (electrophilicity index) |
| `spectroscopic` | 4 | `NMR_shift_{C1,C4,H5}`, `IR_freq_C1_O2` (harmonic C=O stretch) |
| `sterimol` | 3 | `Sterimol_{B1,B5,L}_C1_C4(Å)_morfeus` — along C1→C4, i.e. the sterics of R seen from the acid carbon |
| `sasa` | 3 | `SASA_sphericity`, `SASA_surface_area(Å²)`, `SASA_volume(Å³)` |
| `geometry` | 3 | `distance_O3_H5(Å)`, `dihedral_C4_C1_O3_H5(°)`, `dihedral_O2_C1_O3_H5(°)` |
| `electrostatic` | 4 | `dipole(Debye)`, `polar_iso`, `polar_aniso`, `volume(Bohr_radius³/mol)` |

**Not in the published library**, so not available to this tutorial: Hirshfeld or ChelpG
charges, a dispersion descriptor (P_int), pKa, C=O or C–O bond lengths, buried Sterimol, and
pyramidalisation (amines only).

**One upstream mislabel we record but do not silently propagate:** `polar_iso` and `polar_aniso`
are labelled `(Debye)` in the acids database but are polarisabilities in atomic units.
`UNIT_OF_BASE` says so; the column name stays verbatim because it is the join key.

> The authoritative, machine-readable list — names, order, family, units, ASCII aliases — lives
> in `instructor/descriptor_spec.py`. `02_make_splits.py` serialises it into
> `data/student/targets.json`, and the notebooks, the scorer and the validator all read that.
> Change the spec in one place; everything follows.

### A note on the unicode

Target names contain `%`, `Å`, `²`, `³`, `°`, `η`, `μ`, `ω`, parentheses and `/`. We keep them
**verbatim** so every target is traceable to the paper and the API with no mapping table to
maintain. All CSV and JSON I/O is explicitly UTF-8. `bundle.ascii(target)` gives an ASCII-safe
alias for filenames and plot labels; the aliases are asserted collision-free.

---

## 4. Splits and budget

| split | n | given to students | purpose |
|---|---|---|---|
| `pool` | ~6,528 | SMILES + metadata. Labels behind the oracle. | the thing they buy from |
| `dev` | 1,000 | SMILES, all 156 labels, and the 39 `_boltz_stdev` extras | free validation set |
| `test_hidden` | 1,000 | nothing at all | the leaderboard |

Bemis–Murcko scaffold split, asserted disjoint in code. Two choices worth defending to the room:

- **`dev` is free and labelled.** Real practitioners always have *some* free data. Withholding
  it would make the exercise about guessing hyperparameters rather than about acquisition, and
  it removes the excuse "my model was bad, not my acquisition function." Sections (b) and (c)
  spend **zero budget** as a direct consequence, which is itself the lesson: rehearse on free
  data before you queue DFT jobs.
- **`test_hidden` is scaffold-disjoint from `pool`.** It contains skeletons no acquisition
  strategy can buy at any budget. This is why a pure representativeness strategy underperforms:
  it keeps buying near the pool's mode.

```
seed:      100 molecules   (student chooses HOW — task (c))
rounds:    10
batch:     50 per round
total:     600 labels  ≈ 9% of the pool  ≈ 70,000 CPU-hours of DFT
```

Enforced by `student/al_toolkit.py::Oracle`, which refuses to exceed 600 unique labels, writes
an append-only `al_log.jsonl`, and is the only object that can read the sealed label file.

Timing on Colab CPU: one Chemprop fit on ≤600 molecules × 156 tasks ≈ 25–50 s at 40 epochs, so a
10-round loop is ~6–10 min. Students can afford two or three complete strategies plus the random
baseline. **The random baseline is mandatory** — section (d) runs it first.

---

## 5. Scoring

Two dimensionless numbers, each averaged over the 156 targets.

**Accuracy — mean scaled MAE**

```
sMAE = (1/T) Σ_t  MAE_t / σ_t          σ_t = std of task t over the hidden test set
```

`sMAE = 1.0` means "no better than predicting the mean"; predicting the mean of a normal
actually scores ≈ 0.8, which the tests assert. Dividing by each task's own spread is what stops
`volume(Bohr_radius³/mol)` (~2,000) from drowning `NBO_charge_H5` (~0.5 e).

**Calibration — mean ENCE**

Students emit a predictive standard deviation per molecule per target. Per task, bin the test
molecules into 10 equal-count bins by predicted σ, then

```
ENCE_t = (1/B) Σ_b  |RMSE_b − RMV_b| / RMV_b
```

(Levi *et al.*, *Sensors* **2022**, *22*, 5540. `RMV_b` = root-mean predicted variance in bin b.)
`0` is perfect. A constant σ scores badly by construction, which is the point — this cannot be
faked with a global error bar. It is also the same quantity an uncertainty-based acquisition
function depends on, so a calibrated model and a good acquisition strategy are one skill.

**Leaderboard**

```
combined = mean_sMAE + mean_ENCE          (lower is better)
```

There are **two** boards. During the session students self-report this quantity computed on the
public **dev** set, to a Sheets-backed live board on the tutorial page. Afterwards you compute it
on the hidden **test** set from their checkpoints. Teams move between the two; that movement is
the closing lesson, and `leaderboard/README.md` says how to frame it.

Reported alongside: per-family sMAE and ENCE, Spearman(σ, |error|), labels used, AULC from the
submitted learning curve, and `MAE_over_published`.

### The published reference, and its caveat

`published_benchmark.csv` carries the paper's own 3D GNN (DimeNet++) test MAEs for 20 of our
targets — the Sterimol trio, the C=O stretch and the dipole, each in all four aggregations.

**Say this out loud when you show the comparison:** their numbers come from a **random** split
with **7,290 training molecules**; this test set is **scaffold-disjoint** and the budget is
**600**. Their numbers are a ceiling, not a like-for-like target. A ratio of 2× is a good
result.

One genuinely useful pattern in their table, worth a slide: **`_low_e` is consistently the
hardest aggregation.** Sterimol L scores MAE 0.196 Å / R² 0.969 for `_min` but 0.800 Å / 0.631
for `_low_e`. The paper attributes it to conformer-sampling noise — "this noise may especially
impact the descriptors of the lowest-energy conformers." That is an aleatoric term in a dataset
with no experimental error at all, and it is exactly why §6's epistemic/aleatoric distinction is
not academic here.

---

## 6. What the students actually do

### (a) Look at the data
Prints the oracle's cost per label first. Then pool composition (MW, scaffolds, acid subclass),
a grid of twelve structures, and the descriptor table with **units**, because the units are the
setup for section (d)'s trap. The centrepiece: conformational spread per descriptor, using the
authors' own `_boltz_stdev`. The dihedrals come out on top — `dihedral_O2_C1_O3_H5` is the
syn/anti flip of the acid proton, so its `_min` and `_max` are barely the same quantity — and
the NBO charges at the bottom. Then a correlation map showing the buried-volume block is one
thing measured three times, an optional cell that pulls real DFT conformer geometries from the
API, and a PCA showing the scaffold gap.

### (b) Choose a GNN
Chemprop v2 Python API on the free dev set. A small architecture sweep, then the choice that
matters — **the predictor head**, because it determines what uncertainty exists at all:

| head | uncertainty available | cost |
|---|---|---|
| `RegressionFFN` | none — σ is all zeros | 1× |
| `MveFFN` | aleatoric only | 1× |
| `EvidentialFFN` | epistemic + aleatoric | 1× |
| ensemble of `RegressionFFN` × 5 | epistemic (disagreement) | 5× |
| ensemble of `MveFFN` × 3 | epistemic + aleatoric | 3× |

The trap they should walk into: MVE alone gives *aleatoric* uncertainty, the wrong thing to
acquire on. Here the aleatoric term is conformer-ensemble noise rather than measurement noise —
real, and irreducible at this budget.

### (c) Initialisation
Four seed methods on 100 molecules: random, MaxMin on Morgan fingerprints, k-means medoids,
scaffold-balanced. Measured three ways before any training — mean pairwise Tanimoto, distinct
scaffolds, and **coverage distance** (mean distance from every pool molecule to its nearest seed
molecule, the quantity core-set theory is about). Then §3 reruns `random` with five seeds and
prints whether the method gap exceeds seed noise. That check is the notebook's real payload.

### (d) Acquisition
The zoo, all pre-implemented with one signature, plus a stub:

| name | family |
|---|---|
| `random` | baseline (mandatory) |
| `max_variance` | uncertainty, top-k, **raw** — the trap |
| `max_variance_scaled` | uncertainty, per-task normalised |
| `max_epistemic` | epistemic only |
| `bald_ensemble` | Gaussian mutual information |
| `coreset_greedy` | pure representativeness, k-centre greedy on Chemprop embeddings |
| `badge` | uncertainty-scaled embedding + k-means++ |
| `batch_diverse_topk` | top-4k by σ, then MaxMin — the cheap BatchBALD surrogate |
| `qbc_disagreement` | query by committee |
| `uncertainty_times_novelty` | closest to the JACS 2025 acquisition function |
| `your_own` | stub with the signature and a docstring full of ideas |

**The spine.** Run `random`, then `max_variance`. With 156 targets in mixed units, a raw sum of
standard deviations is — to three significant figures — a sum over `volume` (~2,000 Bohr³) and
`IR_freq` (~1,800 cm⁻¹). The acquisition function spends the whole budget improving two
descriptors out of thirty-nine, and the score never tells you, because the metric scales each
task. It should land at or below random. `max_variance_scaled` fixes it in one line. The
per-family bar chart is the diagnosis, not just the symptom.

Batch redundancy comes free: mean pairwise Tanimoto *within* each acquired batch, top-k vs BADGE.
Forty near-identical fluorobenzoic acids at 117 CPU-hours each is a concrete waste, not an
abstract one.

### (e) Package and submit

```
submission_<team>/
  manifest.json      strategy, seed method, AF, budget used, target order
  models/*.pt        Chemprop checkpoint(s) via chemprop.models.save_model
  predict.py         PROVIDED, UNMODIFIED — SHA-256 checked
  al_log.jsonl       append-only oracle log
  learning_curve.csv dev sMAE + ENCE after every round (→ AULC, no extra upload)
```

`validate_submission.py` is the self-test. It fails loudly on: a modified `predict.py`, an
unloadable checkpoint, wrong output shape or **column order**, NaNs, all-zero σ, budget > 600,
duplicate oracle queries, `labels_used` disagreeing with the log, and dev molecules in the
purchase log. Then it actually runs `predict.py` on 50 public molecules. Nothing gets uploaded
before it prints `READY TO SUBMIT`.

The column-order check earns its keep here: `sorted(targets)` is a natural thing to type and it
silently permutes the buried-volume columns, because their names contain `min` and `max`. The
test suite covers both `reversed()` and `sorted()`.

Section (e) also POSTs the team's dev score to the live board (one cell, everything read off the
`LoopResult` so only the team name is typed), and ends by comparing their dev MAEs against
`published_benchmark.csv` with the random-vs-scaffold-split caveat printed alongside.

Instructor side: `leaderboard/score_submissions.py` walks the Drive-synced folder, runs each
`predict.py` in a subprocess against `test_hidden`, and writes `leaderboard.md` + `.csv`.
`--audit` evaluates each model on 500 pool molecules *absent* from that team's log; if their error
there is indistinguishable from their error on their own logged training molecules, it flags for a
conversation. That is a real statistical check, not a bluff.

---

## 7. Instructor setup

```
instructor/
  descriptor_spec.py       the 39 x 4 spec, the API layout, the parsing helpers
  obfuscate.py             label sealing (a speed bump, not a lock)
  01_fetch_dft_labels.py   MolSSI API -> data/labels_all.csv          ~15 min
  02_make_splits.py        scaffold split, seal, student bundle        ~1 min
  run_all.sh               driver
leaderboard/
  score_submissions.py     the authoritative board + overtraining audit
  apps_script.gs           the live self-report board (see leaderboard/SETUP.md)
  submit_payload.py        what the notebook POSTs
```

One environment, no GPU, no quantum chemistry:

```bash
python -m venv ~/envs/al && source ~/envs/al/bin/activate
pip install chemprop==2.3.1 rdkit scikit-learn matplotlib pandas

cd instructor
./run_all.sh smoke     # 300 molecules end-to-end, ~2 min
./run_all.sh full      # all 8,528, ~15 min, almost all of it API paging
```

Then commit `data/student/` so the notebook can fetch it from raw.githubusercontent.com at
runtime, and set up the live board — `leaderboard/SETUP.md` has the click-by-click.

`run_all.sh` calls `--verify-header` first, so an upstream schema change fails fast. It ends by
running `tests/test_logic.py` (96 checks, numpy + pandas only).

**Never commit `data/instructor/`** — it holds the hidden test labels and `splits.json`. The
folder's `.gitignore` excludes it; check `git status` before pushing.

### Two boards, on purpose

Students self-report their **dev** score to a live Sheets-backed board during the session, because
they cannot compute their own hidden-test score. You publish the authoritative board afterwards
from `leaderboard/score_submissions.py`. Teams reorder between the two, and that reordering is the
closing lesson — see `leaderboard/README.md`.

**Versions verified 2026-08-18:** `chemprop 2.3.1` (Python ≥3.11, torch ≥2.1) · `rdkit` ·
`scikit-learn`. Students install only these; Colab's setup cell handles it.

---

## 8. Session timing (90 min)

| min | what | notes |
|---|---|---|
| 0–5 | framing: the oracle cost 117 CPU-hours per label, the budget is 600, the test set is hidden | show the paper's Fig. 1 and the cost cell |
| 5–20 | **(a)** *Look at the data*, as a group | slow down on the conformational-spread chart and on the units table |
| 20–35 | **(b)** *Choose a GNN* | they must commit to a head; take a show of hands |
| 35–45 | **(c)** *Choose an initialisation* | cheap — seed selection needs no training |
| 45–75 | **(d)** *Acquisition* — the loop, in teams | `random` and `max_variance` first, then their own |
| 75–85 | **(e)** *Package and submit*, validate, upload | the validator must go green before they leave |
| 85–90 | the live dev board, plus the comparison against the published GNN | the real board comes after, from `leaderboard/score_submissions.py` |

Sections (a)–(c) are mostly pre-written with short "your turn" cells; only (d) is open-ended. If the
room is slow, 03 collapses to a five-minute demo.

---

## 9. References

1. Haas, B. C.; Hardy, M. A.; Sowndarya S. V., S.; Adams, K.; Coley, C. W.; Paton, R. S.; Sigman, M. S. *Digital Discovery* **2025**, *4*, 222–233. DOI [10.1039/D4DD00284A](https://doi.org/10.1039/D4DD00284A). Data: FigShare [10.6084/m9.figshare.25213742](https://doi.org/10.6084/m9.figshare.25213742). CC BY 4.0. — **the labels, the molecule pool, and the benchmark.**
2. MolSSI Descriptor Libraries, <https://descriptor-libraries.molssi.org/> · source: <https://github.com/Descriptor-Libraries/descriptor-libraries-framework>. — the API we fetch from.
3. Heid, E. *et al.* **Chemprop: A Machine Learning Package for Chemical Property Prediction.** *J. Chem. Inf. Model.* **2024**, *64*, 9–17. DOI [10.1021/acs.jcim.3c01250](https://doi.org/10.1021/acs.jcim.3c01250). v2 software paper: DOI [10.1021/acs.jcim.5c02332](https://doi.org/10.1021/acs.jcim.5c02332).
4. Smith, J. S.; Nebgen, B.; Lubbers, N.; Isayev, O.; Roitberg, A. E. **"Less is more: sampling chemical space with active learning."** *J. Chem. Phys.* **2018**, *148*, 241733. DOI [10.1063/1.5023802](https://doi.org/10.1063/1.5023802). — the lecture's §8 anchor; same shape of problem, where the model *is* the deliverable.
5. Schleinitz, J.; Carretero-Cerdán, A.; Gurajapu, A. *et al.* *J. Am. Chem. Soc.* **2025**, *147*, 7476–7484. DOI [10.1021/jacs.4c15902](https://doi.org/10.1021/jacs.4c15902). — Lecture 13's running example; acquisition weighted by predicted reactivity × uncertainty.
6. Sener, O.; Savarese, S. **"Active learning for CNNs: a core-set approach."** ICLR **2018**. arXiv [1708.00489](https://arxiv.org/abs/1708.00489). — `coreset_greedy`.
7. Ash, J. T.; Zhang, C.; Krishnamurthy, A.; Langford, J.; Agarwal, A. **BADGE.** ICLR **2020**. arXiv [1906.03671](https://arxiv.org/abs/1906.03671). — `badge`.
8. Kirsch, A.; van Amersfoort, J.; Gal, Y. **BatchBALD.** NeurIPS **2019**. arXiv [1906.08158](https://arxiv.org/abs/1906.08158). — motivation for `batch_diverse_topk`.
9. Levi, D.; Gispan, L.; Giladi, N.; Fetaya, E. **"Evaluating and calibrating uncertainty prediction in regression tasks."** *Sensors* **2022**, *22*, 5540. DOI [10.3390/s22155540](https://doi.org/10.3390/s22155540). — the ENCE definition the scorer uses.
10. Underlying descriptor definitions, as cited by the source library: Verloop Sterimol; buried volume from Falivene *et al.* SambVca 2, *Organometallics* **2016**, *35*, 2286; NBO natural population analysis; ᴍᴏʀғᴇᴜs (<https://digital-chemistry-laboratory.github.io/morfeus/>) for the Sterimol and %Vbur implementations used by the authors.
11. Ebejer, J.-P.; Morris, G. M.; Deane, C. M. *J. Chem. Inf. Model.* **2012**, *52*, 1146. — the rotatable-bond conformer heuristic, for context on ensemble sizes.
