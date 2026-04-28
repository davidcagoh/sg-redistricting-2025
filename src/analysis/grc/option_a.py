"""Option A: post-process paper 1 ensemble with random seat-type permutation.

Null model: for each of the 9,000 seed_001 equal-population steps, randomly
shuffle seat-type labels (N_GRC=18 GRC districts, N_SMC=15 SMC districts)
across the 33 districts and compute minority capture.

Test question: Given equal-population district boundaries, does the actual
2025 seat-type assignment concentrate minority populations in GRC districts at
rates inconsistent with neutral random assignment?

Public API
----------
run_option_a(ensemble_dir, graph, layer, electoral_2025, *, output_dir, ...)
    Full pipeline. Returns OptionAResult.

compute_district_stats(assignments_df, pop_by_node, min_pop_by_node)
    Pure: compute (step, district) → (total_pop, minority_pop).

run_null_distribution(district_stats, *, n_grc, n_districts, n_perms, seed)
    Pure: build null distribution of grc_minority_pct.

compute_actual_capture(node_to_ed, pop_by_node, min_pop_by_node, grc_ed_names)
    Pure: compute actual 2025 GRC minority capture.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# 2025 structure: 15 SMC + 8 GRC(4-seat) + 10 GRC(5-seat) = 33 districts
N_GRC = 18
N_SMC = 15
N_DISTRICTS = 33


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ActualCapture:
    """GRC and SMC minority capture for the actual 2025 plan."""

    grc_minority_pct: float
    smc_minority_pct: float
    grc_total_pop: int
    smc_total_pop: int
    n_grc_nodes: int
    n_smc_nodes: int
    n_unmatched_nodes: int


@dataclass(frozen=True)
class OptionAResult:
    """Full result from Option A analysis."""

    actual: ActualCapture
    null_grc_minority_pct: np.ndarray  # shape (n_steps * n_perms,)
    percentile_rank: float  # 0-100: where actual falls in null distribution
    p_value_above: float  # fraction of null >= actual (one-sided)
    p_value_below: float  # fraction of null <= actual (one-sided)
    n_steps: int
    n_perms: int


# ---------------------------------------------------------------------------
# Pure computation helpers
# ---------------------------------------------------------------------------


def build_node_arrays(
    graph: Any,
) -> tuple[np.ndarray, np.ndarray, int]:
    """Extract pop and minority_pop arrays indexed by node_id.

    Returns
    -------
    pop_by_node:
        Array of length (max_node_id + 1). pop_by_node[node_id] = pop_total.
    min_pop_by_node:
        Array of length (max_node_id + 1). min_pop_by_node[node_id] = pop_total * pct_minority.
    max_node_id:
        Maximum node ID in the graph.
    """
    import networkx as nx

    node_ids = list(graph.nodes())
    max_node_id = max(node_ids)

    pop_by_node = np.zeros(max_node_id + 1, dtype=np.float64)
    min_pop_by_node = np.zeros(max_node_id + 1, dtype=np.float64)

    for n in node_ids:
        attrs = graph.nodes[n]
        pop = float(attrs.get("pop_total", 0))
        pct_min = float(attrs.get("pct_minority", 0.0))
        pop_by_node[n] = pop
        min_pop_by_node[n] = pop * pct_min

    return pop_by_node, min_pop_by_node, max_node_id


def compute_district_stats(
    assignments_df: pd.DataFrame,
    pop_by_node: np.ndarray,
    min_pop_by_node: np.ndarray,
) -> pd.DataFrame:
    """Compute per-(step, district) population and minority population.

    Parameters
    ----------
    assignments_df:
        Parquet-loaded DataFrame with columns: step_index, node_id, district_id.
    pop_by_node:
        Array indexed by node_id → pop_total (from build_node_arrays).
    min_pop_by_node:
        Array indexed by node_id → pop_total * pct_minority.

    Returns
    -------
    DataFrame with columns: step_index, district_id, total_pop, minority_pop.
    One row per (step, district) pair.
    """
    df = assignments_df[["step_index", "node_id", "district_id"]].copy()
    node_ids = df["node_id"].values
    df["pop"] = pop_by_node[node_ids]
    df["minority_pop"] = min_pop_by_node[node_ids]

    stats = (
        df.groupby(["step_index", "district_id"], sort=True)
        .agg(total_pop=("pop", "sum"), minority_pop=("minority_pop", "sum"))
        .reset_index()
    )
    return stats


def run_null_distribution(
    district_stats: pd.DataFrame,
    *,
    n_grc: int = N_GRC,
    n_districts: int = N_DISTRICTS,
    n_perms: int = 100,
    seed: int = 0,
) -> np.ndarray:
    """Build null distribution of GRC minority capture by random label shuffling.

    For each ensemble step, randomly assigns n_grc of the n_districts to 'GRC'
    and the remaining to 'SMC', then computes grc_minority_pct. Repeats n_perms
    times per step.

    Returns
    -------
    null_scores:
        Array of shape (n_steps * n_perms,) with grc_minority_pct values.
    """
    rng = np.random.default_rng(seed)
    step_groups = district_stats.groupby("step_index", sort=True)
    n_steps = len(step_groups)

    null_scores = np.empty(n_steps * n_perms, dtype=np.float64)
    write_idx = 0

    for _step_idx, step_df in step_groups:
        total_pops = step_df["total_pop"].values  # (n_districts,)
        minority_pops = step_df["minority_pop"].values  # (n_districts,)

        # Generate n_perms independent permutations at once: shape (n_perms, n_districts)
        perm_matrix = rng.permuted(
            np.tile(np.arange(n_districts), (n_perms, 1)), axis=1
        )
        grc_masks = perm_matrix < n_grc  # True where district is labelled GRC

        grc_minority = (minority_pops * grc_masks).sum(axis=1)  # (n_perms,)
        grc_total = (total_pops * grc_masks).sum(axis=1)  # (n_perms,)

        with np.errstate(invalid="ignore", divide="ignore"):
            scores = np.where(grc_total > 0, grc_minority / grc_total, 0.0)

        null_scores[write_idx : write_idx + n_perms] = scores
        write_idx += n_perms

    return null_scores


def compute_actual_capture(
    node_to_ed: dict[int, str | None],
    pop_by_node: np.ndarray,
    min_pop_by_node: np.ndarray,
    grc_ed_names: set[str],
) -> ActualCapture:
    """Compute minority capture for the actual 2025 electoral plan.

    Parameters
    ----------
    node_to_ed:
        Mapping node_id → electoral district name (upper-case), or None if unmatched.
    pop_by_node:
        Array indexed by node_id → pop_total.
    min_pop_by_node:
        Array indexed by node_id → pop_total * pct_minority.
    grc_ed_names:
        Set of electoral district names (upper-case) that are GRCs.

    Returns
    -------
    ActualCapture with grc_minority_pct and smc_minority_pct.
    """
    grc_min_pop = 0.0
    grc_tot_pop = 0.0
    smc_min_pop = 0.0
    smc_tot_pop = 0.0
    n_grc_nodes = 0
    n_smc_nodes = 0
    n_unmatched = 0

    for node_id, ed_name in node_to_ed.items():
        if ed_name is None:
            n_unmatched += 1
            continue
        pop = float(pop_by_node[node_id]) if node_id < len(pop_by_node) else 0.0
        min_pop = float(min_pop_by_node[node_id]) if node_id < len(min_pop_by_node) else 0.0

        if ed_name.upper() in grc_ed_names:
            grc_min_pop += min_pop
            grc_tot_pop += pop
            n_grc_nodes += 1
        else:
            smc_min_pop += min_pop
            smc_tot_pop += pop
            n_smc_nodes += 1

    grc_pct = grc_min_pop / grc_tot_pop if grc_tot_pop > 0 else 0.0
    smc_pct = smc_min_pop / smc_tot_pop if smc_tot_pop > 0 else 0.0

    return ActualCapture(
        grc_minority_pct=grc_pct,
        smc_minority_pct=smc_pct,
        grc_total_pop=int(round(grc_tot_pop)),
        smc_total_pop=int(round(smc_tot_pop)),
        n_grc_nodes=n_grc_nodes,
        n_smc_nodes=n_smc_nodes,
        n_unmatched_nodes=n_unmatched,
    )


def compute_percentile_rank(actual_score: float, null_scores: np.ndarray) -> float:
    """Return percentile rank (0-100) of actual_score in null_scores.

    Rank = fraction of null scores strictly below actual × 100.
    """
    return float(np.mean(null_scores < actual_score) * 100)


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------


def run_option_a(
    ensemble_dir: Path,
    graph: Any,
    layer: Any,
    electoral_2025: Any,
    *,
    n_perms: int = 100,
    null_seed: int = 0,
    output_dir: Path | None = None,
) -> OptionAResult:
    """Full Option A pipeline.

    Parameters
    ----------
    ensemble_dir:
        Directory containing assignments.parquet (e.g. data/processed/ensemble/seed_001/).
    graph:
        NetworkX graph with pop_total and pct_minority on nodes.
    layer:
        SubzoneLayer with .svy21 GeoDataFrame.
    electoral_2025:
        GeoDataFrame of 2025 electoral boundaries.
    n_perms:
        Number of random label permutations per ensemble step.
    null_seed:
        RNG seed for the null distribution permutations.
    output_dir:
        If provided, saves null_scores.npy and summary.json there.

    Returns
    -------
    OptionAResult
    """
    from src.analysis.assign_actual import assign_actual_plan

    logger.info("Option A: loading ensemble assignments from %s", ensemble_dir)
    assignments_df = pd.read_parquet(ensemble_dir / "assignments.parquet")
    n_steps = int(assignments_df["step_index"].nunique())
    logger.info("Loaded %d steps, %d rows", n_steps, len(assignments_df))

    # Build node attribute arrays
    logger.info("Building node attribute arrays")
    pop_by_node, min_pop_by_node, _ = build_node_arrays(graph)

    # Compute per-(step, district) stats
    logger.info("Computing district-level population stats")
    district_stats = compute_district_stats(assignments_df, pop_by_node, min_pop_by_node)

    # Null distribution
    logger.info("Running null distribution: %d steps × %d permutations", n_steps, n_perms)
    null_scores = run_null_distribution(
        district_stats,
        n_grc=N_GRC,
        n_districts=N_DISTRICTS,
        n_perms=n_perms,
        seed=null_seed,
    )
    logger.info(
        "Null distribution: mean=%.4f  std=%.4f  [%.4f, %.4f]",
        null_scores.mean(),
        null_scores.std(),
        null_scores.min(),
        null_scores.max(),
    )

    # Actual 2025 plan
    logger.info("Computing actual 2025 minority capture")
    node_to_ed = assign_actual_plan(2025, graph, layer.svy21, electoral_2025)

    # Parse GRC names from ED_DESC_FU
    grc_mask = electoral_2025["ED_DESC_FU"].str.contains("GRC", na=False)
    grc_ed_names: set[str] = set(
        electoral_2025.loc[grc_mask, "ED_DESC"].str.upper().tolist()
    )
    logger.info("GRC constituencies (%d): %s", len(grc_ed_names), sorted(grc_ed_names))

    actual = compute_actual_capture(node_to_ed, pop_by_node, min_pop_by_node, grc_ed_names)
    logger.info(
        "Actual 2025: GRC minority=%.4f  SMC minority=%.4f",
        actual.grc_minority_pct,
        actual.smc_minority_pct,
    )

    # Percentile rank and p-values
    pct_rank = compute_percentile_rank(actual.grc_minority_pct, null_scores)
    p_above = float(np.mean(null_scores >= actual.grc_minority_pct))
    p_below = float(np.mean(null_scores <= actual.grc_minority_pct))

    logger.info(
        "Percentile rank: %.1f%%  p_above=%.4f  p_below=%.4f",
        pct_rank,
        p_above,
        p_below,
    )

    result = OptionAResult(
        actual=actual,
        null_grc_minority_pct=null_scores,
        percentile_rank=pct_rank,
        p_value_above=p_above,
        p_value_below=p_below,
        n_steps=n_steps,
        n_perms=n_perms,
    )

    if output_dir is not None:
        _save_results(result, output_dir)

    return result


def _save_results(result: OptionAResult, output_dir: Path) -> None:
    """Save null scores array and summary JSON to output_dir."""
    import json

    output_dir.mkdir(parents=True, exist_ok=True)

    np.save(output_dir / "null_grc_minority_pct.npy", result.null_grc_minority_pct)

    summary = {
        "actual_grc_minority_pct": result.actual.grc_minority_pct,
        "actual_smc_minority_pct": result.actual.smc_minority_pct,
        "actual_grc_total_pop": result.actual.grc_total_pop,
        "actual_smc_total_pop": result.actual.smc_total_pop,
        "actual_n_grc_nodes": result.actual.n_grc_nodes,
        "actual_n_smc_nodes": result.actual.n_smc_nodes,
        "actual_n_unmatched_nodes": result.actual.n_unmatched_nodes,
        "null_mean": float(result.null_grc_minority_pct.mean()),
        "null_std": float(result.null_grc_minority_pct.std()),
        "null_min": float(result.null_grc_minority_pct.min()),
        "null_max": float(result.null_grc_minority_pct.max()),
        "null_p25": float(np.percentile(result.null_grc_minority_pct, 25)),
        "null_p50": float(np.percentile(result.null_grc_minority_pct, 50)),
        "null_p75": float(np.percentile(result.null_grc_minority_pct, 75)),
        "percentile_rank": result.percentile_rank,
        "p_value_above": result.p_value_above,
        "p_value_below": result.p_value_below,
        "n_steps": result.n_steps,
        "n_perms": result.n_perms,
        "total_null_samples": result.n_steps * result.n_perms,
    }

    with open(output_dir / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    logger.info("Saved results to %s", output_dir)
