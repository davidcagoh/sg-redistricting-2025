# Literature — Annotated Bibliography

Part of the [project wiki](../INDEX.md). See also: [Methodology](../methodology.md) · [Seeding](../seeding.md) · [Decisions](../decisions.md)

---

## Core ensemble / MCMC papers

### Mattingly, "Ensembles and Outliers" (2018)
**File:** `Ensembles and Outliers.txt` (blog post, Duke Math)  
**Key claims:**
- The ensemble framework separates (1) defining the target distribution, (2) generating samples (MCMC algorithm), and (3) using the ensemble for inference. Each can be critiqued independently.
- The seed is an initializer, not a draw from the target distribution. Any valid seed is equivalent after chain mixing.
- Metropolis-Hastings/ReCom cleanly encodes assumptions in the target distribution, unlike ad-hoc map-generation methods.

**Relevance to this project:** Foundational motivation for the Singapore ensemble. Justifies Fix A (BFS seeder) over Fix B (actual plan as seed) — see [Seeding](../seeding.md#fix-a-vs-fix-b-literature-basis).

---

### Herschlag, Kuo, Lo, Otterness, Schutzman, Soskin, Mattingly, "Quantifying Gerrymandering in North Carolina" (2018)
**File:** `2018 Quantifying Gerrymandering in North Carolina.pdf`  
**Key claims:**
- Applied ensemble to NC 2016 US Congressional and NC House/Senate maps.
- Atomic units: ~2,700 census precincts (all with pop > 0).
- Multiple independent chains from different random seeds verify mixing — not from the actual plan being tested.
- The actual NC 2016 plan ranked in the 99th+ percentile on partisan metrics across ~24,000 ensemble plans.
- Polsby-Popper and county-splitting used as secondary metrics alongside partisan outcomes.

**Relevance:** NC precincts differ from Singapore subzones in that all precincts have population > 0. Singapore's ~36% zero-population subzones is the root cause of the seeding failure. See [Issues](../issues.md#issue-1).

---

### Autry, Carter, Herschlag, Hunter, Mattingly, "Multi-Scale Merge-Split Markov Chain Monte Carlo for Redistricting" (2020)
**File:** `2020 MULTI-SCALE MERGE-SPLIT MARKOV CHAIN MONTE CARLO FOR REDISTRICTING.pdf`  
**Key claims:**
- Introduces Forest-Recom (Merge-Split) as a more mixing-efficient alternative to single-edge ReCom.
- Proves that any valid initial partition works because the chain is ergodic over all valid k-partitions.
- Used on NC county-level and precinct-level graphs.

**Relevance:** Ergodicity proof supports Fix A — any valid seed (including BFS) leads to the same stationary distribution. Merge-Split may be worth switching to if GerryChain ReCom exhibits slow mixing on Singapore's zero-pop-heavy graph.

---

### "Redistricting and the Will of the People" (2014)
**File:** `2014 REDISTRICTING AND THE WILL OF THE PEOPLE.pdf`  
**Key claims:** Early Mattingly group work advocating probability distributions over map space as the principled alternative to one-map comparisons or efficiency gap metrics.

**Relevance:** Historical foundation for the ensemble approach used here.

---

### "The Ensemble Method and its Use for Outlier Analysis in Redistricting"
**File:** `Ensemble Method and its use for Outlier Analysis in Redistricting.pdf`  
**Key claims:** Extended treatment of how to conduct outlier analysis using an ensemble — selecting metrics, interpreting percentile ranks, addressing the "many metrics" multiple-comparison problem.

**Relevance:** Guides our choice of metrics: max_abs_pop_dev, towns_split, pln_area_splits, mean_pp. See [Decisions](../decisions.md#analysis-direction).

---

## Contextual / background

### "How Math Has Changed the Shape of Gerrymandering" (Quanta Magazine)
**File:** `How Math Has Changed the Shape of Gerrymandering | Quanta Magazine.pdf`  
Accessible explainer of the ensemble approach for general audience. No novel methods.

### NC General Assembly County Clusterings from the 2020 Census (2020)
**File:** `2020 NC General Assembly County Clusterings from the 2020 Census.pdf`  
NC-specific legislative application of county-clustering methods. Tangential to Singapore analysis.

### QGIS Introduction
**File:** `QGIS-3.44-GentleGISIntroduction-en.pdf`  
GIS tooling reference for QGIS work on the Singapore geospatial layers.

---

## Links (external)
See [`links.md`](links.md) for external URLs including the Singapore electoral data source (data.gov.sg/ELD), the Tong Hui Kang GE analysis, and the Rice Gerrymandering web tool.
