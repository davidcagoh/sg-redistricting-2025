# Methodology — MCMC Ensemble for Singapore Electoral Redistricting

Part of the [project wiki](INDEX.md). See also: [Decisions](decisions.md) · [Seeding](seeding.md) · [Literature](literature/INDEX.md) · [Open Questions](open-questions.md)

---

## Overview

We adapt the Mattingly/Herschlag MCMC ensemble method — originally developed for North Carolina redistricting challenges — to evaluate Singapore's 2020 and 2025 electoral boundary changes.

The core question: **are the 2020 and 2025 Singapore electoral maps outliers with respect to the space of all maps satisfying the same non-partisan criteria?**

---

## The Ensemble Framework

The framework, per Mattingly's ["Ensembles and Outliers"](literature/INDEX.md#mattingly-ensembles-and-outliers-2018), has three cleanly separated components:

| Component | What it is | What can be critiqued |
|-----------|-----------|----------------------|
| Target distribution | The probability distribution over all valid k-partitions, defined by non-partisan criteria (compactness, contiguity, population balance, community preservation) | The choice of criteria; e.g. why Polsby-Popper and not Reock? |
| Sampling algorithm | ReCom (Merge-Split via GerryChain) producing samples from the target distribution | Mixing time, burn-in sufficiency, chain correctness |
| Inference | Percentile-ranking the actual plans against the ensemble distribution on each metric | Metric choice, multiple comparisons, interpretation |

The seed is part of the sampling algorithm, not the target distribution. See [Seeding](seeding.md).

---

## Atomic Units

**Singapore subzones** (URA Master Plan 2019) are the atomic units:
- 332 subzones after filtering 4 offshore islands (SUDONG, SEMAKAU, SOUTHERN GROUP, PULAU SELETAR)
- Population from Census 2020, joined by subzone name
- ~36% of subzones have `pop_total = 0` (parks, reservoirs, industrial zones) — the key Singapore-specific challenge not present in NC precinct-level work

**Contrast with NC:** The [2018 NC paper](literature/INDEX.md#herschlag-quantifying-gerrymandering-in-nc-2018) used ~2,700 census precincts, all with population > 0 (precincts are electoral units by definition). The zero-population subzone problem is uniquely Singaporean.

---

## Partition Parameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| k_districts | 33 | 2025 constituency count; ignores GRC/SMC seat structure for mathematical tractability |
| pop_tolerance | 10% | Standard ±10% deviation used in US redistricting law and NC ensemble analyses |
| n_steps | 10,000 | NC-scale analyses used ~24,000 plans on ~2,700 nodes; 332 nodes requires fewer steps for mixing |
| burn_in | (config default) | Steps discarded before sampling; ensures chain has moved from seed |

**On k=33 vs k=31:** The actual 2020/2025 plans have 31 districts. Using k=33 creates a clean equal-population ensemble but means the comparison is not perfectly apples-to-apples (31-district actual vs. 33-district ensemble). This was a conscious design choice — see [Decisions](decisions.md#on-k33-vs-k31) and [Open Questions](open-questions.md#grc-multi-member-structure).

---

## Metrics

Computed per ensemble plan and for each actual plan:

| Metric | Description | NC analogue |
|--------|-------------|-------------|
| `max_abs_pop_dev` | Maximum absolute population deviation from ideal across all districts | Population equality (Karcher v. Daggett standard) |
| `towns_split` | Number of HDB towns split across district boundaries | County/municipality splitting (NC's primary non-partisan criterion) |
| `pln_area_splits` | Number of URA planning areas split | Secondary community-of-interest metric |
| `mean_pp` | Mean Polsby-Popper compactness score | Compactness (used in NC analyses) |

**HDB towns as communities of interest:** HDB towns (Tampines, Jurong West, Woodlands, etc.) are the closest Singapore analogue to US counties. They are planned residential communities with shared infrastructure, schools, and hawker centres — the natural "communities of interest" the ensemble should preserve. See [Decisions](decisions.md#why-hdb-towns).

---

## ReCom Chain

GerryChain's ReCom (Recombination) proposal:
1. Select two adjacent districts
2. Merge them into a single region
3. Build a random spanning tree of the merged region
4. Find a tree edge whose removal creates two population-balanced subtrees
5. Accept/reject via configured acceptance function

The chain is ergodic over all valid contiguous k-partitions under mild connectivity conditions. See [Autry et al. 2020](literature/INDEX.md#autry-et-al-merge-split-2020).

**Singapore-specific issue:** Steps 2–4 fail when the merged region contains contiguous zero-population clusters, because no spanning-tree cut can balance two subgraphs where one side has all-zero population nodes. This is the root cause of the seeding failure documented in [Issues](issues.md#issue-1) — and why the BFS seeder was necessary.

---

## What We Cannot Do (Partisan Analysis)

The [NC paper](literature/INDEX.md#herschlag-quantifying-gerrymandering-in-nc-2018) overlaid historical election results on ensemble plans to detect partisan outliers. Singapore does not publish precinct-level or polling-district-level vote returns — only constituency-level results, which are too coarse. Partisan analysis is therefore out of scope.

GRC ethnic composition constraints (each GRC must field ≥1 minority candidate) are a real feature of Singapore electoral law but are treated as secondary. Subzone-level ethnic data exists in Census 2020 and could be added as a future metric.

---

## Pipeline

```
data/processed/subzone_with_population.geojson
    ↓ io_layer.py
    ↓ graph_build.py          332-node rook adjacency graph
    ↓ communities.py          attach HDB town labels
    ↓ seed_plans.py           BFS seed partition (k=33)    ← see seeding.md
    ↓ mcmc/recom.py           10,000 ReCom steps
    ↓ metrics/registry.py     per-step metric collection
    ↓ ensemble.py             metrics.parquet + manifest.json
    ↓ assign_actual.py        2020.parquet, 2025.parquet
    ↓ diff_2020_2025.py       percentile ranks
    ↓ reporting/              plots + summary table
```

Full phase status in [Implementation Plan](implementation-plan.md).
