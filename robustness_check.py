"""Robustness check: compare sg2025 (seed=42), seed_001 (seed=1), seed_002 (seed=2).

Outputs:
  - Per-metric ensemble distribution stats across seeds (mean, std, p5, p50, p95)
  - Actual 2020 and 2025 plan percentile ranks re-computed against each seed
  - Kolmogorov-Smirnov D-statistic between seed pairs (how different are the distributions?)
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

BASE = Path(__file__).parent
ENSEMBLE_DIR = BASE / "data/processed/ensemble"
ACTUAL_DIR = BASE / "output/actual_assignments"

RUNS = ["sg2025", "seed_001", "seed_002"]
METRICS = ["towns_split", "pln_area_splits", "max_abs_pop_dev", "mean_pp"]
METRIC_LABELS = {
    "towns_split": "HDB towns split",
    "pln_area_splits": "Planning-area splits",
    "max_abs_pop_dev": "Max abs pop deviation",
    "mean_pp": "Mean Polsby-Popper",
}


def load_run(run_id: str) -> pd.DataFrame:
    return pd.read_parquet(ENSEMBLE_DIR / run_id / "metrics.parquet")


def percentile_rank(actual: float, ensemble: np.ndarray) -> float:
    return 100.0 * (ensemble < actual).sum() / len(ensemble)


def main() -> None:
    runs = {r: load_run(r) for r in RUNS}
    actual_2020 = json.loads((ACTUAL_DIR / "2020_metrics.json").read_text())
    actual_2025 = json.loads((ACTUAL_DIR / "2025_metrics.json").read_text())

    print("=" * 72)
    print("ENSEMBLE DISTRIBUTION STATS  (9,000 post-burn-in steps each)")
    print("=" * 72)
    print(f"{'Metric':<26} {'Run':<12} {'mean':>8} {'std':>7} {'p5':>8} {'p50':>8} {'p95':>8}")
    print("-" * 72)

    for metric in METRICS:
        label = METRIC_LABELS[metric]
        for i, run_id in enumerate(RUNS):
            col = runs[run_id][metric].to_numpy()
            tag = label if i == 0 else ""
            print(
                f"{tag:<26} {run_id:<12} "
                f"{col.mean():>8.3f} {col.std():>7.3f} "
                f"{np.percentile(col, 5):>8.3f} "
                f"{np.percentile(col, 50):>8.3f} "
                f"{np.percentile(col, 95):>8.3f}"
            )
        print()

    print("=" * 72)
    print("KS-TEST  (D-stat between seed pairs; D < 0.05 → near-identical distributions)")
    print("=" * 72)
    print(f"{'Metric':<26} {'sg2025 vs 001':>14} {'sg2025 vs 002':>14} {'001 vs 002':>12}")
    print("-" * 72)
    for metric in METRICS:
        a = runs["sg2025"][metric].to_numpy()
        b = runs["seed_001"][metric].to_numpy()
        c = runs["seed_002"][metric].to_numpy()
        d_ab = stats.ks_2samp(a, b).statistic
        d_ac = stats.ks_2samp(a, c).statistic
        d_bc = stats.ks_2samp(b, c).statistic
        label = METRIC_LABELS[metric]
        print(f"{label:<26} {d_ab:>14.4f} {d_ac:>14.4f} {d_bc:>12.4f}")

    print()
    print("=" * 72)
    print("ACTUAL PLAN PERCENTILE RANKS  (re-computed against each seed)")
    print("Lower percentile = actual plan more extreme than ensemble")
    print("=" * 72)
    for year, actual in [(2020, actual_2020), (2025, actual_2025)]:
        print(f"\n  Plan year: {year}")
        print(f"  {'Metric':<26} {'sg2025':>8} {'seed_001':>9} {'seed_002':>9}  actual_val")
        print(f"  {'-'*65}")
        for metric in METRICS:
            val = float(actual[metric])
            pcts = [
                percentile_rank(val, runs[r][metric].to_numpy()) for r in RUNS
            ]
            print(
                f"  {METRIC_LABELS[metric]:<26} "
                + "".join(f"{p:>8.1f}%" for p in pcts)
                + f"   {val:.4f}"
            )


if __name__ == "__main__":
    main()
