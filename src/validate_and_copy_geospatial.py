#!/usr/bin/env python3
"""
Copy raw GeoJSON to data/processed with CRS and unique _feature_id where needed.
Electoral 2020/2025 already have CRS84 and FID; URA subzone handled in merge script.
"""
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW = PROJECT_ROOT / "data" / "raw"
PROCESSED = PROJECT_ROOT / "data" / "processed"


def ensure_crs_and_id(path: Path, out_name: str) -> None:
    with open(path, encoding="utf-8") as f:
        fc = json.load(f)
    if "crs" not in fc:
        fc["crs"] = {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}}
    for i, feat in enumerate(fc.get("features", [])):
        p = feat.get("properties") or {}
        if "FID" not in p and "_feature_id" not in p:
            p["_feature_id"] = i + 1
        feat["properties"] = p
    PROCESSED.mkdir(parents=True, exist_ok=True)
    out = PROCESSED / out_name
    with open(out, "w", encoding="utf-8") as f:
        json.dump(fc, f, indent=2, ensure_ascii=False)
    print(f"Wrote {out} ({len(fc.get('features', []))} features)")


def main():
    ensure_crs_and_id(RAW / "electoral_boundaries" / "ElectoralBoundary2020GEOJSON.geojson", "electoral_boundaries_2020.geojson")
    ensure_crs_and_id(RAW / "electoral_boundaries" / "ElectoralBoundary2025GEOJSON.geojson", "electoral_boundaries_2025.geojson")


if __name__ == "__main__":
    main()
