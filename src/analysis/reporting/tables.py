"""Summary table generation for the MCMC ensemble analysis."""
from __future__ import annotations

from pathlib import Path

import pandas as pd


def build_summary_table(diff_report: list[dict]) -> pd.DataFrame:
    """Pivot diff_report into a summary DataFrame.

    Columns: metric, value_2020, percentile_2020, value_2025, percentile_2025.
    One row per metric. If a year is missing from report, fill with NaN.
    """
    if not diff_report:
        return pd.DataFrame(
            columns=["metric", "value_2020", "percentile_2020", "value_2025", "percentile_2025"]
        )

    # Build a lookup: (metric, year) → (actual_value, percentile)
    lookup: dict[tuple[str, int], tuple[float, float]] = {}
    metrics_order: list[str] = []
    seen_metrics: set[str] = set()

    for entry in diff_report:
        metric = entry["metric"]
        year = entry["plan_year"]
        lookup[(metric, year)] = (entry["actual_value"], entry["percentile"])
        if metric not in seen_metrics:
            metrics_order.append(metric)
            seen_metrics.add(metric)

    rows = []
    for metric in metrics_order:
        v2020, p2020 = lookup.get((metric, 2020), (float("nan"), float("nan")))
        v2025, p2025 = lookup.get((metric, 2025), (float("nan"), float("nan")))
        rows.append(
            {
                "metric": metric,
                "value_2020": v2020,
                "percentile_2020": p2020,
                "value_2025": v2025,
                "percentile_2025": p2025,
            }
        )

    return pd.DataFrame(rows)


def save_summary_table(df: pd.DataFrame, output_dir: Path) -> tuple[Path, Path]:
    """Write df to output_dir/summary.csv and output_dir/summary.md (markdown table).

    Creates output_dir if needed. Returns (csv_path, md_path).
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_path = output_dir / "summary.csv"
    df.to_csv(csv_path, index=False)

    md_path = output_dir / "summary.md"
    md_path.write_text(df.to_markdown(index=False))

    return csv_path, md_path
