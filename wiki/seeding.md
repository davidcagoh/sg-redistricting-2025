# Seeding — MCMC Initializer for the Singapore Graph

Part of the [project wiki](INDEX.md). See also: [Issues](issues.md#issue-1) · [Methodology](methodology.md#recom-chain) · [Decisions](decisions.md) · [Literature](literature/INDEX.md)

---

## What Is a Seed Partition?

A seed partition is the initial assignment of subzone nodes to districts passed to the GerryChain ReCom chain. It is the chain's starting state, not a draw from the target distribution. Per the Mattingly framework (["Ensembles and Outliers"](literature/INDEX.md#mattingly-ensembles-and-outliers-2018)):

> *The seed is part of the sampling algorithm, not the definition of the ensemble.*

Any valid seed — contiguous, population-balanced within tolerance — is equivalent after sufficient chain mixing. The chain is ergodic and converges to the same stationary distribution regardless of initialization (proven in [Autry et al. 2020](literature/INDEX.md#autry-et-al-merge-split-2020)).

---

## The Seeding Failure

`recursive_tree_part` (GerryChain's default seeder) builds random spanning trees of the full graph and searches for an edge whose removal creates two population-balanced subtrees. On the Singapore graph it fails with:

```
RuntimeError: Could not find a possible cut after 10000 attempts.
→ SeedPartitionError: Failed to generate a valid seed partition after 100 attempt(s).
```

**Root cause:** ~119 of 332 subzones (36%) have `pop_total = 0` (parks, reservoirs, industrial zones). Large contiguous zero-population clusters (Central Catchment Area, Jurong Island, Western Islands) appear in adjacency graph recursion sub-graphs. Within such a sub-graph, every spanning-tree cut produces one side with near-zero total population — outside any plausible epsilon. The failure is topological, not stochastic. More attempts (Fix C) cannot fix it.

**Contrast with NC:** The [2018 NC paper](literature/INDEX.md#herschlag-quantifying-gerrymandering-in-nc-2018) used ~2,700 census precincts, all with `pop > 0`. `recursive_tree_part` works on NC graphs because every spanning-tree cut produces two sides with non-trivial population.

Full root cause, reproduction steps, and node inventory: [Issues](issues.md#issue-1).

---

## Fix A vs Fix B — Literature Basis

### Fix A: Custom BFS Seeder (chosen)

Replaces `recursive_tree_part` with a greedy BFS growth algorithm:
1. Pick k seeds from non-zero-population subzones (random sample)
2. Grow each district by BFS, always expanding the district with smallest current population
3. Assign disconnected remainder nodes to adjacent districts
4. Run a local boundary swap pass to bring all districts within `pop_tolerance`
5. Validate; retry with a different random seed if validation fails

**Why this is literature-faithful:**
- Produces a neutral, spatially random starting state — the chain can move freely from it
- Does not introduce political or structural bias into the ensemble
- BFS guarantees contiguity by construction; the swap pass handles population balance
- After 10,000 ReCom steps on a 332-node graph, chain mixing wipes out any initialization effect

**Implementation:** `src/analysis/seed_plans.py` — `_bfs_seed_partition()` called as fallback from `make_seed_partition()` when `recursive_tree_part` fails all `max_attempts_per_step` attempts.

---

### Fix B: Use 2020 Actual Plan as Seed (rejected)

Change k→31 and initialise the chain from the actual 2020 electoral plan.

**Why this is methodologically problematic (per NC literature):**

Herschlag et al. run multiple chains from *different random seeds* specifically to verify chain mixing and independence from initialization. Starting the chain from the plan you are testing for outlier status introduces circular reasoning:

- If burn-in is insufficient, the ensemble concentrates near the actual plan, understating its outlier-ness
- You cannot simultaneously use the actual plan as seed AND claim the ensemble is an independent baseline against which to test it
- This conflates component (2) (sampling algorithm) with component (3) (inference) in Mattingly's three-way separation

The k=33→31 change is a separate methodological question (see [Open Questions](open-questions.md#grc-multi-member-structure)) that deserves its own decision record, not bundling into a seeding fix.

---

### Fix C: Increase max_attempts (rejected)

Per the root cause analysis, the seeding failure is structural (no balanced cut exists in certain sub-graphs) not stochastic (balanced cuts exist but are rare). Additional attempts cannot find cuts that do not exist.

---

## Current State

Fix A is implemented as of session 9. `make_seed_partition` now:
1. Tries `recursive_tree_part` for `config.max_attempts_per_step` attempts (phase 1)
2. Falls back to `_bfs_seed_partition` with 10 attempts at different seeds (phase 2)
3. Raises `SeedPartitionError` only if both phases fail

Ensemble unblocked. See [Session Log](session-log.md) for run history.
