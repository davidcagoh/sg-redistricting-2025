# Open Issues

Part of the [project wiki](INDEX.md). See also: [Seeding](seeding.md) · [Methodology](methodology.md) · [Session Log](session-log.md)

**Updated**: 2026-04-17 (session 10) — ISSUE-4 and ISSUE-5 resolved. Ensemble running.

---

## ISSUE-5 (RESOLVED — session 10): BFS seeder fails with non-contiguous district on real graph

**Root cause:** Node 317 (pop=50, no adjacency edges — an isolated subzone) was kept by `filter_for_mcmc` because its population exceeded the old default `min_pop=1`. The BFS seeder's remainder-assignment step assigned it to the smallest-pop district (district 0) without a contiguity check, making district 0 non-contiguous.

**Fix:** Changed `filter_for_mcmc` default from `min_pop=1` to `min_pop=float("inf")` in `src/analysis/graph_build.py`. All non-mainland components are now excluded by default. Node 317's 50 residents (0.001% of total) are negligible.

---

## ISSUE-4 (RESOLVED — session 10): Chain floods with BipartitionWarning — very high rejection rate

**Fix:** `src/analysis/mcmc/recom.py` — `build_chain()` now passes `method=functools.partial(bipartition_tree, allow_pair_reselection=True, max_attempts=1000)` to the `recom` proposal. `allow_pair_reselection` is on `bipartition_tree`, not on `MarkovChain`, in GerryChain 0.3.2. `max_attempts=1000` is critical for speed: without it each failing pair tries 100 000 spanning trees (~20 s/step); with it each pair gives up after 1 000 attempts and reselects (~0.15 s/step).

### Symptom

After seeding succeeds, the MCMC chain emits continuous:

```
BipartitionWarning: Failed to find a balanced cut after 1000 attempts.
If possible, consider enabling pair reselection within your
MarkovChain proposal method to allow the algorithm to select
a different pair of districts for recombination.
```

The chain runs (PID 61909 at 99% CPU) but no output has been written to `output/runs/` after several minutes. Effectively zero accepted proposals.

### Root cause

Each ReCom step selects two adjacent districts, merges them, builds a random spanning tree, and searches for a balanced cut. With Singapore's ~36% zero-population subzones, merged regions often contain contiguous zero-pop clusters where no balanced spanning-tree cut exists. When GerryChain fails to find a cut, it raises BipartitionWarning and that step is rejected — but the chain is not told to try a different district pair. Almost every step fails this way, making the effective acceptance rate ~0.

### Fix

Add `allow_pair_reselection=True` to the `MarkovChain` constructor in `src/analysis/mcmc/recom.py:111`. This tells GerryChain to resample a different adjacent district pair when bipartition fails, rather than rejecting immediately.

```python
return MarkovChain(
    proposal=proposal,
    constraints=constraints,
    accept=acceptance,
    initial_state=initial_partition,
    total_steps=config.n_steps,
    allow_pair_reselection=True,   # ← add this
)
```

**Verification:** After the fix, BipartitionWarnings should disappear or become rare, and `output/runs/sg2025/` should be written within a few minutes of chain start.

### Action for next session

1. Kill the stuck run: `kill 61909`
2. Apply the fix to `src/analysis/mcmc/recom.py`
3. Update tests (tdd-guide agent) — the `build_chain()` test should assert `allow_pair_reselection=True` is passed
4. Re-run: `python -m src.analysis.cli run-ensemble --run-id sg2025 --n-steps 10000`

---

## ISSUE-1 (RESOLVED — session 9): `make_seed_partition` fails on the real Singapore graph

**Resolution:** BFS seeder (Fix A) implemented in `src/analysis/seed_plans.py`. See [Seeding](seeding.md) for full fix rationale and literature basis. See [Decisions](decisions.md#2026-04-17--bfs-seeder-chosen-over-actual-plan-seed) for the methodological decision record.

### Symptom

```
RuntimeError: Could not find a possible cut after 10000 attempts.
→ SeedPartitionError: Failed to generate a valid seed partition after 100 attempt(s).
```

Full traceback in `/tmp/ensemble_sg2025.log`. Occurs during `run-ensemble` at the seeding step, before the MCMC chain starts.

### Root cause

`recursive_tree_part` (GerryChain) builds random spanning trees and looks for an edge whose removal creates two population-balanced subtrees. It fails when:

1. **~36 % of nodes are zero-population** (119 of 332 subzones are parks, reservoirs, industrial zones). These nodes contribute nothing to population balance, so many spanning tree cuts produce one side with near-zero population — outside any plausible epsilon.

2. **Single large-population node can dominate a small subgraph.** At a deep recursion level, the sub-graph being bisected may have only one or two non-zero nodes. If the largest node has population > `(1 + epsilon) * ideal_pop / 2` for that sub-graph, no balanced cut exists regardless of how many spanning trees are tried.

3. **Singapore geography has large contiguous non-residential clusters** (Central Catchment Area, Jurong Island, Western Islands). These cluster together in the adjacency graph, making it highly probable that recursion sub-graphs contain contiguous zero-pop regions that cannot be balanced.

The algorithm retries up to `max_attempts_per_step=100` times; each attempt calls `bipartition_tree` with `max_attempts=10000` spanning trees. All 100 × 10000 attempts fail.

### What was tried

Previous session added a seeding epsilon schedule `[0.45, 0.40, 0.35, 0.30, 0.25, 0.20, config.pop_tolerance]`. This was intended to be lenient for the seed. It did **not** fix the problem because the failure is topological, not epsilon-dependent: no balanced cut exists in certain recursion sub-graphs regardless of epsilon.

### Why a simple population floor (e.g. replace pop=0 with pop=1) does not help

With `ideal_pop ≈ 121 000` and a floor of 1, zero-pop nodes contribute `1 / 121 000 < 0.001 %` to population. The floor is numerically irrelevant. A subgraph whose only non-zero node has population 200 000 still produces unbalanced cuts.

### Proposed fixes (in order of preference)

---

#### Fix A — Custom BFS seed (recommended)

Replace `recursive_tree_part` with a greedy BFS growth algorithm. BFS guarantees contiguity and naturally absorbs zero-pop nodes into adjacent districts.

**Algorithm:**

```python
def _bfs_seed(graph, k, seed_rng):
    # 1. Pick k seeds from non-zero-pop nodes (sample uniformly)
    nonzero = [n for n in graph if graph.nodes[n]["pop_total"] > 0]
    seeds = seed_rng.sample(nonzero, k)
    
    assignment = {s: i for i, s in enumerate(seeds)}
    district_pops = [graph.nodes[s]["pop_total"] for s in seeds]
    frontiers = [set(nb for nb in graph.neighbors(s) if nb not in assignment)
                 for s in seeds]
    unassigned = set(graph.nodes) - set(assignment)
    
    while unassigned:
        # Always grow the district with the smallest population that has frontier
        candidates = [(district_pops[i], i) for i in range(k) if frontiers[i]]
        if not candidates:
            break
        _, best = min(candidates)
        node = seed_rng.choice(sorted(frontiers[best]))
        frontiers[best].discard(node)
        if node not in unassigned:
            continue
        assignment[node] = best
        district_pops[best] += graph.nodes[node]["pop_total"]
        unassigned.discard(node)
        for nb in graph.neighbors(node):
            if nb not in assignment:
                frontiers[best].add(nb)
    
    # Assign any disconnected remainder
    for node in unassigned:
        best = min((assignment[nb] for nb in graph.neighbors(node)
                    if nb in assignment),
                   key=lambda d: district_pops[d], default=0)
        assignment[node] = best
        district_pops[best] += graph.nodes[node]["pop_total"]
    
    return assignment
```

**Population balance concern**: BFS growth roughly balances districts but is not guaranteed to be within `pop_tolerance=0.10` of ideal. Each district's last-added node can push it over by up to one full node population (max ~50 000 for a large subzone = ~40 % overshoot). Therefore:

- After BFS, add a **local-swap pass**: for each district that is outside tolerance, try moving one boundary node to an adjacent under-populated district. Iterate until all districts are within tolerance or max iterations exceeded.
- Retry with a different random seed if swaps fail to converge.

**Implementation location**: `src/analysis/seed_plans.py`. Add `_bfs_seed_partition` as a private function; keep `make_seed_partition` as the public entry point, falling back to BFS if `recursive_tree_part` raises.

---

#### Fix B — Lower k_districts from 33 to 31 and use the 2020 actual plan as seed

**Data facts discovered this session:**

- The 2020 actual assignment parquet (`output/actual_assignments/2020.parquet`) has **328 nodes** and **31 districts**.
- The graph has **332 nodes**. The 4 missing nodes are uninhabited islands with `pop_total=0`:
  - Node 27: SUDONG (WESTERN ISLANDS)
  - Node 28: SEMAKAU (WESTERN ISLANDS)
  - Node 29: SOUTHERN GROUP (SOUTHERN ISLANDS)
  - Node 308: PULAU SELETAR (SIMPANG)
- The 2020 actual plan IS a valid partition: contiguous, population-balanced by Singapore electoral law.

**Procedure:**
1. Change `EnsembleConfig.k_districts` default from `33` to `31` in `src/analysis/config.py`.
2. Update test `test_config.py:36` which asserts `k_districts == 33`, and `test_config.py:311` which checks the manifest JSON.
3. In `make_seed_partition`, load the 2020 actual parquet, convert string `ed_name` → integer district IDs (e.g., sort unique names and map), assign the 4 island nodes to their geographically adjacent mainland district (any adjacent district works; they have zero population).
4. Validate the resulting assignment with `validate_partition`.

**Risk**: Changes the analysis parameter `k` and breaks 2 test assertions. The `implementation-plan.md` constraint says "k=33 equal-population partition (GRC seat-count ignored)" — this was a design choice, not a data constraint. 31 better reflects reality.

---

#### Fix C — Increase `max_attempts` in GerryChain's bipartition_tree

Pass `max_attempts=500_000` through `recursive_tree_part` kwargs. This only helps if balanced cuts exist but are rare. Based on the root cause analysis above, the failure is structural in some recursion sub-graphs — more attempts will not fix it. **Not recommended as a primary fix, but worth trying in combination with Fix A as a fast first path.**

---

### Recommended action for next agent

1. Attempt Fix A (BFS seeding with local swap). It does not change `k_districts` or break tests.
2. If BFS still cannot balance within `pop_tolerance=0.10`, consider Fix B.
3. Do NOT pursue Fix C alone.

---

## ISSUE-2 (NON-BLOCKING): 4 island nodes never assigned to any electoral district

Nodes 27, 28, 29, 308 (see above) have `pop_total=0` and are uninhabited islands. The `assign_actual_plan` function assigns them to `ed_name=None` because they do not intersect any electoral boundary polygon. They are silently excluded from the 2020/2025 parquets.

**Current behaviour**: The `diff` subcommand is written to compare assigned nodes only, so these 4 nodes are harmlessly excluded.

**Potential future issue**: If these nodes are included in the graph used for MCMC but not in the actual assignments used for comparison, there may be off-by-4-node discrepancies in district-level metrics.

**Action**: After Fix A or B lands, verify that `validate_partition` covers all 332 graph nodes (including the 4 islands) in the ensemble seed. The islands should be assigned to some district even if they contribute zero population.

---

## ISSUE-3 (NON-BLOCKING): Session 7 "What to do next" is now stale

`session-log.md` says: "run `diff` subcommand". That cannot happen until the ensemble completes. The ensemble is blocked by ISSUE-1. Update the session log after ISSUE-1 is fixed.

---

## Reproduction steps

```bash
# 1. Confirm ensemble is failing:
python -m src.analysis.cli run-ensemble --run-id debug_seed 2>&1 | tail -20

# 2. Inspect the graph to understand zero-pop distribution:
python3 -c "
import sys; sys.path.insert(0, '.')
from src.utils import PROCESSED, RAW
from src.analysis.io_layer import load_subzones_with_population
from src.analysis.graph_build import build_subzone_graph, filter_for_mcmc
import geopandas as gpd

sz = gpd.read_file(str(PROCESSED / 'subzone_with_population.geojson')).to_crs(epsg=3414)
sz = sz.reset_index(drop=True)
g_raw = build_subzone_graph(sz)
g, excl = filter_for_mcmc(g_raw)
pops = [g.nodes[n]['pop_total'] for n in g.nodes]
print(f'nodes={len(pops)}, zero_pop={sum(1 for p in pops if p==0)}, max_pop={max(pops)}')
"

# 3. After implementing BFS seed, validate it:
python3 -c "
import sys; sys.path.insert(0, '.')
# ... (load graph, call make_seed_partition, call validate_partition) ...
"
```

---

## Key file locations

| File | Relevance |
|------|-----------|
| `src/analysis/seed_plans.py` | Where the fix goes — add BFS seeder here |
| `src/analysis/config.py:28` | `k_districts=33` default |
| `tests/test_config.py:36,311` | Assertions on k_districts default — update if changing to 31 |
| `output/actual_assignments/2020.parquet` | 328-node, 31-district actual plan for Fix B |
| `/tmp/ensemble_sg2025.log` | Full traceback from failed run |
| `wiki/implementation-plan.md:57` | Records "k=33" as a constraint |
