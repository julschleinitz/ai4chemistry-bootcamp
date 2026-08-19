# Papers and datasets — Tutorial 13

Everything this tutorial uses, where it came from, and what the licence permits.

---

## The dataset (labels, molecule pool, and benchmark)

**Haas, B. C.; Hardy, M. A.; Sowndarya S. V., S.; Adams, K.; Coley, C. W.; Paton, R. S.;
Sigman, M. S.** "Rapid prediction of conformationally-dependent DFT-level descriptors using graph
neural networks for carboxylic acids and alkyl amines." *Digital Discovery* **2025**, *4*,
222–233. DOI [10.1039/D4DD00284A](https://doi.org/10.1039/D4DD00284A).

- **Data:** FigShare [10.6084/m9.figshare.25213742](https://doi.org/10.6084/m9.figshare.25213742)
  (v3), `Acid_Library.xlsx`, 113 MB.
- **Served by:** MolSSI Descriptor Libraries, <https://descriptor-libraries.molssi.org/api/acids/>
  (open REST API, no authentication). Framework source:
  <https://github.com/Descriptor-Libraries/descriptor-libraries-framework>.
- **Licence: CC BY 4.0.** Redistribution and modification permitted with attribution. Attribution
  appears in `instructor/01_fetch_dft_labels.py`, `data/student/targets.json`,
  `data/student/README.md`, and sections (a) and (e) of the notebook.
- **Preprint:** ChemRxiv [10.26434/chemrxiv-2024-m5bpn](https://doi.org/10.26434/chemrxiv-2024-m5bpn).
- **Authors' code:** <https://github.com/nsf-c-cas/AcidAmine_Descriptor_Predict>;
  descriptor collection via <https://github.com/SigmanGroup/GetProperties>.

### Scope and provenance of the numbers

| | |
|---|---|
| molecules | 8,528 carboxylic acids |
| conformers | 71,324 (~8.4 per molecule) |
| published descriptors | 275 = 55 base properties × 5 aggregations |
| **used here** | **156 = 39 base properties × 4 aggregations** (see `PLAN.md` §3) |
| conformer search | Schrödinger Maestro, search + clustering |
| geometry optimisation | B3LYP-D3(BJ)/6-31G(d,p)-LANL2DZ(I, Sn, Se) |
| single-point energies | M06-2X/def2-TZVP-SDD(I, Sn, Se) |
| thermochemistry | GoodVibes, quasi-harmonic Gibbs |
| Boltzmann weighting | 298.15 K, 5 kcal/mol window |
| phase | gas |
| **reported cost** | **> 1,000,000 CPU hours** (~117 CPU-hours per molecule) |

The 600-label budget in this tutorial therefore corresponds to roughly **70,000 CPU-hours** of
quantum chemistry, which is the number section (a) prints before students spend anything.

### Their GNN, used as our reference line

`data/student/published_benchmark.csv` carries the authors' own 3D GNN (DimeNet++) test MAEs for
20 of our targets. **Not like-for-like:** their split is **random** with **7,290** training
molecules; ours is **scaffold-disjoint** with a 600-label budget. Treat their numbers as a ceiling.

Their split sizes, for the record: 2D GNNs 7301 / 480 / 476 (+149 external validation);
3D GNNs 7290 / 478 / 476 (+149). They modelled 21 base descriptors × 4 aggregations = 84 targets,
not all 55 bases.

---

## Why not Enamine directly

The acid list originates in Enamine's building-block catalogue, but **we do not source it from
Enamine**, and neither should any derivative of this tutorial.

Enamine Terms of Use §15.2 prohibits "using, processing, analyzing, modelling, or incorporating
any Enamine Data into any computational system, including but not limited to AI/ML Systems,
traditional cheminformatics tools, predictive modelling platforms, quantitative
structure–activity relationship (QSAR) models, structure-based drug design software, or any other
data processing or modelling systems — whether for training, development, testing, benchmarking,
or any other purpose whatsoever — unless explicitly authorized in writing by Enamine." §3.2
separately prohibits redistribution.

Haas *et al.* published their derived dataset under **CC BY 4.0**. Our chain of title runs through
their publication, not through Enamine.

### If you ever need a fresh in-stock list instead

Verified working, no login: the UCSF **Arthor** SMARTS server against the **Mcule In-Stock** index,

```
https://arthor.docking.org/dt/MMcule-In-Stock-25Q3-6.5M/search?query=<SMARTS>&type=SMA&start=0&length=1000
```

docking.org's Terms and Conditions state "you are free to share the results of a ZINC search or a
screen of molecules from ZINC". Cite ZINC-22: **Tingle, B. I. et al.** *J. Chem. Inf. Model.*
**2023**, *63*, 1166–1176. DOI [10.1021/acs.jcim.2c01253](https://doi.org/10.1021/acs.jcim.2c01253).
Mcule's own bulk downloads (<https://mcule.com/database/>) are free and unauthenticated, but their
Terms §2.9 restrict redistribution, so ship a fetch script rather than the derived file.

---

## Software

| package | version | licence | role |
|---|---|---|---|
| **Chemprop** | 2.3.1 | MIT | the D-MPNN students train |
| **RDKit** | current | BSD-3 | fingerprints, scaffolds, descriptors |
| scikit-learn | current | BSD-3 | PCA, k-means, k-means++ |

Chemprop: **Heid, E. et al.** *J. Chem. Inf. Model.* **2024**, *64*, 9–17.
DOI [10.1021/acs.jcim.3c01250](https://doi.org/10.1021/acs.jcim.3c01250). v2 software paper:
DOI [10.1021/acs.jcim.5c02332](https://doi.org/10.1021/acs.jcim.5c02332).

---

## Methods cited in the notebook

| idea | reference |
|---|---|
| "Less is more" — AL where the model *is* the deliverable | Smith, J. S.; Nebgen, B.; Lubbers, N.; Isayev, O.; Roitberg, A. E. *J. Chem. Phys.* **2018**, *148*, 241733. DOI [10.1063/1.5023802](https://doi.org/10.1063/1.5023802) |
| acquisition weighted by predicted reactivity × uncertainty | Schleinitz, J.; Carretero-Cerdán, A.; Gurajapu, A. *et al.* *J. Am. Chem. Soc.* **2025**, *147*, 7476–7484. DOI [10.1021/jacs.4c15902](https://doi.org/10.1021/jacs.4c15902) |
| core-set / k-centre greedy | Sener, O.; Savarese, S. ICLR **2018**. arXiv [1708.00489](https://arxiv.org/abs/1708.00489) |
| BADGE | Ash, J. T. *et al.* ICLR **2020**. arXiv [1906.03671](https://arxiv.org/abs/1906.03671) |
| BatchBALD | Kirsch, A.; van Amersfoort, J.; Gal, Y. NeurIPS **2019**. arXiv [1906.08158](https://arxiv.org/abs/1906.08158) |
| ENCE (the calibration metric) | Levi, D.; Gispan, L.; Giladi, N.; Fetaya, E. *Sensors* **2022**, *22*, 5540. DOI [10.3390/s22155540](https://doi.org/10.3390/s22155540) |
| Sterimol | Verloop, A. *Drug Design*, Vol. III, **1976** |
| buried volume (SambVca 2) | Falivene, L. *et al.* *Organometallics* **2016**, *35*, 2286 |
| ᴍᴏʀғᴇᴜs (used by the source library for Sterimol / %Vbur) | <https://digital-chemistry-laboratory.github.io/morfeus/> (MIT) |

---

## Required attribution, copy-paste

> Descriptor data from Haas, B. C.; Hardy, M. A.; Sowndarya S. V., S.; Adams, K.; Coley, C. W.;
> Paton, R. S.; Sigman, M. S. *Digital Discovery* **2025**, *4*, 222–233,
> DOI 10.1039/D4DD00284A, used under CC BY 4.0. Served via the MolSSI Descriptor Libraries API.
