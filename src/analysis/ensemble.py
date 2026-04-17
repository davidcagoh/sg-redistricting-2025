"""MCMC ensemble driver.

Orchestrates the full pipeline:
  load data → build graph → seed → chain → sample → write Parquet + manifest.

Output layout::

    output/ensemble/<run_id>/
        metrics.parquet      – one row per post-burn-in step
        assignments.parquet  – long format: (run_id, step_index, node_id, district_id)
        manifest.json        – provenance record
"""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import geopandas as gpd
import networkx as nx
import pandas as pd

from src.analysis.communities import attach_hdb_towns
from src.analysis.config import (
    EnsembleConfig,
    PathsConfig,
    RunManifest,
    get_git_sha,
    make_run_id,
    manifest_to_dict,
)
from src.analysis.graph_build import build_subzone_graph, filter_for_mcmc
from src.analysis.io_layer import (
    load_hdb_buildings,
    load_hdb_property_table,
    load_subzones_with_population,
)
from src.analysis.mcmc.acceptance import make_acceptance
from src.analysis.mcmc.constraints import build_constraints
from src.analysis.mcmc.recom import build_chain, build_initial_partition
from src.analysis.metrics.registry import compute_all
from src.analysis.seed_plans import make_seed_partition


# ---------------------------------------------------------------------------
# Pipeline input loader
# ---------------------------------------------------------------------------


def build_pipeline_inputs(
    paths: PathsConfig,
) -> tuple[nx.Graph, gpd.GeoDataFrame, dict[Any, Any]]:
    """Load data and build the filtered, annotated graph.

    Returns
    -------
    graph
        Filtered subzone graph with ``hdb_town`` and ``pln_area`` node attrs.
    filtered_gdf
        GeoDataFrame (SVY21) for the filtered subzones only.
    subzone_geoms
        ``{row_index: geometry}`` mapping for the filtered subzones.
    """
    subzone_layer = load_subzones_with_population()
    hdb_buildings = load_hdb_buildings()
    hdb_properties = load_hdb_property_table()

    graph = build_subzone_graph(subzone_layer.svy21)
    filtered_graph, _excluded = filter_for_mcmc(graph)
    annotated_graph = attach_hdb_towns(
        filtered_graph, subzone_layer.svy21, hdb_buildings, hdb_properties
    )

    # Build filtered GDF and geometry lookup from the annotated graph's nodes
    filtered_gdf = subzone_layer.svy21.loc[list(annotated_graph.nodes)]
    subzone_geoms = {idx: row.geometry for idx, row in filtered_gdf.iterrows()}

    return annotated_graph, filtered_gdf, subzone_geoms


# ---------------------------------------------------------------------------
# Output writer
# ---------------------------------------------------------------------------


def _build_run_outputs(
    run_dir: Path,
    metrics_rows: list[dict],
    assignment_rows: list[dict],
    manifest: RunManifest,
) -> None:
    """Write metrics.parquet, assignments.parquet, and manifest.json into *run_dir*."""
    metrics_df = pd.DataFrame(metrics_rows) if metrics_rows else pd.DataFrame(
        columns=[
            "run_id", "step_index", "accepted",
            "max_abs_pop_dev", "pop_range", "ideal_pop",
            "mean_pp", "min_pp", "cut_edges",
            "towns_split", "pln_area_splits", "town_split_entropy",
        ]
    )
    assignment_df = pd.DataFrame(assignment_rows) if assignment_rows else pd.DataFrame(
        columns=["run_id", "step_index", "node_id", "district_id"]
    )

    metrics_df.to_parquet(run_dir / "metrics.parquet", index=False)
    assignment_df.to_parquet(run_dir / "assignments.parquet", index=False)

    manifest_data = manifest_to_dict(manifest)
    (run_dir / "manifest.json").write_text(
        json.dumps(manifest_data, indent=2, sort_keys=True) + "\n"
    )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def run_ensemble(config: EnsembleConfig, paths: PathsConfig) -> Path:
    """Run an MCMC ensemble and write outputs to disk.

    Parameters
    ----------
    config:
        Ensemble hyperparameters.
    paths:
        Filesystem paths.

    Returns
    -------
    Path
        The final run directory containing metrics.parquet, assignments.parquet,
        and manifest.json.

    Raises
    ------
    FileExistsError
        If the final run directory already exists (prevents accidental overwrite).
    """
    run_id = make_run_id(config)
    final_dir = paths.ensemble_dir(run_id)
    tmp_dir = Path(str(final_dir) + ".tmp")

    if final_dir.exists():
        raise FileExistsError(
            f"Ensemble run directory already exists: {final_dir}. "
            "Choose a different run_id or delete the existing directory."
        )

    # Remove stale tmp dir from a crashed prior run
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)

    tmp_dir.mkdir(parents=True, exist_ok=True)
    started_at = datetime.now(tz=timezone.utc).isoformat()
    git_sha = get_git_sha()

    try:
        graph, filtered_gdf, subzone_geoms = build_pipeline_inputs(paths)

        seed_assignment = make_seed_partition(graph, config)
        initial_partition = build_initial_partition(graph, seed_assignment, config)
        raw_constraints = build_constraints(config)
        acceptance = make_acceptance(config)
        # constraints[1] is a partial(within_percent_of_ideal_population, percent=...)
        # that must be called with the initial partition to produce a live Bounds callable.
        pop_bounds = raw_constraints[1](initial_partition)
        live_constraints = [raw_constraints[0], pop_bounds]
        chain = build_chain(initial_partition, config, live_constraints, acceptance)

        metrics_rows: list[dict] = []
        assignment_rows: list[dict] = []
        n_accepted = 0

        for step_index, partition in enumerate(chain):
            if step_index < config.burn_in:
                continue

            metrics = compute_all(
                partition.parts, subzone_geoms, graph, partition.assignment
            )

            metrics_rows.append(
                {
                    "run_id": run_id,
                    "step_index": step_index,
                    "accepted": True,
                    **metrics,
                }
            )

            for node_id, district_id in partition.assignment.items():
                assignment_rows.append(
                    {
                        "run_id": run_id,
                        "step_index": step_index,
                        "node_id": node_id,
                        "district_id": district_id,
                    }
                )

            n_accepted += 1

        completed_at = datetime.now(tz=timezone.utc).isoformat()
        manifest = RunManifest(
            run_id=run_id,
            git_sha=git_sha,
            config=config,
            input_hashes={},
            started_at=started_at,
            completed_at=completed_at,
            n_accepted=n_accepted,
            n_rejected=0,
        )

        _build_run_outputs(tmp_dir, metrics_rows, assignment_rows, manifest)

        # Atomic rename: tmp → final
        tmp_dir.rename(final_dir)

    except Exception:
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)
        raise

    return final_dir
