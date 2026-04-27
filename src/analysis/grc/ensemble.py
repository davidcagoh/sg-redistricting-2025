"""Variable-size GRC/SMC ensemble driver (paper 2).

Orchestrates the full pipeline for one run:
  load data → build graph → variable-size seed → chain → sample → write outputs.

Output layout::

    data/processed/ensemble/grc/<run_id>/
        metrics.parquet       – one row per post-burn-in step
        assignments.parquet   – long format: (run_id, step_index, node_id, district_id)
        manifest.json         – provenance record
"""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src.analysis.config import PathsConfig, RunManifest, get_git_sha, manifest_to_dict
from src.analysis.ensemble import build_pipeline_inputs
from src.analysis.graph_build import attach_pct_minority
from src.analysis.grc.config import GRCConfig
from src.analysis.io_layer import load_ethnic_data
from src.analysis.grc.metrics import compute_grc_metrics
from src.analysis.grc.recom import build_grc_partition, build_variable_recom_proposal
from src.analysis.grc.seed_partition import make_grc_seed_partition
from src.analysis.metrics.registry import compute_all


def _grc_run_id(config: GRCConfig) -> str:
    if config.run_id:
        return config.run_id
    timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%S")
    sha = get_git_sha()
    return f"grc_{timestamp}-{sha}"


def run_grc_ensemble(config: GRCConfig, paths: PathsConfig) -> Path:
    """Run one variable-size GRC/SMC ensemble and write outputs.

    The run directory is placed under data/processed/ensemble/grc/<run_id>/
    to keep paper-2 outputs cleanly separate from paper-1 outputs.

    Parameters
    ----------
    config:
        GRC ensemble hyperparameters including district_types seat vector.
    paths:
        Filesystem paths (reuses PathsConfig from paper-1 pipeline).

    Returns
    -------
    Path
        The final run directory.

    Raises
    ------
    FileExistsError
        If the final run directory already exists.
    """
    run_id = _grc_run_id(config)
    final_dir = paths.processed_dir / "ensemble" / "grc" / run_id
    tmp_dir = Path(str(final_dir) + ".tmp")

    if final_dir.exists():
        raise FileExistsError(
            f"GRC ensemble run directory already exists: {final_dir}"
        )
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)

    tmp_dir.mkdir(parents=True, exist_ok=True)
    started_at = datetime.now(tz=timezone.utc).isoformat()
    git_sha = get_git_sha()

    try:
        graph, _filtered_gdf, subzone_geoms = build_pipeline_inputs(paths)
        attach_pct_minority(graph, load_ethnic_data())

        seat_counts = config.seat_counts_by_id()
        total_pop = sum(graph.nodes[n]["pop_total"] for n in graph.nodes)

        seed_assignment = make_grc_seed_partition(graph, config)
        initial_partition = build_grc_partition(graph, seed_assignment, config)

        proposal = build_variable_recom_proposal(
            graph, config, seat_counts, total_pop
        )

        # Constraint: population balance is enforced inside the proposal itself
        # (each piece checked against its per-district target). We add only
        # contiguity here as an external hard constraint on the MarkovChain.
        from gerrychain import MarkovChain
        from gerrychain.constraints import contiguous

        chain = MarkovChain(
            proposal=proposal,
            constraints=[contiguous],
            accept=lambda _p: True,
            initial_state=initial_partition,
            total_steps=config.n_steps,
        )

        metrics_rows: list[dict] = []
        assignment_rows: list[dict] = []
        n_accepted = 0

        for step_index, partition in enumerate(chain):
            if step_index < config.burn_in:
                continue

            # Paper-1 metrics (community splitting, compactness, population)
            base_metrics = compute_all(
                partition.parts, subzone_geoms, graph, partition.assignment
            )

            # Paper-2 metrics (minority capture, GRC/SMC type geography)
            grc_metrics = compute_grc_metrics(partition.parts, graph, seat_counts)

            metrics_rows.append(
                {
                    "run_id": run_id,
                    "step_index": step_index,
                    **base_metrics,
                    **grc_metrics,
                }
            )

            for node_id, district_id in partition.assignment.items():
                assignment_rows.append(
                    {
                        "run_id": run_id,
                        "step_index": step_index,
                        "node_id": node_id,
                        "district_id": district_id,
                        "seat_count": seat_counts[district_id],
                    }
                )

            n_accepted += 1

        completed_at = datetime.now(tz=timezone.utc).isoformat()

        # Reuse RunManifest — config stored as a plain dict since GRCConfig
        # is not directly JSON-serialisable via asdict.
        manifest_data = {
            "run_id": run_id,
            "pipeline": "grc_ensemble_v1",
            "git_sha": git_sha,
            "config": {
                "district_types": [
                    {"seat_count": dt.seat_count, "num_districts": dt.num_districts}
                    for dt in config.district_types
                ],
                "k_districts": config.k_districts,
                "total_seats": config.total_seats,
                "pop_tolerance": config.pop_tolerance,
                "n_steps": config.n_steps,
                "burn_in": config.burn_in,
                "seed": config.seed,
                "recom_epsilon": config.recom_epsilon,
            },
            "started_at": started_at,
            "completed_at": completed_at,
            "n_steps_collected": n_accepted,
        }

        metrics_df = pd.DataFrame(metrics_rows) if metrics_rows else pd.DataFrame()
        assignment_df = pd.DataFrame(assignment_rows) if assignment_rows else pd.DataFrame()

        metrics_df.to_parquet(tmp_dir / "metrics.parquet", index=False)
        assignment_df.to_parquet(tmp_dir / "assignments.parquet", index=False)
        (tmp_dir / "manifest.json").write_text(
            json.dumps(manifest_data, indent=2, sort_keys=True) + "\n"
        )

        tmp_dir.rename(final_dir)

    except Exception:
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)
        raise

    return final_dir
