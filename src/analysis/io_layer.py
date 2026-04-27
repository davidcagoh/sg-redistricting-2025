"""Schema-validated loaders for all spatial and tabular data layers.

Each loader returns a new object on every call — no global caching, no mutation.
PROCESSED and RAW are module-level names so tests can monkeypatch them.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import geopandas as gpd
import pandas as pd

from src.utils import PROCESSED, RAW, normalize_subzone_name

# Re-export so tests can monkeypatch at the module level
PROCESSED = PROCESSED  # noqa: PLW0127
RAW = RAW  # noqa: PLW0127

_SUBZONE_FILE = "subzone_with_population.geojson"
_ELECTORAL_FILES = {
    2020: "electoral_boundaries_2020.geojson",
    2025: "electoral_boundaries_2025.geojson",
}
_HDB_BUILDINGS_FILE = "HDBExistingBuilding.geojson"
_HDB_PROPERTY_FILE = "HDBPropertyInformation.csv"
_ETHNIC_FILE = (
    "census_2020_subzone/"
    "ResidentPopulationbyPlanningAreaSubzoneofResidenceEthnicGroupandSexCensusofPopulation2020.csv"
)

_SVY21_EPSG = 3414


@dataclass(frozen=True)
class SubzoneLayer:
    """Subzone GeoDataFrame in two CRS variants."""

    wgs84: gpd.GeoDataFrame  # original WGS84 / CRS84
    svy21: gpd.GeoDataFrame  # EPSG:3414 (Singapore SVY21) for area and adjacency ops


def load_subzones_with_population() -> SubzoneLayer:
    """Load processed subzone polygons with Census 2020 population.

    Validates required columns and CRS. Adds ``subzone_name_norm`` (uppercase,
    whitespace-collapsed). Returns both WGS84 and SVY21 projections.

    Raises
    ------
    FileNotFoundError
        If the processed file is absent; message mentions the upstream script.
    """
    path: Path = PROCESSED / _SUBZONE_FILE
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run merge_census_and_geospatial.py to generate it."
        )

    gdf: gpd.GeoDataFrame = gpd.read_file(path)

    required = {"SUBZONE_N", "PLN_AREA_N", "pop_total"}
    missing = required - set(gdf.columns)
    if missing:
        raise ValueError(f"subzone GeoJSON missing required columns: {missing}")

    gdf = gdf.assign(
        subzone_name_norm=gdf["SUBZONE_N"].map(normalize_subzone_name)
    )

    wgs84 = gdf.copy()
    svy21 = gdf.to_crs(epsg=_SVY21_EPSG)

    return SubzoneLayer(wgs84=wgs84, svy21=svy21)


def load_electoral_boundaries(year: int) -> gpd.GeoDataFrame:
    """Load processed electoral division polygons for the given election year.

    Parameters
    ----------
    year:
        Must be 2020 or 2025.

    Raises
    ------
    ValueError
        For unsupported years.
    FileNotFoundError
        If the processed file is absent; message mentions the upstream script.
    """
    if year not in _ELECTORAL_FILES:
        raise ValueError(
            f"Unsupported year {year!r}. Must be 2020 or 2025."
        )

    path: Path = PROCESSED / _ELECTORAL_FILES[year]
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run validate_and_copy_geospatial.py to generate it."
        )

    gdf: gpd.GeoDataFrame = gpd.read_file(path)

    if "ED_DESC" not in gdf.columns and "Name" not in gdf.columns:
        raise ValueError(
            f"Electoral {year} GeoJSON has neither 'ED_DESC' nor 'Name' column."
        )

    return gdf


def load_hdb_buildings() -> gpd.GeoDataFrame:
    """Load HDB existing building footprint polygons.

    Returns the GeoDataFrame in its native CRS (caller reprojects if needed).

    Raises
    ------
    FileNotFoundError
        If the raw file is absent.
    """
    path: Path = RAW / "hdb" / _HDB_BUILDINGS_FILE
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Place HDBExistingBuilding.geojson in data/raw/hdb/."
        )

    gdf: gpd.GeoDataFrame = gpd.read_file(path)

    if len(gdf) == 0:
        raise ValueError("HDB buildings GeoJSON loaded but contains zero features.")

    # Normalise column names to lowercase
    gdf.columns = [c.lower() for c in gdf.columns]

    return gdf


def load_hdb_property_table() -> pd.DataFrame:
    """Load HDB property information CSV.

    Normalises ``bldg_contract_town`` to uppercase and stripped. Returns a
    new DataFrame on every call.

    Raises
    ------
    FileNotFoundError
        If the raw file is absent.
    ValueError
        If required columns are missing.
    """
    path: Path = RAW / "hdb" / _HDB_PROPERTY_FILE
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Place HDBPropertyInformation.csv in data/raw/hdb/."
        )

    df: pd.DataFrame = pd.read_csv(path, dtype=str)

    required = {"blk_no", "street", "bldg_contract_town"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"HDB property CSV missing required columns: {missing}")

    df = df.assign(
        bldg_contract_town=df["bldg_contract_town"]
        .str.strip()
        .str.upper()
    )

    return df


def load_ethnic_data() -> dict[str, float]:
    """Load Census 2020 ethnic breakdown and return pct_minority by subzone.

    ``pct_minority`` is defined as (Malays + Indians + Others) / Total.

    Rows representing planning-area totals (containing " - Total") and the
    national aggregate row ("Total") are excluded.  Subzones with suppressed
    data ("-") in any ethnic column are assigned ``pct_minority = 0.0``.

    Returns
    -------
    dict[str, float]
        Mapping from normalized subzone name (uppercase, stripped) to
        ``pct_minority`` in [0.0, 1.0].  Keys match the ``subzone_name_norm``
        node attribute produced by ``build_subzone_graph``.

    Raises
    ------
    FileNotFoundError
        If the raw ethnic CSV is absent.
    ValueError
        If required columns are missing.
    """
    path: Path = RAW / _ETHNIC_FILE
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Expected Census 2020 ethnic subzone CSV."
        )

    df: pd.DataFrame = pd.read_csv(path, dtype=str)

    required = {"Number", "Total_Total", "Malays_Total", "Indians_Total", "Others_Total"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Ethnic CSV missing required columns: {missing}")

    # Drop national total and planning-area subtotal rows
    df = df[
        (df["Number"] != "Total")
        & (~df["Number"].str.contains(" - Total", na=False))
    ].copy()

    numeric_cols = ["Total_Total", "Malays_Total", "Indians_Total", "Others_Total"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    df["pct_minority"] = df.apply(
        lambda r: (
            (r["Malays_Total"] + r["Indians_Total"] + r["Others_Total"]) / r["Total_Total"]
            if r["Total_Total"] > 0
            else 0.0
        ),
        axis=1,
    )

    return {
        normalize_subzone_name(row["Number"]): float(row["pct_minority"])
        for _, row in df.iterrows()
    }
