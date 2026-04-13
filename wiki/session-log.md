# Session Log

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
