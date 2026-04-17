# Session Log

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

- **Ensemble unblocked:** `run-ensemble --run-id sg2025 --n-steps 10000` started successfully; chain is running

### State at end of session

Ensemble running in background. `BipartitionWarning` messages are normal (rejected ReCom proposals). Check `/tmp/ensemble_sg2025_v2.log`.

### What to do next session

1. Wait for ensemble to complete, check `output/runs/sg2025/`
2. `python -m src.analysis.cli diff --run-id diff_sg2025 --year-2020-run-id sg2025 --year-2025-run-id sg2025`
3. Review `output/runs/sg2025/*.png` and `summary_table.csv`
4. Interpret percentile ranks for HDB town-splitting and population deviation

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
