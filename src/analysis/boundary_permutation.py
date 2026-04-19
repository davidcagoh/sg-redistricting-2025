"""
Boundary change permutation test for Singapore 2020→2025 redistricting.

Primary test (H&M-style): among the 114 subzones that changed constituency,
did those from competitive 2020 constituencies (PAP < 55%) systematically
avoid landing in competitive 2025 constituencies?

H0: Competitive-origin subzones are equally likely to land in competitive
    2025 destinations as any other changed subzone.
Test: Hypergeometric / Fisher's exact (one-sided).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats
from scipy.stats import hypergeom

# ── paths ────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[2]
CHANGES_CSV = ROOT / "output/electoral_profile/boundary_changes.csv"
CONS_2020_CSV = ROOT / "output/electoral_profile/constituencies_2020.csv"
CONS_2025_CSV = ROOT / "output/electoral_profile/constituencies_2025.csv"
OUT_DIR = ROOT / "output/electoral_profile/boundary_permutation"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── constants ─────────────────────────────────────────────────────────────────
CATEGORY_ORDER = ["marginal_pap", "safe_pap", "stronghold_pap", "walkover"]
CATEGORY_LABELS = {
    "marginal_pap": "Marginal PAP\n(<55%)",
    "safe_pap": "Safe PAP\n(55–65%)",
    "stronghold_pap": "Stronghold PAP\n(>65%)",
    "walkover": "Walkover\n(uncontested)",
}
CATEGORY_COLORS = {
    "marginal_pap": "#e8a838",
    "safe_pap": "#5b9bd5",
    "stronghold_pap": "#2e6fac",
    "walkover": "#888888",
}
FROM_ORDER = ["marginal_pap", "safe_pap", "stronghold_pap"]
FROM_LABELS = {
    "marginal_pap": "Competitive origin\n(PAP 50–55% in 2020)",
    "safe_pap": "Safe PAP origin\n(PAP 55–65% in 2020)",
    "stronghold_pap": "Stronghold origin\n(PAP >65% in 2020)",
}
FROM_COLORS = {
    "marginal_pap": "#d64e12",
    "safe_pap": "#5b9bd5",
    "stronghold_pap": "#2e6fac",
}


# ── load ──────────────────────────────────────────────────────────────────────
def load_data():
    df = pd.read_csv(CHANGES_CSV)
    df["from_pap_pct_2020"] = df["from_pap_pct_2020"].astype(float)
    df["to_pap_pct_2025"] = df["to_pap_pct_2025"].astype(float)
    df["pop_total_num"] = df["pop_total_num"].astype(float)
    df["delta_pap"] = df["to_pap_pct_2025"] - df["from_pap_pct_2020"]
    df["competitive_origin"] = df["from_category_2020"] == "marginal_pap"
    df["competitive_dest"] = df["to_category_2025"] == "marginal_pap"
    return df


# ── primary test: Fisher's exact / hypergeometric ────────────────────────────
def run_fisher_test(df: pd.DataFrame) -> dict:
    N = len(df)                                     # 114 total changed
    K = int(df["competitive_dest"].sum())           # competitive destinations
    n = int(df["competitive_origin"].sum())         # competitive origins
    x = int((df["competitive_origin"] & df["competitive_dest"]).sum())  # overlap

    # Fisher's exact (competitive origin less likely to reach competitive dest)
    table = [
        [x,         n - x],
        [K - x,     N - n - K + x],
    ]
    OR, p_fisher = stats.fisher_exact(table, alternative="less")
    expected = n * K / N

    # Full hypergeometric PMF for the figure
    k_vals = np.arange(0, min(n, K) + 1)
    pmf = hypergeom.pmf(k_vals, N, K, n)
    p_hyper = float(hypergeom.cdf(x, N, K, n))

    comp_names = sorted(df.loc[df["competitive_origin"], "ed_name_2020"].unique().tolist())
    dest_names = sorted(df.loc[df["competitive_dest"], "ed_name_2025"].unique().tolist())

    return {
        "N_total_changed": N,
        "K_competitive_destinations": K,
        "n_competitive_origins": n,
        "x_actual_overlap": x,
        "expected_overlap": round(expected, 2),
        "p_fisher_one_sided": round(p_fisher, 4),
        "p_hypergeometric": round(p_hyper, 4),
        "odds_ratio": float(OR),
        "competitive_origin_constituencies": comp_names,
        "competitive_dest_constituencies": dest_names,
        "contingency_table": {
            "comp_orig_comp_dest": x,
            "comp_orig_non_comp_dest": n - x,
            "non_comp_orig_comp_dest": K - x,
            "non_comp_orig_non_comp_dest": N - n - K + x,
        },
        "k_vals": k_vals.tolist(),
        "pmf": pmf.tolist(),
    }


# ── flow summary ──────────────────────────────────────────────────────────────
def compute_flow_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for from_cat in FROM_ORDER:
        sub = df[df["from_category_2020"] == from_cat]
        total_pop = sub["pop_total_num"].sum()
        for to_cat in CATEGORY_ORDER:
            s = sub[sub["to_category_2025"] == to_cat]
            rows.append({
                "from_category": from_cat,
                "to_category": to_cat,
                "n_subzones": len(s),
                "population": s["pop_total_num"].sum(),
                "pct_of_from_pop": s["pop_total_num"].sum() / total_pop * 100 if total_pop else 0,
            })
    return pd.DataFrame(rows)


# ── figure 1: hypergeometric distribution ────────────────────────────────────
def plot_hypergeometric(result: dict, out_path: Path):
    k_vals = np.array(result["k_vals"])
    pmf = np.array(result["pmf"])
    x_actual = result["x_actual_overlap"]
    expected = result["expected_overlap"]
    p = result["p_hypergeometric"]
    n = result["n_competitive_origins"]
    K = result["K_competitive_destinations"]
    N = result["N_total_changed"]

    fig, ax = plt.subplots(figsize=(9, 5.5))
    fig.patch.set_facecolor("#f8f8f8")
    ax.set_facecolor("#f8f8f8")

    colors = ["#d64e12" if k <= x_actual else "#5b9bd5" for k in k_vals]
    bars = ax.bar(k_vals, pmf, color=colors, edgecolor="white", linewidth=0.6, width=0.7)

    ax.axvline(expected, color="#333", linewidth=1.5, linestyle="--", alpha=0.75,
               label=f"Expected under H₀ = {expected:.1f}")

    ax.annotate(
        f"Actual = {x_actual}\n(p = {p:.3f})",
        xy=(x_actual, pmf[x_actual]),
        xytext=(x_actual + 0.6, pmf[x_actual] + 0.04),
        arrowprops=dict(arrowstyle="->", color="#d64e12", lw=1.5),
        color="#d64e12", fontsize=11, fontweight="bold",
    )

    ax.set_xlabel("Number of competitive-origin subzones landing in competitive 2025 constituencies", fontsize=11)
    ax.set_ylabel("Probability", fontsize=11)
    ax.set_title(
        "Hypergeometric null: how many competitive-origin subzones\n"
        "would land in competitive 2025 constituencies by chance?",
        fontsize=13, fontweight="bold", pad=14,
    )

    context = (
        f"Setup: {N} subzones changed constituency 2020→2025\n"
        f"{n} came from competitive 2020 constituencies (PAP <55%)\n"
        f"{K} changed subzones ended up in competitive 2025 constituencies\n"
        f"Competitive 2025 destinations: {', '.join(result['competitive_dest_constituencies'])}\n"
        f"Competitive 2020 origins: {', '.join(result['competitive_origin_constituencies'])}"
    )
    ax.text(0.98, 0.97, context, transform=ax.transAxes, fontsize=8.5,
            va="top", ha="right",
            bbox=dict(boxstyle="round,pad=0.4", facecolor="white", alpha=0.85))

    ax.legend(fontsize=10)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_xticks(k_vals)

    plt.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  → {out_path}")


# ── figure 2: flow bar chart ──────────────────────────────────────────────────
def plot_flow(flow: pd.DataFrame, out_path: Path):
    fig, axes = plt.subplots(1, 3, figsize=(13, 5.5), sharey=False)
    fig.patch.set_facecolor("#f8f8f8")
    fig.suptitle(
        "Where did changed subzones end up?\n"
        "Destination category (2025) by origin category (2020) — % of origin population",
        fontsize=12, fontweight="bold", y=1.02,
    )

    for ax, from_cat in zip(axes, FROM_ORDER):
        ax.set_facecolor("#f8f8f8")
        sub = flow[flow["from_category"] == from_cat].set_index("to_category").reindex(CATEGORY_ORDER).fillna(0)

        colors = [CATEGORY_COLORS[c] for c in CATEGORY_ORDER]
        bars = ax.bar(
            [CATEGORY_LABELS[c] for c in CATEGORY_ORDER],
            sub["pct_of_from_pop"],
            color=colors, edgecolor="white", linewidth=0.5,
        )
        for bar, (_, row) in zip(bars, sub.iterrows()):
            if row["pct_of_from_pop"] > 2:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 1.5,
                    f"{row['pct_of_from_pop']:.0f}%\n(n={int(row['n_subzones'])})",
                    ha="center", va="bottom", fontsize=8.5,
                )

        ax.set_title(FROM_LABELS[from_cat], fontsize=10.5, fontweight="bold",
                     color=FROM_COLORS[from_cat], pad=8)
        ax.set_ylabel("% of origin population" if from_cat == FROM_ORDER[0] else "", fontsize=10)
        ax.set_ylim(0, 115)
        ax.tick_params(axis="x", labelsize=8)
        ax.spines[["top", "right"]].set_visible(False)

    plt.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  → {out_path}")


# ── figure 3: scatter — origin PAP% vs delta ─────────────────────────────────
def plot_scatter(df: pd.DataFrame, out_path: Path):
    fig, ax = plt.subplots(figsize=(8, 5.5))
    fig.patch.set_facecolor("#f8f8f8")
    ax.set_facecolor("#f8f8f8")

    for from_cat in FROM_ORDER:
        sub = df[df["from_category_2020"] == from_cat]
        sizes = np.clip(sub["pop_total_num"] / 800, 10, 400)
        ax.scatter(
            sub["from_pap_pct_2020"] * 100,
            sub["delta_pap"] * 100,
            s=sizes, alpha=0.55,
            color=FROM_COLORS[from_cat],
            edgecolors="white", linewidths=0.4,
            label=FROM_LABELS[from_cat].replace("\n", " "),
        )

    ax.axhline(0, color="#333", linewidth=1, linestyle="--", alpha=0.5)
    ax.set_xlabel("2020 origin constituency PAP vote share (%)", fontsize=11)
    ax.set_ylabel("Shift: destination PAP 2025 − origin PAP 2020 (pp)", fontsize=11)
    ax.set_title(
        "Subzones from competitive 2020 constituencies moved to systematically safer seats\n"
        "(each point = one changed subzone; size ∝ population)",
        fontsize=11, fontweight="bold", pad=12,
    )
    r, p_val = stats.pearsonr(df["from_pap_pct_2020"], df["delta_pap"])
    ax.text(0.03, 0.97, f"Pearson r = {r:.3f}  (p = {p_val:.3f})", transform=ax.transAxes,
            fontsize=10, va="top",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))
    ax.legend(fontsize=9, loc="upper right")
    ax.spines[["top", "right"]].set_visible(False)

    plt.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  → {out_path}")


# ── figure 4: competitive seat geography shift ────────────────────────────────
def plot_seat_geography(out_path: Path):
    cons_2020 = pd.read_csv(CONS_2020_CSV)
    cons_2025 = pd.read_csv(CONS_2025_CSV)

    # PAP competitive = not opposition, PAP < 60%
    pap_2020 = cons_2020[(cons_2020["pap_pct"] < 0.60) & (cons_2020["political_category"] != "opposition")].copy()
    pap_2025 = cons_2025[(cons_2025["pap_pct"] < 0.60) & (cons_2025["political_category"] != "opposition")].copy()

    # Classify as survived (same name) or new
    names_2020 = set(pap_2020["constituency"])
    names_2025 = set(pap_2025["constituency"])
    pap_2020["status"] = pap_2020["constituency"].apply(
        lambda c: "survived" if c in names_2025 else "dissolved/merged"
    )
    pap_2025["status"] = pap_2025["constituency"].apply(
        lambda c: "survived" if c in names_2020 else "new"
    )

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5), sharey=False)
    fig.patch.set_facecolor("#f8f8f8")
    fig.suptitle(
        "Competitive PAP constituencies (PAP <60%): which survived and which are new?\n"
        "Opposition-held seats (Aljunied, Hougang, Sengkang) excluded",
        fontsize=12, fontweight="bold", y=1.02,
    )

    status_colors_2020 = {"survived": "#5b9bd5", "dissolved/merged": "#d64e12"}
    status_colors_2025 = {"survived": "#5b9bd5", "new": "#2ca02c"}

    for ax, df_sub, year, status_colors, title in [
        (axes[0], pap_2020, "2020", status_colors_2020,
         f"2020 competitive PAP constituencies (n={len(pap_2020)})"),
        (axes[1], pap_2025, "2025", status_colors_2025,
         f"2025 competitive PAP constituencies (n={len(pap_2025)})"),
    ]:
        ax.set_facecolor("#f8f8f8")
        df_sorted = df_sub.sort_values("pap_pct")
        colors = [status_colors[s] for s in df_sorted["status"]]
        bars = ax.barh(range(len(df_sorted)), df_sorted["pap_pct"] * 100,
                       color=colors, edgecolor="white", linewidth=0.5)
        ax.set_yticks(range(len(df_sorted)))
        ax.set_yticklabels(
            [c.title() for c in df_sorted["constituency"]], fontsize=9
        )
        ax.axvline(55, color="#e8a838", linewidth=1.2, linestyle="--", alpha=0.8,
                   label="55% threshold")
        ax.axvline(60, color="#888", linewidth=1, linestyle=":", alpha=0.7,
                   label="60% threshold")
        ax.set_xlabel("PAP vote share (%)", fontsize=10)
        ax.set_title(title, fontsize=11, fontweight="bold", pad=8)
        ax.set_xlim(40, 65)
        ax.spines[["top", "right"]].set_visible(False)

        # Legend patches
        patches = [
            plt.Rectangle((0, 0), 1, 1, color=c, label=lab)
            for lab, c in status_colors.items()
        ]
        ax.legend(handles=patches, fontsize=8.5, loc="lower right")

    plt.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  → {out_path}")


# ── main ──────────────────────────────────────────────────────────────────────
def main():
    print("Loading boundary change data...")
    df = load_data()
    print(f"  {len(df)} changed subzones")

    print("\nRunning Fisher's exact / hypergeometric test...")
    result = run_fisher_test(df)
    save_result = {k: v for k, v in result.items() if k not in ("k_vals", "pmf")}
    with open(OUT_DIR / "permutation_result.json", "w") as f:
        json.dump(save_result, f, indent=2)

    print(f"  Competitive origins: {result['n_competitive_origins']} subzones"
          f" from {result['competitive_origin_constituencies']}")
    print(f"  Competitive destinations: {result['K_competitive_destinations']} subzones"
          f" → {result['competitive_dest_constituencies']}")
    print(f"  Actual overlap: {result['x_actual_overlap']}  (expected: {result['expected_overlap']})")
    print(f"  p (Fisher's exact, one-sided): {result['p_fisher_one_sided']}")
    print(f"  p (hypergeometric CDF):        {result['p_hypergeometric']}")

    print("\nComputing flow summary...")
    flow = compute_flow_summary(df)
    flow.to_csv(OUT_DIR / "flow_summary.csv", index=False)

    print("\nGenerating plots...")
    plot_hypergeometric(result, OUT_DIR / "hypergeometric_test.png")
    plot_flow(flow, OUT_DIR / "destination_flow.png")
    plot_scatter(df, OUT_DIR / "origin_vs_delta.png")
    plot_seat_geography(OUT_DIR / "competitive_seat_geography.png")

    print("\nDone. Results in:", OUT_DIR)


if __name__ == "__main__":
    main()
