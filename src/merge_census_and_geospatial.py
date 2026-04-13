#!/usr/bin/env python3
"""
Merge Census 2020 subzone CSVs into master population table.
Validate URA subzone GeoJSON and join population to polygons.
Output: data/processed/master_population_subzone.csv, data/processed/subzone_with_population.geojson
"""
import csv
import json
import os
import re
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW = PROJECT_ROOT / "data" / "raw"
PROCESSED = PROJECT_ROOT / "data" / "processed"


def normalize_subzone_name(name: str) -> str:
    """Normalize subzone/planning area name for joining (uppercase, strip)."""
    if not name or not isinstance(name, str):
        return ""
    return name.strip().upper()


def load_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def merge_census_tables():
    """Merge the three Census 2020 subzone CSVs on Number (subzone name)."""
    census_dir = RAW / "census_2020_subzone"
    age_path = census_dir / "ResidentPopulationbyPlanningAreaSubzoneofResidenceAgeGroupandFloorAreaofResidenceCensusofPopulation2020.csv"
    dwelling_path = census_dir / "ResidentPopulationbyPlanningAreaSubzoneofResidenceandTypeofDwellingCensusofPopulation2020.csv"
    ethnic_path = census_dir / "ResidentPopulationbyPlanningAreaSubzoneofResidenceEthnicGroupandSexCensusofPopulation2020.csv"

    age = load_csv(age_path)
    dwelling = load_csv(dwelling_path)
    ethnic = load_csv(ethnic_path)

    # Key by normalized Number for merge; keep original Number as subzone_id
    def by_number(rows):
        return {normalize_subzone_name(r["Number"]): r for r in rows}

    age_by = by_number(age)
    dwelling_by = by_number(dwelling)
    ethnic_by = by_number(ethnic)

    all_keys = set(age_by) | set(dwelling_by) | set(ethnic_by)
    master = []
    for key in sorted(all_keys):
        if not key or key == "TOTAL":
            continue
        row = {"subzone_id": key}
        a = age_by.get(key, {})
        d = dwelling_by.get(key, {})
        e = ethnic_by.get(key, {})
        # Preserve original Number from first source
        row["Number"] = a.get("Number") or d.get("Number") or e.get("Number") or key
        # Add key demographics (avoid duplicate column names by prefixing)
        if a:
            raw_pop = a.get("Total1_Total", "")
            row["pop_total"] = 0 if raw_pop == "-" or raw_pop == "" else int(raw_pop)
            for k, v in a.items():
                if k != "Number":
                    row[f"age_floor_{k}"] = v
        if d:
            for k, v in d.items():
                if k != "Number":
                    row[f"dwelling_{k}"] = v
        if e:
            for k, v in e.items():
                if k != "Number":
                    row[f"ethnic_{k}"] = v
        master.append(row)
    return master


def write_master_csv(master: list[dict]):
    PROCESSED.mkdir(parents=True, exist_ok=True)
    if not master:
        return
    out_path = PROCESSED / "master_population_subzone.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=master[0].keys(), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(master)
    print(f"Wrote {out_path} ({len(master)} rows)")


def validate_and_join_geojson(master: list[dict]):
    """Load URA subzone GeoJSON, ensure unique IDs, join population, write cleaned GeoJSON."""
    geojson_path = RAW / "ura_subzone" / "MasterPlan2019SubzoneBoundaryNoSeaGEOJSON.geojson"
    with open(geojson_path, encoding="utf-8") as f:
        fc = json.load(f)

    # Build population lookup by normalized subzone name
    pop_by_name = {}
    for row in master:
        num = row.get("Number") or row.get("subzone_id", "")
        key = normalize_subzone_name(num)
        if key:
            pop_by_name[key] = row

    features = fc.get("features", [])
    seen_ids = set()
    for i, feat in enumerate(features):
        props = feat.get("properties") or {}
        # Ensure unique id
        obj_id = props.get("OBJECTID")
        if obj_id is None or obj_id in seen_ids:
            props["_feature_id"] = i + 1
            seen_ids.add(i + 1)
        else:
            props["_feature_id"] = obj_id
            seen_ids.add(obj_id)

        subzone_n = (props.get("SUBZONE_N") or "").strip().upper()
        if subzone_n and subzone_n in pop_by_name:
            pop_row = pop_by_name[subzone_n]
            props["pop_total"] = int(pop_row.get("pop_total", 0))
            props["subzone_census_id"] = pop_row.get("Number", "")
        else:
            props["pop_total"] = 0
            props["subzone_census_id"] = ""

    # Ensure CRS for GIS (WGS84)
    if "crs" not in fc:
        fc["crs"] = {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}}

    out_path = PROCESSED / "subzone_with_population.geojson"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(fc, f, indent=2, ensure_ascii=False)
    print(f"Wrote {out_path} ({len(features)} features)")


def main():
    master = merge_census_tables()
    write_master_csv(master)
    validate_and_join_geojson(master)


if __name__ == "__main__":
    main()
