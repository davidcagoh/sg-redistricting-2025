# Implementation Plan

Phases 0–4 complete (401 tests). Only Phase 5 remains.

## Completed phases (summary)

| Phase | Tasks | Tests |
|-------|-------|-------|
| 0: Foundations | utils.py, test_sanity.py, analysis scaffold | 65 |
| 1: Graph | io_layer.py, graph_build.py, communities.py | 78 |
| 2: MCMC skeleton | config.py, seed_plans.py, mcmc/constraints+acceptance+recom | ~40 |
| 3: Metrics | metrics/population+compactness+splitting+registry | ~50 |
| 4: Ensemble driver | ensemble.py, assign_actual.py | ~52 |

## Phase 5: Diff + Reporting + CLI

### 5.1 `src/analysis/diff_2020_2025.py`

Compare actual 2020 and 2025 plans against the ensemble distribution.

- `load_actual_assignments(year) -> pd.DataFrame` — loads from `output/actual_assignments/<year>.parquet`
- `load_ensemble_metrics(run_id, paths) -> pd.DataFrame` — reads `metrics.parquet`
- `compute_percentile(actual_val, ensemble_vals) -> float` — percentile rank of a scalar in a distribution
- `build_diff_report(year_2020, year_2025, ensemble_metrics) -> dict` — keys: plan_year, metric, actual_value, percentile, n_ensemble
- `save_diff_report(report, output_dir)` — writes `diff_report.json`

Metrics to compare: `max_abs_pop_dev`, `towns_split`, `pln_area_splits`, `mean_pp`.

### 5.2 `src/analysis/reporting/plots.py`

Histogram + marker plots showing where actual plans sit in the ensemble distribution.

- `plot_metric_distribution(ensemble_vals, actual_vals_by_year, metric_name, ax)` — histogram with vertical lines for 2020/2025 actual
- `save_all_plots(diff_report, ensemble_metrics, output_dir)` — writes PNG files for each metric

### 5.3 `src/analysis/reporting/tables.py`

- `build_summary_table(diff_report) -> pd.DataFrame` — columns: metric, value_2020, percentile_2020, value_2025, percentile_2025
- `save_summary_table(df, output_dir)` — writes CSV + markdown

### 5.4 `src/analysis/cli.py`

Three subcommands:
1. `run-ensemble` — calls `run_ensemble(config, paths)`
2. `assign-actual` — calls `assign_actual_plan(year, ...)` for 2020 and 2025
3. `diff` — calls `build_diff_report(...)` and `save_all_plots(...)`

Use `argparse`. Entry point: `python -m src.analysis.cli`.

## Key constraints (immutable)

- GerryChain as MCMC engine — do not reinvent ReCom acceptance ratio
- `dict[node_id, district_id]` as the universal partition representation
- Parquet for ensemble output (not JSON — too large at 10k × 320 rows)
- Run manifest with git SHA + input hashes — non-negotiable
- k=33 equal-population partition (GRC seat-count ignored)
- Same seed → byte-identical metrics.parquet
