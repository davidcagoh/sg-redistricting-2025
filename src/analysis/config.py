"""
Configuration dataclasses and helpers for the MCMC ensemble pipeline.

All config objects are frozen dataclasses (immutable). Helper functions
handle run ID generation, manifest serialisation, and disk persistence.
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.utils import OUTPUT, PROCESSED, RAW

# ---------------------------------------------------------------------------
# Config dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EnsembleConfig:
    """Hyperparameters for a single MCMC ensemble run."""

    k_districts: int = 33
    pop_tolerance: float = 0.10
    n_steps: int = 10_000
    burn_in: int = 1_000
    seed: int = 42
    recom_epsilon: float = 0.05
    recom_node_repeats: int = 2
    max_attempts_per_step: int = 100
    run_id: str = ""


@dataclass(frozen=True)
class PathsConfig:
    """Filesystem paths used by the pipeline."""

    processed_dir: Path
    raw_dir: Path
    output_dir: Path

    def ensemble_dir(self, run_id: str) -> Path:
        """Return the directory for a specific ensemble run's outputs."""
        return self.processed_dir / "ensemble" / run_id


@dataclass(frozen=True)
class RunManifest:
    """Immutable record written at the end of each ensemble run."""

    run_id: str
    git_sha: str
    config: EnsembleConfig
    input_hashes: dict
    started_at: str
    completed_at: str
    n_accepted: int = 0
    n_rejected: int = 0
    metrics_version: str = "1"


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def get_git_sha() -> str:
    """Return the short git SHA of HEAD, or ``"unknown"`` if git is unavailable."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"


def make_run_id(config: EnsembleConfig) -> str:
    """Return the run ID to use for *config*.

    If ``config.run_id`` is non-empty it is returned verbatim.
    Otherwise a fresh ID is generated from the current UTC timestamp
    and the current git SHA.
    """
    if config.run_id:
        return config.run_id
    timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%S")
    sha = get_git_sha()
    return f"{timestamp}-{sha}"


def manifest_to_dict(manifest: RunManifest) -> dict[str, Any]:
    """Convert *manifest* to a plain, JSON-serialisable dict.

    All :class:`pathlib.Path` values are converted to strings.
    Nested dataclasses are recursively converted via :func:`dataclasses.asdict`.
    """
    raw = asdict(manifest)
    return _paths_to_str(raw)


def write_manifest(manifest: RunManifest, path: Path) -> None:
    """Serialise *manifest* as pretty-printed JSON to *path*.

    Parent directories are created automatically if they do not exist.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    data = manifest_to_dict(manifest)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _paths_to_str(obj: Any) -> Any:
    """Recursively convert :class:`pathlib.Path` objects to strings."""
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, dict):
        return {k: _paths_to_str(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        converted = [_paths_to_str(v) for v in obj]
        return type(obj)(converted)
    return obj
