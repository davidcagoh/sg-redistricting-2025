# Design & Methodology Decisions

## 2026-04-13 — HDB building-to-property join strategy

**Decision date:** 2026-04-13
**Why:** `HDBExistingBuilding.geojson` stores `ST_COD` (a street code like `CLA09K`), not a human-readable street name. The original design assumed a `blk_no + street` compound join to `HDBPropertyInformation.csv`, which achieves 0% match rate on real data. Since `blk_no` has 3407 unique values matching across both sources, and most blocks belong to a single town, a `blk_no`-only join with modal aggregation of `bldg_contract_town` is used as a fallback. The primary `blk_no + street` path is preserved for any caller that passes buildings with a `street` column (e.g. unit tests using synthetic data).
**Implication:** HDB town assignment uses modal town per block number when processing the real buildings file. A small minority of blocks that straddle town boundaries will be assigned the majority town, which may introduce minor noise in the splitting metric. This is acceptable given the coarseness of the subzone-level analysis.



## 2026-04-12 — Analysis direction: ensemble + community splitting

### Decision
Adapt the Herschlag/Mattingly MCMC ensemble method (specifically ReCom / Merge-Split) to Singapore, with **HDB town splitting as the primary metric** and **population deviation as a secondary metric**. Partisan seat analysis is out of scope.

### Rationale

**What the ensemble method requires:**
1. Atomic geographic units with population → URA subzones (~320) with Census 2020 data ✓
2. Adjacency graph derived from subzone GeoJSON → computable ✓
3. A target partition count → 33 constituencies (2025) ✓
4. A "community of interest" to measure splitting → HDB towns (natural Singapore analogue of US counties)

**Why HDB towns, not polling districts:**
- HDB towns are planned residential communities with shared infrastructure, schools, hawker centres. They are the clearest Singapore "communities of interest."
- We have HDB block data; town-level polygons may be derivable.
- Polling district polygons exist only as PDFs requiring digitization — too much work for this stage.

**Why not partisan analysis:**
- Singapore does not publish precinct-level or polling-district-level vote returns. The only public data is constituency-level results, which are too coarse to detect redistricting effects.
- The Herschlag/Mattingly partisan analysis (running historical elections through ensemble plans) has no Singapore data equivalent.

**Why not GRC ethnic quota analysis (yet):**
- The ethnic composition constraint (each GRC must field ≥1 minority candidate) is real but secondary to the geometric/population question.
- Subzone-level ethnic data exists in Census 2020 — could be added as a metric later.

### The GRC structure problem
Singapore GRCs hold 3–5 seats with correspondingly larger target populations; SMCs hold 1 seat. The neutral ensemble must decide whether to:
- **(Option A — chosen for now)** Treat all constituencies as equal-population units in a k=33 partition. This ignores seat-count variation but produces a mathematically clean ensemble where the actual plan's structural outlier-ness can be assessed on population and shape alone.
- **(Option B — future)** Fix a seat-count vector matching the actual plan's GRC/SMC mix and compute per-district target populations accordingly. This is harder and requires deciding whether the seat-count vector itself is fixed or variable — which is a policy question.

### Plan sequence
1. Compute subzone adjacency graph from `data/processed/subzone_with_population.geojson`
2. Implement ReCom sampler (GerryChain Python library or custom) on subzone graph
3. Generate ensemble of ~5,000–10,000 plans (k=33 partition)
4. Metrics per plan: population deviation (max, mean abs), HDB town splits, compactness (Polsby-Popper)
5. Locate actual 2020 and 2025 plans in the ensemble distributions
6. Descriptive 2020→2025 diff: which subzones reassigned, to where

### Literature basis
- Herschlag & Mattingly, "The Ensemble Method and its use for Outlier Analysis in Redistricting" (2021 draft)
- Autry, Carter, Herschlag, Hunter, Mattingly, "Multi-Scale Merge-Split Markov Chain Monte Carlo for Redistricting" (2020)
- Mattingly blog: "Ensembles and Outliers" (2018)
- Herschlag et al., "Quantifying Gerrymandering in North Carolina" (2018)
