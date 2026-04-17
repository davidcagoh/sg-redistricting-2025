# Design & Methodology Decisions

Part of the [project wiki](INDEX.md). See also: [Methodology](methodology.md) · [Open Questions](open-questions.md) · [Literature](literature/INDEX.md) · [Seeding](seeding.md)

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
