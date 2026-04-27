# Design & Methodology Decisions

Part of the [project wiki](INDEX.md). See also: [Methodology](methodology.md) · [Open Questions](open-questions.md) · [Literature](literature/INDEX.md) · [Seeding](seeding.md)

---

## 2026-04-26 — Paper 2 GRC analysis: post-process paper 1 ensemble (Option A) {#grc-option-a}

**Decision:** Use the existing paper 1 equal-population `seed_001` ensemble (9,000 steps) as the base for GRC minority-capture analysis. For each step, randomly assign seat types (15×SMC, 8×GRC4, 10×GRC5) across the 33 districts and compute minority capture, building a null distribution. Compare to the actual 2025 GRC configuration.

**Why:** The variable-seat-count ReCom approach (paper 2 GRC seeder) was structurally infeasible for Singapore's subzone graph. 15 subzones have populations exceeding the SMC target × 1.2 (largest = 130,980; SMC target ≈ 41,527 × 1.2 = 49,832), meaning those subzones cannot physically be placed in an SMC-sized district. Only 1/100 BFS seeding attempts passed even a 50% population tolerance. Multiple seeding strategies were tried and failed: stratified BFS, absolute-deficit-priority BFS, sequential BFS, and unit-merge with k=97 intermediate units (unit max deviation 214%, too unequal to merge cleanly). The fundamental constraint is Singapore's subzone granularity — some subzones are 3× the SMC target population, making variable-target contiguous partitioning impossible within practical tolerances.

**What was kept in the codebase:** `src/analysis/grc/seed_partition.py` retains the modular additions made during exploration: (a) empty-district bug fix in `_grc_swap_pass`, (b) `pop_tolerance` override parameter in `validate_grc_partition`, (c) `_unit_merge_grc_seed` as a documented modular function alongside the original `_bfs_grc_seed`. These remain as reference and do not affect paper 2's analysis path.

**Implication:** Paper 2 GRC analysis answers: "Given equal-population district boundaries, does the actual seat-type assignment (SMC vs GRC4 vs GRC5) concentrate or dilute minority populations compared to random assignment?" This is methodologically clean — it isolates the seat-type allocation decision from the boundary-drawing decision.

---

## 2026-04-17 — filter_for_mcmc excludes all non-mainland components by default

**Decision:** Changed `filter_for_mcmc` default from `min_pop=1` to `min_pop=float("inf")`, so all non-mainland connected components are excluded regardless of population.

**Why:** Node 317 (pop=50, no adjacency edges) caused BFS seeding to fail with non-contiguous districts. It is a single isolated subzone with no graph neighbours, meaning no spanning-tree cut can include it in any contiguous district. Its population (50 of 4,044,340 total = 0.001%) is negligible. The old `min_pop=1` threshold was an approximation that accidentally allowed isolated populated nodes through. The MCMC framework requires the graph to be connected; any non-mainland component is incompatible with contiguity requirements.

**Implication:** The MCMC graph now has 327 nodes (was 328). Callers wanting to retain non-mainland populated components (e.g. for non-MCMC analysis) must pass `min_pop` explicitly.

---

## 2026-04-17 — allow_pair_reselection via bipartition_tree partial, not MarkovChain

**Decision:** ISSUE-4 fix passes `functools.partial(bipartition_tree, allow_pair_reselection=True, max_attempts=1000)` as `method` kwarg to `recom`, rather than setting `allow_pair_reselection` on `MarkovChain` (which doesn't expose this parameter in GerryChain 0.3.2).

**Why:** The GerryChain 0.3.2 `MarkovChain.__init__` does not accept `allow_pair_reselection`. The flag lives on `bipartition_tree`. Setting `max_attempts=1000` (equal to `warn_attempts`) is critical: without it, each failing district pair exhausts 100 000 spanning-tree attempts before triggering reselection, yielding ~20 s/step. With `max_attempts=1000`, failing pairs give up immediately and trigger reselection, yielding ~0.15 s/step (130× speedup).

**Implication:** If GerryChain is upgraded to a version that exposes `allow_pair_reselection` on `MarkovChain`, the `recom.py` approach should be revisited — but the current approach is functionally correct for 0.3.2.

---

## 2026-04-17 — BFS seeder chosen over actual-plan seed

**Decision:** Use a custom BFS growth seeder (Fix A) as fallback when `recursive_tree_part` fails, rather than using the 2020 actual plan as seed (Fix B).

**Why:** Fix B is methodologically circular — the [NC literature](literature/INDEX.md#herschlag-quantifying-gerrymandering-in-nc-2018) explicitly runs chains from independent random seeds to verify mixing and avoid biasing the ensemble toward the plan being tested. Fix A produces a neutral random starting state that chain mixing erases. Full reasoning: [Seeding](seeding.md#fix-a-vs-fix-b-literature-basis).

**On k=33 vs k=31:** The 2020/2025 actual plans have 31 districts; the ensemble uses k=33. Acknowledged as imperfect (see [Open Questions](open-questions.md#grc-multi-member-structure)); not changed here to avoid conflating two distinct methodological questions.

---

## 2026-04-13 — HDB building-to-property join strategy

**Why:** `HDBExistingBuilding.geojson` stores `ST_COD` (a street code like `CLA09K`), not a human-readable street name. The original design assumed a `blk_no + street` compound join to `HDBPropertyInformation.csv`, achieving 0% match rate on real data. Since `blk_no` has 3,407 unique values matching across both sources, and most blocks belong to a single town, a `blk_no`-only join with modal aggregation of `bldg_contract_town` is used as fallback.

**Implication:** A small minority of blocks straddling town boundaries will be assigned the majority town, introducing minor noise in the splitting metric. Acceptable given the coarseness of the subzone-level analysis.

---

## 2026-04-12 — Analysis direction: ensemble + community splitting {#analysis-direction}

### Decision

Adapt the Herschlag/Mattingly MCMC ensemble method (ReCom / Merge-Split) to Singapore, with **HDB town splitting as primary metric** and **population deviation as secondary metric**. Partisan seat analysis is out of scope.

### Rationale

**What the ensemble method requires:**
1. Atomic geographic units with population → URA subzones (~320) with Census 2020 data ✓
2. Adjacency graph from subzone GeoJSON → computable ✓
3. A target partition count → 33 constituencies (2025) ✓
4. A "community of interest" to measure splitting → HDB towns

**Why HDB towns, not polling districts:** {#why-hdb-towns}
HDB towns are planned residential communities with shared infrastructure, schools, and hawker centres — the clearest Singapore analogue to US counties (which the [NC paper](literature/INDEX.md#herschlag-quantifying-gerrymandering-in-nc-2018) uses as the primary community-preservation metric). Polling district polygons exist only as PDFs requiring manual digitization. See [Open Questions](open-questions.md).

**Why not partisan analysis:**
Singapore does not publish precinct- or polling-district-level vote returns. Only constituency-level results are public, which are too coarse to detect redistricting effects. The [NC partisan analysis](literature/INDEX.md#herschlag-quantifying-gerrymandering-in-nc-2018) (overlaying historical elections on ensemble plans) has no Singapore data equivalent. See [Methodology](methodology.md#what-we-cannot-do-partisan-analysis).

**Why not GRC ethnic quota analysis (yet):**
The ethnic composition constraint (each GRC must field ≥1 minority candidate) is real but secondary to the geometric/population question. Subzone-level ethnic data exists in Census 2020 and could be added as a future metric.

### The GRC structure problem {#on-k33-vs-k31}

Singapore GRCs hold 3–5 seats; SMCs hold 1 seat. Two options:
- **(Option A — chosen)** Treat all constituencies as equal-population units in a k=33 partition. Ignores seat-count variation but produces a mathematically clean ensemble.
- **(Option B — future)** Fix a seat-count vector matching the actual plan's GRC/SMC mix and compute per-district target populations. Requires deciding whether the seat-count vector itself is fixed or variable — a policy question. See [Open Questions](open-questions.md#grc-multi-member-structure).

### Literature basis
- [Herschlag et al., "Quantifying Gerrymandering in North Carolina" (2018)](literature/INDEX.md#herschlag-quantifying-gerrymandering-in-nc-2018)
- [Autry et al., "Multi-Scale Merge-Split MCMC for Redistricting" (2020)](literature/INDEX.md#autry-et-al-merge-split-2020)
- [Mattingly, "Ensembles and Outliers" (2018)](literature/INDEX.md#mattingly-ensembles-and-outliers-2018)
- ["The Ensemble Method and its Use for Outlier Analysis in Redistricting"](literature/INDEX.md#the-ensemble-method-and-its-use-for-outlier-analysis)
