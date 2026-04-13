"""
Shared constants and helper utilities for the gerrymandering analysis pipeline.

All path constants are derived from this file's location — never from cwd.
"""
import hashlib
import re
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------

PROJECT_ROOT: Path = Path(__file__).resolve().parents[1]
RAW: Path = PROJECT_ROOT / "data" / "raw"
PROCESSED: Path = PROJECT_ROOT / "data" / "processed"
OUTPUT: Path = PROJECT_ROOT / "output"

# ---------------------------------------------------------------------------
# CRS constant
# ---------------------------------------------------------------------------

_CRS_WGS84_CRS84: dict = {
    "type": "name",
    "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"},
}

# ---------------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------------


def normalize_subzone_name(name: Any) -> str:
    """Strip and uppercase a subzone name.

    Returns ``''`` for ``None``, ``float('nan')``, non-string values, or
    empty strings.  Ported from merge_census_and_geospatial.py lines 19-23.
    """
    if not isinstance(name, str):
        return ""
    return re.sub(r"\s+", " ", name.strip()).upper()


def ensure_crs(fc: dict) -> dict:
    """Return a new FeatureCollection dict with CRS injected if missing.

    If the input already contains a ``"crs"`` key the value is left
    unchanged.  The input dict is never mutated.
    """
    if "crs" in fc:
        return {**fc}
    return {**fc, "crs": _CRS_WGS84_CRS84}


def ensure_feature_ids(features: list[dict]) -> list[dict]:
    """Return a new list of feature dicts with ``_feature_id`` populated.

    Features that already carry a ``_feature_id`` value are kept as-is
    (returned as new dicts with identical contents so the caller's
    reference is not aliased).  Features without ``_feature_id`` are
    assigned sequential integers starting from 1, skipping any values
    already present in the input.

    Input dicts are never mutated.
    """
    # Collect the set of already-taken ids.
    taken: set[int] = set()
    for feat in features:
        fid = feat.get("_feature_id")
        if fid is not None:
            taken.add(fid)

    # Generator for collision-safe sequential ids.
    def _next_ids() -> Any:
        candidate = 1
        while True:
            if candidate not in taken:
                taken.add(candidate)
                yield candidate
            candidate += 1

    id_gen = _next_ids()

    result: list[dict] = []
    for feat in features:
        if "_feature_id" in feat:
            result.append(dict(feat))
        else:
            result.append({**feat, "_feature_id": next(id_gen)})
    return result


def file_sha256(path: Path) -> str:
    """Return the lowercase hex SHA-256 digest of the file at *path*.

    Reads the file in 64 KB chunks to keep memory usage bounded.
    Raises ``FileNotFoundError`` if the path does not exist.
    """
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()
