"""Constituency-level electoral and demographic analysis.

Builds a per-constituency dataset combining:
  - ELD vote results (2020, 2025)
  - Subzone demographic data (Census 2020)
  - Dwelling-type composition (HDB vs private, flat size)
  - MCMC-derived metrics for context

Outputs written to output/electoral_profile/:
  - constituencies_2020.csv
  - constituencies_2025.csv
  - malapportionment.csv
  - findings_summary.json
  - plots/
"""
from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
OUTPUT = ROOT / "output" / "electoral_profile"
OUTPUT.mkdir(parents=True, exist_ok=True)
(OUTPUT / "plots").mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Normalise constituency names (uppercase, strip whitespace)
# ---------------------------------------------------------------------------

def _norm(name: str) -> str:
    return str(name).strip().upper()


# ---------------------------------------------------------------------------
# 1. Load and process ELD vote results
# ---------------------------------------------------------------------------

_WALKOVERS = {
    # (year, constituency_norm): (type, seats, winner)
    (2025, "MARINE PARADE-BRADDELL HEIGHTS"): ("GRC", 5, "PAP"),
}


def load_eld_results(year: int) -> pd.DataFrame:
    """Return one row per constituency with PAP%, opposition%, seats, etc."""
    raw = json.loads((RAW / "eld_results_raw.json").read_text())
    recs = pd.DataFrame(raw["result"]["records"])
    recs = recs[recs["year"] == str(year)].copy()
    recs["vote_count"] = pd.to_numeric(recs["vote_count"], errors="coerce").fillna(0)
    recs["vote_percentage"] = pd.to_numeric(recs["vote_percentage"], errors="coerce").fillna(0)
    recs["seats"] = recs["candidates"].str.count(r"\|") + 1
    recs["constituency_norm"] = recs["constituency"].apply(_norm)

    rows = []
    for const, grp in recs.groupby("constituency_norm"):
        total_votes = grp["vote_count"].sum()
        seats = grp["seats"].iloc[0]
        ctype = grp["constituency_type"].iloc[0]

        # Identify PAP row
        pap = grp[grp["party"] == "PAP"]
        pap_votes = pap["vote_count"].sum() if len(pap) else 0
        pap_pct = pap["vote_percentage"].sum() if len(pap) else 0.0

        # Winner
        if len(grp) == 1:
            # Walkover
            winner = grp["party"].iloc[0]
            contested = False
        else:
            idx = grp["vote_count"].idxmax()
            winner = grp.loc[idx, "party"]
            contested = True

        opp_pct = 1.0 - pap_pct if contested else 0.0

        # Best opposition result (highest single opposition party %)
        opp_rows = grp[grp["party"] != "PAP"]
        best_opp_pct = opp_rows["vote_percentage"].max() if len(opp_rows) else 0.0
        best_opp_party = opp_rows.loc[opp_rows["vote_percentage"].idxmax(), "party"] if len(opp_rows) else ""

        rows.append({
            "constituency": const,
            "constituency_display": grp["constituency"].iloc[0],
            "type": ctype,
            "seats": seats,
            "contested": contested,
            "winner": winner,
            "pap_pct": float(pap_pct),
            "pap_votes": int(pap_votes),
            "best_opp_pct": float(best_opp_pct),
            "best_opp_party": best_opp_party,
            "total_valid_votes": int(total_votes),
            "voters_per_seat": total_votes / seats if seats > 0 else 0,
            "margin": float(pap_pct - best_opp_pct) if contested else 1.0,
            "year": year,
        })

    df = pd.DataFrame(rows).sort_values("constituency").reset_index(drop=True)

    # Add any walkovers missing from ELD dataset
    existing = set(df["constituency"].values)
    for (yr, const_norm), (ctype, seats, winner) in _WALKOVERS.items():
        if yr == year and const_norm not in existing:
            df = pd.concat([df, pd.DataFrame([{
                "constituency": const_norm,
                "constituency_display": const_norm.title(),
                "type": ctype,
                "seats": seats,
                "contested": False,
                "winner": winner,
                "pap_pct": 1.0,
                "pap_votes": 0,
                "best_opp_pct": 0.0,
                "best_opp_party": "",
                "total_valid_votes": 0,
                "voters_per_seat": 0,
                "margin": 1.0,
                "year": year,
            }])], ignore_index=True)

    return df


# ---------------------------------------------------------------------------
# 2. Load subzone demographics via node→constituency assignments
# ---------------------------------------------------------------------------

def load_subzone_demographics() -> pd.DataFrame:
    """Return per-subzone demographic stats, indexed by node_id."""
    gdf = gpd.read_file(PROCESSED / "subzone_with_population.geojson")
    pop = pd.read_csv(PROCESSED / "master_population_subzone.csv")

    # Normalise join keys
    pop["subzone_key"] = pop["subzone_id"].apply(_norm)
    gdf["subzone_key"] = gdf["SUBZONE_N"].apply(_norm)

    # Merge demographics onto GDF by subzone name
    merged = gdf.merge(
        pop[["subzone_key",
             "ethnic_Chinese_Total", "ethnic_Malays_Total",
             "ethnic_Indians_Total",
             "dwelling_HDBDwellings_Total",
             "dwelling_HDBDwellings_1_and2_RoomFlats1",
             "dwelling_HDBDwellings_3_RoomFlats",
             "dwelling_HDBDwellings_4_RoomFlats",
             "dwelling_HDBDwellings_5_RoomandExecutiveFlats",
             "dwelling_CondominiumsandOtherApartments",
             "dwelling_LandedProperties"]],
        on="subzone_key", how="left"
    )

    # Coerce to numeric
    numeric_cols = [
        "pop_total_num",
        "ethnic_Chinese_Total", "ethnic_Malays_Total", "ethnic_Indians_Total",
        "dwelling_HDBDwellings_Total",
        "dwelling_HDBDwellings_1_and2_RoomFlats1",
        "dwelling_HDBDwellings_3_RoomFlats",
        "dwelling_HDBDwellings_4_RoomFlats",
        "dwelling_HDBDwellings_5_RoomandExecutiveFlats",
        "dwelling_CondominiumsandOtherApartments",
        "dwelling_LandedProperties",
    ]
    for c in numeric_cols:
        if c in merged.columns:
            merged[c] = pd.to_numeric(merged[c], errors="coerce").fillna(0)

    merged["node_id"] = merged.index  # row index = node_id
    merged["SUBZONE_N"] = merged["SUBZONE_N"]
    merged["PLN_AREA_N"] = merged["PLN_AREA_N"]
    return merged[["node_id", "SUBZONE_N", "PLN_AREA_N"] + numeric_cols].copy()


def aggregate_demographics_by_constituency(
    assignments: pd.DataFrame,
    subzone_demo: pd.DataFrame,
) -> pd.DataFrame:
    """Aggregate subzone demographics to constituency level.

    Parameters
    ----------
    assignments : DataFrame with node_id, ed_name
    subzone_demo : DataFrame with node_id and demographic cols
    """
    merged = assignments.merge(subzone_demo, on="node_id", how="left")
    merged = merged[merged["ed_name"].notna()].copy()
    merged["constituency"] = merged["ed_name"].apply(_norm)

    # Sum raw counts per constituency
    num_cols = [
        "pop_total_num", "ethnic_Chinese_Total", "ethnic_Malays_Total",
        "ethnic_Indians_Total", "dwelling_HDBDwellings_Total",
        "dwelling_HDBDwellings_1_and2_RoomFlats1", "dwelling_HDBDwellings_3_RoomFlats",
        "dwelling_HDBDwellings_4_RoomFlats",
        "dwelling_HDBDwellings_5_RoomandExecutiveFlats",
        "dwelling_CondominiumsandOtherApartments", "dwelling_LandedProperties",
    ]
    agg = merged.groupby("constituency")[num_cols].sum().reset_index()

    # Derived shares
    pop = agg["pop_total_num"].replace(0, np.nan)
    agg["pct_chinese"] = agg["ethnic_Chinese_Total"] / pop * 100
    agg["pct_malay"] = agg["ethnic_Malays_Total"] / pop * 100
    agg["pct_indian"] = agg["ethnic_Indians_Total"] / pop * 100
    agg["pct_minority"] = (agg["ethnic_Malays_Total"] + agg["ethnic_Indians_Total"]) / pop * 100

    hdb = agg["dwelling_HDBDwellings_Total"].replace(0, np.nan)
    total_dwell = (
        agg["dwelling_HDBDwellings_Total"]
        + agg["dwelling_CondominiumsandOtherApartments"]
        + agg["dwelling_LandedProperties"]
    ).replace(0, np.nan)
    agg["pct_hdb"] = agg["dwelling_HDBDwellings_Total"] / total_dwell * 100
    agg["pct_private"] = (
        agg["dwelling_CondominiumsandOtherApartments"]
        + agg["dwelling_LandedProperties"]
    ) / total_dwell * 100
    agg["pct_small_hdb"] = (
        agg["dwelling_HDBDwellings_1_and2_RoomFlats1"]
        + agg["dwelling_HDBDwellings_3_RoomFlats"]
    ) / hdb * 100
    agg["pct_4room_hdb"] = agg["dwelling_HDBDwellings_4_RoomFlats"] / hdb * 100
    agg["pct_large_hdb"] = agg["dwelling_HDBDwellings_5_RoomandExecutiveFlats"] / hdb * 100

    return agg


# ---------------------------------------------------------------------------
# 3. Build full constituency dataset
# ---------------------------------------------------------------------------

def build_constituency_dataset(year: int) -> pd.DataFrame:
    results = load_eld_results(year)
    subzone_demo = load_subzone_demographics()
    asgn = pd.read_parquet(ROOT / "output" / "actual_assignments" / f"{year}.parquet")
    demo_agg = aggregate_demographics_by_constituency(asgn, subzone_demo)

    df = results.merge(demo_agg, on="constituency", how="left")

    # Political category
    def _cat(row):
        if not row["contested"]:
            return "walkover"
        if row["winner"] != "PAP":
            return "opposition"
        if row["pap_pct"] < 0.55:
            return "marginal_pap"
        if row["pap_pct"] < 0.65:
            return "safe_pap"
        return "stronghold_pap"

    df["political_category"] = df.apply(_cat, axis=1)
    return df


# ---------------------------------------------------------------------------
# 4. Malapportionment analysis
# ---------------------------------------------------------------------------

def malapportionment_analysis(df: pd.DataFrame, year: int) -> pd.DataFrame:
    """Compute seats-vs-votes and efficiency metrics.

    For multi-seat GRCs we treat each seat in a GRC as sharing the same
    vote pool, so 'votes per seat won' = total_party_votes / total_seats_won.
    """
    contested = df[df["contested"]].copy()
    all_df = df.copy()  # includes walkovers

    total_valid_votes = contested["total_valid_votes"].sum()

    # Seat counts (sum of seats in won constituencies, not constituency count)
    total_seats = int(all_df["seats"].sum())
    pap_seats = int(all_df[all_df["winner"] == "PAP"]["seats"].sum())
    opp_seats = int(all_df[all_df["winner"] != "PAP"]["seats"].sum())
    pap_seat_share = pap_seats / total_seats if total_seats else 0

    # Vote shares (contested only — walkovers have no votes)
    total_pap_votes = int(contested["pap_votes"].sum())
    pap_vote_share = total_pap_votes / total_valid_votes if total_valid_votes else 0

    # Votes per seat won: only count votes in constituencies the party WON
    pap_won = contested[contested["winner"] == "PAP"]
    opp_won = contested[contested["winner"] != "PAP"]
    pap_seats_contested = int(pap_won["seats"].sum())
    opp_seats_contested = int(opp_won["seats"].sum())
    # Opposition votes in won constituencies = total - pap_votes in those constituencies
    opp_votes_in_won = int((opp_won["total_valid_votes"] - opp_won["pap_votes"]).sum())
    pap_votes_in_won = int(pap_won["pap_votes"].sum())
    pap_votes_per_seat = pap_votes_in_won / pap_seats_contested if pap_seats_contested else 0
    opp_votes_per_seat = opp_votes_in_won / opp_seats_contested if opp_seats_contested else 0
    opp_votes = int(total_valid_votes - total_pap_votes)

    # Seat-vote gap: how many extra seat-share points does the leading party get
    # relative to its vote share (a direct measure of electoral bonus)
    seat_vote_gap = pap_seat_share - pap_vote_share

    # Efficiency gap — treat each GRC seat as an independent SMC equivalent
    # (standard approximation for block-voting systems)
    wasted_pap = 0
    wasted_opp = 0
    for _, row in contested.iterrows():
        seats = row["seats"]
        # Per-seat vote threshold: valid_votes / (2 * seats) + 1
        threshold = row["total_valid_votes"] / 2
        if row["winner"] == "PAP":
            wasted_pap += max(0, row["pap_votes"] - threshold)
            wasted_opp += row["total_valid_votes"] - row["pap_votes"]
        else:
            wasted_opp += max(0, (row["total_valid_votes"] - row["pap_votes"]) - threshold)
            wasted_pap += row["pap_votes"]

    efficiency_gap = (wasted_opp - wasted_pap) / total_valid_votes if total_valid_votes else 0

    summary = {
        "year": year,
        "total_seats": total_seats,
        "pap_seats": pap_seats,
        "opp_seats": opp_seats,
        "pap_seat_share": round(pap_seat_share, 4),
        "pap_vote_share_contested": round(pap_vote_share, 4),
        "seat_vote_gap": round(seat_vote_gap, 4),
        "pap_votes_per_seat_won": round(pap_votes_per_seat),
        "opp_votes_per_seat_won": round(opp_votes_per_seat),
        "votes_per_seat_ratio_opp_vs_pap": round(opp_votes_per_seat / pap_votes_per_seat, 3) if pap_votes_per_seat else None,
        "efficiency_gap": round(efficiency_gap, 4),
        "pap_wasted_votes": int(wasted_pap),
        "opp_wasted_votes": int(wasted_opp),
    }
    return pd.DataFrame([summary])


# ---------------------------------------------------------------------------
# 5. Correlation analysis
# ---------------------------------------------------------------------------

def correlation_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """Pearson correlations between opposition vote % and demographic variables."""
    contested = df[df["contested"] & df["pap_pct"].notna()].copy()
    opp_pct = (1 - contested["pap_pct"]) * 100

    demo_vars = [
        ("pct_malay", "% Malay"),
        ("pct_indian", "% Indian"),
        ("pct_minority", "% Minority (Malay+Indian)"),
        ("pct_hdb", "% HDB residents"),
        ("pct_small_hdb", "% Small HDB (≤3-room)"),
        ("pct_4room_hdb", "% 4-room HDB"),
        ("pct_large_hdb", "% Large HDB (≥5-room)"),
        ("pct_private", "% Private housing"),
        ("voters_per_seat", "Voters per seat"),
        ("seats", "Seats in constituency"),
    ]

    rows = []
    for col, label in demo_vars:
        if col not in contested.columns:
            continue
        x = pd.to_numeric(contested[col], errors="coerce")
        valid = x.notna() & opp_pct.notna()
        if valid.sum() < 5:
            continue
        r, p = stats.pearsonr(x[valid], opp_pct[valid])
        rows.append({
            "variable": label,
            "column": col,
            "pearson_r": round(r, 3),
            "p_value": round(p, 4),
            "n": int(valid.sum()),
            "significant": p < 0.05,
        })

    return pd.DataFrame(rows).sort_values("pearson_r", key=abs, ascending=False)


# ---------------------------------------------------------------------------
# 6. Constituency size vs political leanings
# ---------------------------------------------------------------------------

def size_vs_politics(df: pd.DataFrame) -> pd.DataFrame:
    contested = df[df["contested"]].copy()
    contested["opposition_pct"] = (1 - contested["pap_pct"]) * 100

    cat_order = ["stronghold_pap", "safe_pap", "marginal_pap", "opposition"]
    rows = []
    for cat in cat_order:
        sub = contested[contested["political_category"] == cat]
        if len(sub) == 0:
            continue
        rows.append({
            "category": cat,
            "n_constituencies": len(sub),
            "total_seats": int(sub["seats"].sum()),
            "mean_voters_per_seat": sub["voters_per_seat"].mean(),
            "median_voters_per_seat": sub["voters_per_seat"].median(),
            "mean_pct_malay": sub["pct_malay"].mean(),
            "mean_pct_indian": sub["pct_indian"].mean(),
            "mean_pct_minority": sub["pct_minority"].mean(),
            "mean_pct_hdb": sub["pct_hdb"].mean(),
            "mean_pct_small_hdb": sub["pct_small_hdb"].mean(),
            "mean_pct_private": sub["pct_private"].mean(),
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 7. Boundary changes 2020 → 2025
# ---------------------------------------------------------------------------

def boundary_changes(df20: pd.DataFrame | None = None, df25: pd.DataFrame | None = None) -> pd.DataFrame:
    """Find subzones that changed constituency between 2020 and 2025.

    Tags each move with the 2020 political category of the source constituency
    and the 2025 political category of the destination.
    """
    a20 = pd.read_parquet(ROOT / "output" / "actual_assignments" / "2020.parquet")
    a25 = pd.read_parquet(ROOT / "output" / "actual_assignments" / "2025.parquet")
    gdf = gpd.read_file(PROCESSED / "subzone_with_population.geojson")

    merged = a20.merge(a25, on="node_id", suffixes=("_2020", "_2025"))
    merged = merged.merge(
        gdf[["SUBZONE_N", "PLN_AREA_N", "pop_total_num"]].reset_index().rename(columns={"index": "node_id"}),
        on="node_id", how="left"
    )
    changed = merged[merged["ed_name_2020"] != merged["ed_name_2025"]].copy()
    changed["pop_total_num"] = pd.to_numeric(changed["pop_total_num"], errors="coerce").fillna(0)

    # Tag political category from 2020/2025 results
    if df20 is not None:
        cat20 = df20.set_index("constituency")[["political_category", "pap_pct"]].rename(
            columns={"political_category": "from_category_2020", "pap_pct": "from_pap_pct_2020"})
        changed["from_key"] = changed["ed_name_2020"].apply(_norm)
        changed = changed.merge(cat20, left_on="from_key", right_index=True, how="left")

    if df25 is not None:
        cat25 = df25.set_index("constituency")[["political_category", "pap_pct"]].rename(
            columns={"political_category": "to_category_2025", "pap_pct": "to_pap_pct_2025"})
        changed["to_key"] = changed["ed_name_2025"].apply(_norm)
        changed = changed.merge(cat25, left_on="to_key", right_index=True, how="left")

    changed = changed.sort_values("pop_total_num", ascending=False)
    base_cols = ["node_id", "SUBZONE_N", "PLN_AREA_N", "ed_name_2020", "ed_name_2025", "pop_total_num"]
    extra_cols = [c for c in ["from_category_2020", "from_pap_pct_2020", "to_category_2025", "to_pap_pct_2025"] if c in changed.columns]
    return changed[base_cols + extra_cols]


# ---------------------------------------------------------------------------
# 8. Plots
# ---------------------------------------------------------------------------

def _despine(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def plot_opposition_vs_voters_per_seat(df: pd.DataFrame, year: int) -> Path:
    contested = df[df["contested"]].copy()
    contested["opp_pct"] = (1 - contested["pap_pct"]) * 100
    contested["label"] = contested["constituency_display"]

    fig, ax = plt.subplots(figsize=(10, 7))
    colors = contested["political_category"].map({
        "opposition": "#e74c3c",
        "marginal_pap": "#f39c12",
        "safe_pap": "#3498db",
        "stronghold_pap": "#1a5276",
        "walkover": "#95a5a6",
    }).fillna("#95a5a6")

    ax.scatter(contested["voters_per_seat"], contested["opp_pct"],
               c=colors, s=contested["seats"] * 30, alpha=0.8, edgecolors="white", linewidth=0.5)

    # Label key constituencies
    for _, row in contested.iterrows():
        if row["opp_pct"] > 40 or row["opp_pct"] < 20 or row["voters_per_seat"] > 30000:
            ax.annotate(row["constituency_display"], (row["voters_per_seat"], row["opp_pct"]),
                        fontsize=7, alpha=0.85, xytext=(4, 2), textcoords="offset points")

    ax.axhline(50, color="grey", linestyle="--", linewidth=0.8, alpha=0.5)
    ax.set_xlabel("Voters per seat (total valid votes ÷ seats)", fontsize=11)
    ax.set_ylabel("Opposition vote %", fontsize=11)
    ax.set_title(f"{year}: Opposition vote % vs constituency size\n(bubble size = number of seats)", fontsize=12)
    _despine(ax)

    # Legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor="#e74c3c", label="Opposition win"),
        Patch(facecolor="#f39c12", label="Marginal PAP (<55%)"),
        Patch(facecolor="#3498db", label="Safe PAP (55–65%)"),
        Patch(facecolor="#1a5276", label="PAP stronghold (>65%)"),
    ]
    ax.legend(handles=legend_elements, loc="upper right", fontsize=8)

    out = OUTPUT / "plots" / f"opp_vs_size_{year}.png"
    fig.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


def plot_demographics_heatmap(df: pd.DataFrame, year: int) -> Path:
    contested = df[df["contested"]].copy()
    contested["opp_pct"] = (1 - contested["pap_pct"]) * 100

    demo_cols = ["pct_malay", "pct_indian", "pct_minority",
                 "pct_hdb", "pct_small_hdb", "pct_private"]
    labels = ["% Malay", "% Indian", "% Minority", "% HDB", "% Small HDB", "% Private"]

    corrs = []
    pvals = []
    for col in demo_cols:
        x = pd.to_numeric(contested[col], errors="coerce")
        valid = x.notna() & contested["opp_pct"].notna()
        if valid.sum() < 5:
            corrs.append(np.nan); pvals.append(np.nan)
            continue
        r, p = stats.pearsonr(x[valid], contested["opp_pct"][valid])
        corrs.append(r); pvals.append(p)

    fig, ax = plt.subplots(figsize=(9, 4))
    y = np.array(corrs)
    colors = ["#e74c3c" if v > 0 else "#3498db" for v in y]
    bars = ax.barh(labels, y, color=colors, edgecolor="white")
    ax.axvline(0, color="black", linewidth=0.8)
    for i, (val, p) in enumerate(zip(y, pvals)):
        sig = "**" if p < 0.01 else ("*" if p < 0.05 else "")
        ax.text(val + (0.01 if val >= 0 else -0.01), i, f"{val:.2f}{sig}",
                va="center", ha="left" if val >= 0 else "right", fontsize=9)
    ax.set_xlabel("Pearson r with opposition vote %", fontsize=11)
    ax.set_title(f"{year}: Demographic correlates of opposition vote share\n(* p<0.05, ** p<0.01)", fontsize=12)
    _despine(ax)
    out = OUTPUT / "plots" / f"demo_corr_{year}.png"
    fig.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


def plot_malapportionment(df20: pd.DataFrame, df25: pd.DataFrame) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    for ax, df, year in [(axes[0], df20, 2020), (axes[1], df25, 2025)]:
        contested = df[df["contested"]].copy()
        contested["opp_pct"] = (1 - contested["pap_pct"]) * 100
        bins = [0, 20000, 25000, 30000, 35000, 40000, 100000]
        labels_b = ["<20k", "20–25k", "25–30k", "30–35k", "35–40k", ">40k"]
        contested["size_bin"] = pd.cut(contested["voters_per_seat"], bins=bins, labels=labels_b)
        mean_opp = contested.groupby("size_bin", observed=True)["opp_pct"].mean()
        count = contested.groupby("size_bin", observed=True).size()

        bars = ax.bar(mean_opp.index, mean_opp.values, color="#3498db", edgecolor="white", alpha=0.85)
        for bar, c in zip(bars, count):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                    f"n={c}", ha="center", va="bottom", fontsize=8)
        ax.axhline(50, color="grey", linestyle="--", linewidth=0.8, alpha=0.6)
        ax.set_xlabel("Voters per seat", fontsize=10)
        ax.set_ylabel("Mean opposition vote %", fontsize=10)
        ax.set_title(f"{year}: Constituency size vs opposition support", fontsize=11)
        ax.set_ylim(0, 60)
        _despine(ax)

    out = OUTPUT / "plots" / "malapportionment_bins.png"
    fig.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


def plot_boundary_changes(changes: pd.DataFrame) -> Path:
    if changes.empty:
        return None
    top = changes.head(25)
    fig, ax = plt.subplots(figsize=(10, 8))
    y = range(len(top))
    colors = []
    for _, row in top.iterrows():
        colors.append("#e74c3c" if row["ed_name_2025"] != row["ed_name_2020"] else "#95a5a6")
    ax.barh(y, top["pop_total_num"] / 1000, color="#3498db", edgecolor="white", alpha=0.8)
    ax.set_yticks(list(y))
    labels = [f"{r.SUBZONE_N}\n{r.ed_name_2020} → {r.ed_name_2025}" for _, r in top.iterrows()]
    ax.set_yticklabels(labels, fontsize=7)
    ax.set_xlabel("Population (thousands)", fontsize=10)
    ax.set_title("Top subzones by population that changed constituency\n(2020 → 2025)", fontsize=11)
    _despine(ax)
    out = OUTPUT / "plots" / "boundary_changes.png"
    fig.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


# ---------------------------------------------------------------------------
# 9. GRC-specific analysis: minority representation vs strategic placement
# ---------------------------------------------------------------------------

def grc_minority_analysis(df: pd.DataFrame, year: int) -> dict:
    """Test whether GRC minority % significantly exceeds what random assignment produces."""
    grcs = df[(df["type"] == "GRC") & df["pct_minority"].notna()].copy()
    smcs = df[(df["type"] == "SMC") & df["pct_minority"].notna()].copy()

    grc_mean = grcs["pct_minority"].mean()
    smc_mean = smcs["pct_minority"].mean()

    t_stat, p_val = stats.ttest_ind(grcs["pct_minority"], smcs["pct_minority"])

    # Among GRCs: does minority % correlate with opposition support?
    grcs_contested = grcs[grcs["contested"]]
    grcs_contested["opp_pct"] = (1 - grcs_contested["pap_pct"]) * 100
    if len(grcs_contested) >= 5:
        r_opp, p_opp = stats.pearsonr(grcs_contested["pct_minority"], grcs_contested["opp_pct"])
    else:
        r_opp, p_opp = np.nan, np.nan

    # Are opposition-leaning GRCs larger (more voters per seat)?
    if len(grcs_contested) >= 5:
        r_size, p_size = stats.pearsonr(grcs_contested["pct_minority"], grcs_contested["voters_per_seat"])
    else:
        r_size, p_size = np.nan, np.nan

    return {
        "year": year,
        "n_grcs": len(grcs),
        "n_smcs": len(smcs),
        "grc_mean_minority_pct": round(grc_mean, 2),
        "smc_mean_minority_pct": round(smc_mean, 2),
        "grc_vs_smc_ttest_p": round(p_val, 4),
        "grc_vs_smc_significant": p_val < 0.05,
        "minority_vs_opp_r": round(r_opp, 3) if not np.isnan(r_opp) else None,
        "minority_vs_opp_p": round(p_opp, 4) if not np.isnan(p_opp) else None,
        "minority_vs_size_r": round(r_size, 3) if not np.isnan(r_size) else None,
        "minority_vs_size_p": round(p_size, 4) if not np.isnan(p_size) else None,
    }


# ---------------------------------------------------------------------------
# 10. Run everything and write outputs
# ---------------------------------------------------------------------------

def run() -> None:
    print("Building constituency datasets...")
    df20 = build_constituency_dataset(2020)
    df25 = build_constituency_dataset(2025)

    df20.to_csv(OUTPUT / "constituencies_2020.csv", index=False)
    df25.to_csv(OUTPUT / "constituencies_2025.csv", index=False)
    print(f"  2020: {len(df20)} constituencies, {df20['seats'].sum()} seats")
    print(f"  2025: {len(df25)} constituencies, {df25['seats'].sum()} seats")

    print("\nMalapportionment analysis...")
    mal20 = malapportionment_analysis(df20, 2020)
    mal25 = malapportionment_analysis(df25, 2025)
    mal = pd.concat([mal20, mal25])
    mal.to_csv(OUTPUT / "malapportionment.csv", index=False)
    print(mal.to_string(index=False))

    print("\nCorrelation analysis...")
    corr20 = correlation_analysis(df20)
    corr25 = correlation_analysis(df25)
    corr20.to_csv(OUTPUT / "correlations_2020.csv", index=False)
    corr25.to_csv(OUTPUT / "correlations_2025.csv", index=False)
    print("2020 top correlations:")
    print(corr20.head(8).to_string(index=False))
    print("\n2025 top correlations:")
    print(corr25.head(8).to_string(index=False))

    print("\nSize vs politics breakdown...")
    svp20 = size_vs_politics(df20)
    svp25 = size_vs_politics(df25)
    svp20.to_csv(OUTPUT / "size_vs_politics_2020.csv", index=False)
    svp25.to_csv(OUTPUT / "size_vs_politics_2025.csv", index=False)
    print("2020:")
    print(svp20[["category","n_constituencies","total_seats","mean_voters_per_seat","mean_pct_minority","mean_pct_hdb"]].to_string(index=False))
    print("2025:")
    print(svp25[["category","n_constituencies","total_seats","mean_voters_per_seat","mean_pct_minority","mean_pct_hdb"]].to_string(index=False))

    print("\nGRC minority analysis...")
    grc20 = grc_minority_analysis(df20, 2020)
    grc25 = grc_minority_analysis(df25, 2025)
    def _p(d): return json.dumps(d, indent=2, default=lambda x: bool(x) if isinstance(x, np.bool_) else str(x))
    print("2020:", _p(grc20))
    print("2025:", _p(grc25))

    print("\nBoundary changes 2020→2025...")
    changes = boundary_changes(df20, df25)
    changes.to_csv(OUTPUT / "boundary_changes.csv", index=False)
    print(f"  {len(changes)} subzones changed constituency")
    if len(changes):
        print(changes.head(15).to_string(index=False))

    print("\nGenerating plots...")
    plot_opposition_vs_voters_per_seat(df20, 2020)
    plot_opposition_vs_voters_per_seat(df25, 2025)
    plot_demographics_heatmap(df20, 2020)
    plot_demographics_heatmap(df25, 2025)
    plot_malapportionment(df20, df25)
    plot_boundary_changes(changes)

    # Save summary findings JSON
    findings = {
        "malapportionment": {
            "2020": mal20.to_dict(orient="records")[0],
            "2025": mal25.to_dict(orient="records")[0],
        },
        "grc_minority": {"2020": grc20, "2025": grc25},
        "correlations": {
            "2020": corr20.to_dict(orient="records"),
            "2025": corr25.to_dict(orient="records"),
        },
        "size_vs_politics": {
            "2020": svp20.to_dict(orient="records"),
            "2025": svp25.to_dict(orient="records"),
        },
        "boundary_changes": {
            "n_subzones_changed": len(changes),
            "top_changes": changes.head(20).to_dict(orient="records"),
        },
    }
    def _json_safe(obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, (np.bool_,)):
            return bool(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return str(obj)

    (OUTPUT / "findings_summary.json").write_text(json.dumps(findings, indent=2, default=_json_safe))
    print(f"\nAll outputs written to {OUTPUT}")


if __name__ == "__main__":
    run()
