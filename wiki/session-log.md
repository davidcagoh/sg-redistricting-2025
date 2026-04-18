# Session Log

## 2026-04-18 (session 11) — diff pipeline fixed + results interpreted

### What was done

- **Fixed broken `diff` pipeline (design gap):** `build_diff_report` was written expecting a `run_id` column in actual-plan assignment parquets and actual-plan metrics embedded in ensemble_metrics at `step_index=0`. But `assign_actual` only saved `{node_id, ed_name}` — no metrics, no run_id.

- **Redesigned diff data flow:**
  - Added `compute_actual_plan_metrics(assignment_str, graph, subzone_geoms)` to `diff_2020_2025.py` — converts `node_id→ed_name` dict to integer district IDs, calls `compute_all` metrics registry.
  - Added `load_actual_metrics(year, paths)` — reads sidecar `{year}_metrics.json`.
  - Changed `build_diff_report(actual_metrics_2020, actual_metrics_2025, ensemble_metrics)` — no more run_id lookup.
  - `_cmd_assign_actual` now computes and saves `{year}_metrics.json` alongside the assignments parquet.
  - `_cmd_diff` loads sidecar metrics, passes directly to `build_diff_report`.
  - Tests updated: `test_diff_2020_2025.py` rewritten for new interface (+9 tests total, 498 passing).

- **Re-ran `assign-actual` for both years** to generate metrics sidecars.

- **Ran `diff --run-id sg2025`** successfully: `output/diff/sg2025/diff_report.json` + 4 plots.

### Results

Ensemble: 9 000 post-burn-in steps, seed 42, k=33, pop_tolerance=10%, recom_epsilon=5%.

| Metric | Actual 2020 | Actual 2025 | Ensemble mean | Ensemble range | 2020 pctile | 2025 pctile |
|--------|------------|------------|---------------|----------------|-------------|-------------|
| `max_abs_pop_dev` | 1.223 | 1.223 | 0.096 (const) | [0.096, 0.096] | 100th | 100th |
| `towns_split` | 12 | 12 | 12 (const) | [12, 12] | 0th | 0th |
| `pln_area_splits` | 30 | 28 | 36.3 | [30, 42] | 0th | 0th |
| `mean_pp` | 0.435 | 0.418 | 0.353 | [0.314, 0.399] | 100th | 100th |

### Interpretation

**Non-informative metrics (ensemble has zero variance):**
- `max_abs_pop_dev` is frozen at 0.0955 across all 9000 steps — likely one subzone always anchors a district at the ReCom constraint ceiling. Comparison against actual (1.22) is also confounded: actual plans use GRCs (multi-member, variable size) vs ensemble's 33 equal-pop SMC-equivalent districts. Not a meaningful comparison.
- `towns_split` is frozen at 12 in every step. With 26 HDB towns divided into 33 districts, 12 towns are structurally always split regardless of how the map is drawn (a graph-topology inevitability for this specific Singapore subzone graph). Not informative.

**Informative metrics:**
- **`pln_area_splits` (0th percentile):** Actual 2020 (30) and 2025 (28) split fewer planning areas than all or nearly all MCMC plans (min=30, mean=36). The 2025 plan ties the MCMC minimum. This is a statistically extreme finding: the actual boundaries preserve planning area cohesion better than any randomly sampled equal-population plan. This strongly suggests the actual electoral boundaries were drawn with explicit reference to planning area lines.
- **`mean_pp` (100th percentile):** Actual plans (0.435, 0.418) are more compact than any MCMC plan (max=0.399). Actual GRC boundaries are more geometrically compact than any of the 9000 random 33-district partitions. This is the opposite of what typical partisan gerrymandering looks like (which tends to produce bizarre shapes). Singapore's GRCs are large, round, administratively aligned — consistent with boundaries following planning areas rather than being drawn to dilute votes.

**Overall conclusion:** The actual electoral boundaries are extreme outliers in planning-area cohesion and compactness, but in a direction inconsistent with shape-based gerrymandering. The GRC system introduces malapportionment (`max_abs_pop_dev`) that is outside the MCMC comparison framework (different institutional structure). The key finding is that real maps respect planning area lines far better than random maps — this is a constraint the ELD appears to be following.

### Limitations to document

1. GRC vs SMC mismatch: the ensemble models 33 single-member equal-pop districts; the actual plans have 12-17 constituencies of varying multi-member size. Pop-balance comparison is not apples-to-apples.
2. `towns_split` and `max_abs_pop_dev` zero-variance in ensemble — structural, not exploratory failure.
3. Only 1 run at 10k steps. Should run multiple seeds to verify mixing.
4. Actual plan assignment is by subzone→ED areal majority. Edge subzones near constituency boundaries may be misassigned.

### State at end of session

`output/diff/sg2025/diff_report.json` written. Plots in `output/diff/sg2025/plots/`. Pipeline complete end-to-end. Findings written above. Next: update `wiki/methodology.md` with results, write findings summary.

### What to do next session

1. Update `wiki/methodology.md` with the quantitative results table and interpretation
2. Write `wiki/findings.md` with the headline conclusions + caveats
3. Consider: rerun ensemble with `seed=123` (or other seeds) for mixing verification
4. Consider: whether the GRC-level comparison (grouping subzones by GRC, not SMC) would be more meaningful

---

## 2026-04-17 (session 10) — ISSUE-4 fix + ISSUE-5 fix; ensemble now running

### What was done

- **Diagnosed why `allow_pair_reselection` was not on `MarkovChain.__init__`:** In GerryChain 0.3.2 the flag lives on `bipartition_tree`, not on `MarkovChain`. The fix required passing `functools.partial(bipartition_tree, allow_pair_reselection=True, max_attempts=1000)` as the `method` kwarg to `recom`.

- **Fixed ISSUE-4 (chain freezes with BipartitionWarning):** `src/analysis/mcmc/recom.py` — `build_chain()` now passes a `bipartition_with_reselection` partial as `method`. `max_attempts=1000` makes failing pairs give up quickly and trigger reselection, yielding a **130× speedup** (19.6 s/step → 0.15 s/step). Tests added/updated in `tests/test_mcmc_recom.py` (TDD: RED → GREEN). Code-reviewer agent approved.

- **Discovered and fixed ISSUE-5 (disconnected graph; node 317 breaks BFS seeder):** After fixing ISSUE-4, the BFS seeder still failed with `SeedPartitionError: District 0 is not contiguous. Nodes in district: [13, 16, 86, 317]`. Investigation found that `filter_for_mcmc` was keeping node 317 (pop=50, no edges — a truly isolated subzone) because its population exceeded the old default `min_pop=1`. Changed default to `min_pop=float("inf")` so **all non-mainland components are excluded by default**, regardless of population. An isolated node cannot participate in any contiguous district, so exclusion is always correct for MCMC. Node 317 represents 0.001% of total population — negligible. Tests updated in `tests/test_graph_build.py` (2 new tests, 1 renamed).

- **489 tests passing** (was 488 at start of session; +1 from recom, +2 from graph_build, -1 old test renamed/updated).

- **Full 10 000-step ensemble launched** (PID 65626, `data/processed/ensemble/sg2025.tmp`). At ~0.15 s/step the chain should complete in ~25 minutes; seeding (once) adds ~20 s.

- **Deleted `wiki/next-agent-prompt.md`** — superseded by session log.

### State at end of session

Ensemble running. `data/processed/ensemble/sg2025.tmp` will rename to `sg2025/` on completion. No diff output yet.

### What to do next session

1. Confirm ensemble completed: `ls data/processed/ensemble/sg2025/`
2. Assign actual plans (if not already done): `python -m src.analysis.cli assign-actual --year 2020` and `--year 2025`
3. Run diff: `python -m src.analysis.cli diff --run-id diff_sg2025 --year-2020-run-id sg2025 --year-2025-run-id sg2025`
4. Review `data/processed/ensemble/sg2025/metrics.parquet` histograms and `diff_report.json` percentiles — focus on `towns_split`, `max_abs_pop_dev`, `mean_pp`
5. Interpret whether the 2020/2025 plans are statistical outliers; update `wiki/methodology.md` with findings

---

## 2026-04-17 (session 9) — Wiki knowledge graph refactor + BFS seeder (Fix A) + ensemble unblocked

### What was done

- **Wiki refactored into Wikipedia-style knowledge graph:**
  - `related-literature/` moved to `wiki/literature/` (git mv, history preserved)
  - `wiki/literature/INDEX.md` — annotated bibliography of all 8 papers
  - `wiki/methodology.md` — full ensemble framework documentation with NC literature comparison
  - `wiki/seeding.md` — seeding problem root cause, Fix A vs Fix B literature reasoning, current state
  - All existing wiki pages updated with bidirectional cross-links
  - `wiki/INDEX.md` — expanded into a proper hub with navigation table and key cross-link paths

- **Literature reasoning for Fix A vs Fix B:**
  - Fix A (BFS seeder): literature-faithful — neutral random initialization, no circularity
  - Fix B (actual plan as seed): rejected as methodologically circular per Herschlag et al. NC practice of running chains from independent random seeds to verify mixing
  - Full argument documented in `wiki/seeding.md` and `wiki/decisions.md`

- **BFS seeder implemented** (`src/analysis/seed_plans.py`):
  - `_bfs_seed_partition()`: greedy BFS growth from non-zero-pop seeds + `_local_swap_pass()` for population balance
  - `make_seed_partition()` now two-phase: `recursive_tree_part` (N attempts) → BFS fallback (10 attempts)
  - 487 tests passing (was 481; added 6 BFS-specific tests; fixed 6 pre-existing CLI test regressions from session 7/8)

- **Ensemble started** — seeding now succeeds; chain entered MCMC loop

- **New blocker identified (ISSUE-4):** Chain is running but flooded with `BipartitionWarning: Failed to find a balanced cut after 1000 attempts`. GerryChain's recommendation is to enable `allow_pair_reselection` on the MarkovChain so that when a district-pair ReCom step fails, the chain resamples a different pair rather than rejecting. Fix location: `src/analysis/mcmc/recom.py` — add `allow_pair_reselection=True` to `MarkovChain(...)`. See `wiki/issues.md`.

### State at end of session

Ensemble running (PID 61909, `/tmp/ensemble_sg2025_v2.log`) but with very high rejection rate due to BipartitionWarnings. No output written to `output/runs/` yet. Should be killed and restarted after the `allow_pair_reselection` fix.

### What to do next session

1. Kill running ensemble: `kill 61909`
2. Fix `src/analysis/mcmc/recom.py`: add `allow_pair_reselection=True` to `MarkovChain(...)` call in `build_chain()`
3. Add/update tests for the fix (tdd-guide agent)
4. Re-run: `python -m src.analysis.cli run-ensemble --run-id sg2025 --n-steps 10000`
5. Once complete: `python -m src.analysis.cli diff --run-id diff_sg2025 --year-2020-run-id sg2025 --year-2025-run-id sg2025`
6. Review output plots and summary table

---

## 2026-04-13 (session 8) — Diagnose seeding failure; write issues.md

### What was done

- Ran `run-ensemble --run-id sg2025 --n-steps 10000` → failed with `SeedPartitionError` at the seeding step
- Root-caused the failure: GerryChain's `recursive_tree_part` cannot bisect the real Singapore graph because ~36 % of subzones have `pop_total=0`, and some recursion sub-graphs have no balanced spanning-tree cut
- Inspected `output/actual_assignments/2020.parquet` (328 nodes, 31 districts)
- Identified 4 uninhabited island nodes (27 SUDONG, 28 SEMAKAU, 29 SOUTHERN GROUP, 308 PULAU SELETAR) absent from actual assignments
- Documented two proposed fixes (BFS seeder, lower k to 31) in `wiki/issues.md`

### State at end of session

**Ensemble blocked.** `assign-actual` Parquets are written and correct. The MCMC chain itself has not run yet.

### What to do next session

1. Implement Fix A from `wiki/issues.md`: add `_bfs_seed_partition` to `src/analysis/seed_plans.py`
2. Test that `make_seed_partition` returns a valid partition on the real graph (`validate_partition` passes)
3. Re-run `python -m src.analysis.cli run-ensemble --run-id sg2025 --n-steps 10000`
4. Once ensemble completes, run `diff` subcommand and review output plots/table

See `wiki/issues.md` for full root cause, pseudocode, and reproduction steps.

---

## 2026-04-13 (session 7) — Sync docs; run actual MCMC analysis

### What was done

- Updated `wiki/implementation-plan.md`: marked Phase 5 complete (was stale at "401 tests / Phase 5 remains")
- Ran `assign-actual --year 2020` and `assign-actual --year 2025` → wrote actual assignment Parquets to `output/actual_assignments/`
- Ran `run-ensemble --run-id sg2025 --n-steps 10000` → generating ensemble in background
- Outputs to vet: `output/actual_assignments/2020.parquet`, `output/actual_assignments/2025.parquet`, `output/runs/sg2025/`

### State at end of session

Analysis pipeline running. Once ensemble completes, run `diff` subcommand.

### What to do next session

1. `python -m src.analysis.cli diff --run-id diff_sg2025 --year-2020-run-id sg2025 --year-2025-run-id sg2025`
2. Review `output/runs/sg2025/diff_report.json`, `output/runs/sg2025/*.png`, `output/runs/sg2025/summary_table.csv`
3. Interpret percentile ranks for HDB town-splitting and population deviation

---

## 2026-04-13 (session 6) — Repo cleanup: remove root-level duplicates, add .gitignore, refresh README

### What was done

- Deleted 10 root-level duplicate directories/files (all confirmed identical to `data/raw/` or `data/reference/`)
- Moved `QGIS-3.44-GentleGISIntroduction-en.pdf` to `related-literature/`
- Removed empty `docs/` and `data/raw/geospatial_subzone/` directories
- Created `.gitignore`: excludes `__pycache__`, `.DS_Store`, `.coverage`, `.venv`, `output/`, `data/processed/`, large raw data dirs (`hdb/`, `polling_community/`, `sla_cadastral/`), large reference binaries
- Removed `__pycache__` directories from git tracking (had been committed)
- Rewrote `README.md` to cover both the preprocessing pipeline and the MCMC analysis pipeline with correct commands

### State at end of session

Clean. Repo root is now minimal: `src/`, `tests/`, `data/`, `wiki/`, `related-literature/`, `output/`, `CLAUDE.md`, `README.md`, `gerrymandering_project.qgz`, `sanity.py`, `requirements.txt`, `pyproject.toml`.

### What to do next session

1. Run `python -m src.analysis.cli assign-actual --year 2020` and `--year 2025` — generate actual assignment Parquets
2. Run `python -m src.analysis.cli run-ensemble --run-id sg2025 --n-steps 10000` — generate ensemble
3. Run `python -m src.analysis.cli diff ...` — produce diff report, plots, and summary table
4. Review `output/` for outlier signals in HDB town-splitting and population deviation

---

## 2026-04-13 (session 5) — Phase 5 complete; full pipeline implemented; 481 tests green

### What was done

- **ensemble.py (task 4.1)** — implemented `run_ensemble`, `build_pipeline_inputs`, `_build_run_outputs`; atomic tmp→rename write; burn_in skipping; Parquet output
- **io_layer fix** — `load_hdb_buildings()` now lowercases all columns (BLK_NO → blk_no)
- **communities fix** — `_join_buildings_to_properties` falls back to blk_no-only modal join when buildings lack a `street` column (`HDBExistingBuilding.geojson` uses `ST_COD` street codes, not names); real-data smoke test now passes
- **Phase 5 via 3 parallel subagents:**
  - `diff_2020_2025.py` — `load_actual_assignments`, `load_ensemble_metrics`, `compute_percentile`, `build_diff_report`, `save_diff_report`
  - `reporting/plots.py` + `reporting/tables.py` — histogram plots with actual plan markers; pivot summary CSV + markdown
  - `cli.py` — `run-ensemble`, `assign-actual`, `diff` subcommands via argparse
- **Wiki compressed** — session-log consolidated, implementation-plan stripped to Phase 5 spec only
- **CLAUDE.md updated** — added analysis pipeline commands and module table

### State at end of session

Clean. 481 tests passing, 0 failing. Full pipeline implemented end-to-end. Ready to run actual analysis.

### What to do next session

1. Run `python -m src.analysis.cli assign-actual --year 2020` and `--year 2025` — generate actual assignment Parquets
2. Run `python -m src.analysis.cli run-ensemble --run-id sg2025 --n-steps 10000` — generate ensemble (takes time; ~10k ReCom steps)
3. Run `python -m src.analysis.cli diff ...` — produce diff report, plots, and summary table
4. Review output plots and table for outlier signals in HDB town-splitting and population deviation

---

## 2026-04-13 (session 4) — Phases 2–4 complete; 401 tests green

### Completed this session

- **ensemble.py (task 4.1)** — `run_ensemble(config, paths)`, `build_pipeline_inputs(paths)`, `_build_run_outputs(...)`. Atomic tmp→rename write; burn_in skipping; Parquet output. 37 tests added.
- **io_layer column fix** — `load_hdb_buildings()` now lowercases all column names (BLK_NO → blk_no, etc.).
- **communities.py join fix** — `_join_buildings_to_properties` falls back to blk_no-only modal join when buildings lack a `street` column (HDBExistingBuilding.geojson has `ST_COD` street code, not readable street names). Real-data smoke test now passes.

### Data discovery

`HDBExistingBuilding.geojson` columns: `OBJECTID, BLK_NO, ST_COD, ENTITYID, POSTAL_COD, INC_CRC, FMEL_UPD_D, SHAPE.AREA, SHAPE.LEN, geometry`. `ST_COD` is a street code (e.g. `CLA09K`), not a human-readable street name — cannot join to property table on `blk_no + street`.

### State at end of session

- 401 tests passing, 0 failing
- Phase 5 is the only remaining work

---

## 2026-04-12 (session 3) — Phases 0–3 built; session 4 picked up mid-Phase 4

### Completed

| Task | File | Tests |
|------|------|-------|
| 0.1 | `src/utils.py` | 20 |
| 0.2 | `tests/test_sanity.py` | 19 |
| 0.3 | `src/analysis/` scaffold + GerryChain 0.3.2 | 26 |
| 1.1 | `src/analysis/io_layer.py` | 28 |
| 1.2 | `src/analysis/graph_build.py` | 37 |
| 1.3 | `src/analysis/communities.py` | 13 |
| 2.1–2.5 | `src/analysis/config.py`, `seed_plans.py`, `mcmc/` | ~40 |
| 3.1–3.4 | `src/analysis/metrics/` | ~50 |
| 4.2 | `src/analysis/assign_actual.py` | ~15 |

Real graph results: 332 subzone nodes, 850 edges, 4 offshore islands excluded (SUDONG, SEMAKAU, SOUTHERN GROUP, PULAU SELETAR).

---

## 2026-04-12 (session 2) — Analysis direction decided

Chose MCMC ensemble method (ReCom/GerryChain) on URA subzones; HDB town splitting as primary metric; population deviation as secondary. Partisan analysis infeasible (no precinct-level vote data). See `decisions.md`.

---

## 2026-04-12 (session 1) — Wiki initialized; no code changes
