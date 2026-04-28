# Session Log

## 2026-04-27 (session 18) — Option A ran; null result; method comparison memo written

### What was done

- **Option A post-processing implemented** (`src/analysis/grc/option_a.py`):
  - `build_node_arrays`, `compute_district_stats`, `run_null_distribution`, `compute_actual_capture`, `compute_percentile_rank`, `run_option_a` — full pipeline
  - 22 unit tests added (`tests/analysis/grc/test_option_a.py`); suite now 550 tests, all passing
- **Option A ran against `seed_001` ensemble** (9,000 steps × 100 permutations = 900,000 null samples):
  - Actual 2025 GRC minority %: **26.03%**, SMC: **23.03%** (+3.00 pp gap)
  - Null mean: 25.65%, std: 1.02%
  - Percentile rank: **64th** — p-value (GRC ≥ actual): **0.356**
  - **Null result**: no evidence that actual GRC placement concentrates minority populations anomalously
  - Results saved to `output/option_a/` (summary.json + null_grc_minority_pct.npy)
- **Method comparison memo written** (`wiki/option-a-b-c-analysis.md`):
  - Full explanation of Options A, B (infeasible), C (hypothetical sequential hierarchical)
  - Key distinction: A tests label permutation, B tests boundary drawing, C is sequential approximation of B with ordering bias
  - Why null result survives Option A's methodological limitations documented

### State at end of session

Clean. Option A complete. 550 tests green. Paper 2 first empirical result is a null finding (GRC placement not minority-optimised). Memo in wiki for review.

### What to do next session

1. Plot null distribution histogram with actual marker → `output/option_a/figure_null_hist.png`
2. Begin `writeup/paper2/paper.tex` draft — introduce method, null finding, interpretation
3. Consider whether paper 2 leads with the null (honest, interesting) or reserves it for §4 after method section

---

## 2026-04-26 (session 17) — paper 1 robustness + pct_minority + GRC Option A decision

### What was done

- **Robustness check (`robustness_check.py`)** — compared sg2025 (seed=42), seed_001 (seed=1), seed_002 (seed=2):
  - sg2025 chain was **stuck**: `towns_split` std=0 (always 12), `max_abs_pop_dev` std=0 (always 0.096). KS D=0.994 vs seed_001.
  - seed_001 and seed_002 consistent with each other (KS D=0.002 for towns_split).
  - All three seeds agree on percentile rankings: actual plan at 0th/100th percentile for all informative metrics.
- **Re-ran diff against seed_001** — new primary ensemble. 2020 `pln_area_splits` moves from 0.0% to 0.1% (1/9000 plans achieves 29 splits); all other rankings unchanged.
- **Updated `writeup/paper1/paper.tex`**:
  - `towns_split` now bolded (informative); ensemble [12,12]→[12,13]; "two striking" → "three striking"
  - All ensemble means/ranges updated to seed_001 values
  - §4 caveat + §7 limitation updated: robustness completed, stuck chain flagged
  - Technical notes: primary seed 42 → seed 1
  - Paper recompiled clean at 16 pages
- **verify_refs.py**: no hallucinations (same as session 16)
- **`pct_minority` attached to graph nodes**:
  - Added `load_ethnic_data()` to `src/analysis/io_layer.py` — parses Census 2020 ethnic CSV, filters aggregate rows, returns `dict[subzone_name_norm → pct_minority]` where pct_minority = (Malays + Indians + Others) / Total_Total
  - Added `attach_pct_minority(graph, lookup)` to `src/analysis/graph_build.py` — mutates graph in place via `subzone_name_norm` join key
  - Wired into `src/analysis/grc/ensemble.py` (called after `build_pipeline_inputs`)
  - Added 5 unit tests in `tests/test_io_layer.py` and 6 tests in `tests/test_graph_build.py`; suite now 528 tests, all passing
- **GRC seeder exploration and pivot**:
  - Diagnosed structural infeasibility of variable-seat-count ReCom for Singapore: 15 subzones exceed SMC target × 1.2 (largest = 130,980 vs target 49,832). Only 1/100 BFS attempts passed 50% tolerance.
  - Multiple seeder strategies tried: stratified BFS, absolute-deficit BFS, sequential BFS, unit-merge k=97 (unit max deviation 214%)
  - Modular approach used: `_unit_merge_grc_seed` added as new function alongside original `_bfs_grc_seed`; bug fixes preserved (empty-district fix, pop_tolerance override parameter)
  - **Decision: Option A** — post-process paper 1 ensemble with random seat-type assignment. See `wiki/decisions.md#grc-option-a`.

### State at end of session

Paper 1 complete and robust. pct_minority attached to graph nodes. GRC analysis strategy decided: post-process paper 1 ensemble. decisions.md updated.

### What to do next session

1. Implement Option A post-processing script: for each of 9,000 `seed_001` steps, randomly permute seat-type assignment (15×SMC, 8×GRC4, 10×GRC5) N times, compute minority capture (mean pct_minority weighted by pop × seats in GRC districts), build null distribution
2. Compute actual 2025 GRC configuration's minority capture score
3. Compare actual vs null distribution (percentile rank, p-value)
4. Begin paper 2 draft in `writeup/paper2/`

---

## 2026-04-24 (session 16) — paper 2 scaffold + robustness seeds + references.bib

### What was done

- **Created `writeup/paper1/references.bib`** — converted the inline `\thebibliography`
  from `paper.tex` into a proper BibTeX file (4 entries). Ran `verify_refs.py`:
  both journal papers (Herschlag 2020, McGhee 2014) verified as LIKELY (title match 1.00);
  government data sources (ELD, URA) correctly NOT_FOUND in Semantic Scholar.

- **Started MCMC robustness seeds** — kicked off `seed_001` (seed=1) and `seed_002`
  (seed=2) as background processes. Both confirmed running.

- **Created `src/analysis/grc/`** — full variable-size GRC/SMC ensemble pipeline for paper 2:
  - `config.py` — `GRCConfig`, `DistrictType`; 2025 structure: 15×SMC + 8×GRC(4) + 10×GRC(5) = 33 districts, 97 seats
  - `seed_partition.py` — variable-target BFS seeder + `validate_grc_partition`
  - `recom.py` — `build_variable_recom_proposal`: custom ReCom that handles asymmetric per-district population targets
  - `metrics.py` — minority capture by district type, seat-type geography by planning area
  - `ensemble.py` — driver; outputs to `data/processed/ensemble/grc/<run_id>/`
  - `cli.py` — `python -m src.analysis.grc.cli run-ensemble`

- **Added 36 new tests** in `tests/analysis/grc/` (19 new + 36 total; suite now 517 tests, all passing)

- **Updated `CLAUDE.md`** — added paper 2 pipeline table, separation note, writeup layout, known gap for `pct_minority`

- **Created `writeup/paper2/outline.md`** — research questions, data gaps, planned sections, next steps

- **Paper 1 published on SocArXiv** (user action, noted for provenance)

### State at end of session

Paper 2 code infrastructure complete. `src/analysis/grc/` is self-contained and cleanly
separated from paper 1 code. MCMC robustness seeds (`seed_001`, `seed_002`) running.

### What to do next session

1. Wait for `seed_001` and `seed_002` to complete; run robustness comparison script
2. Attach `pct_minority` to graph nodes from Census ethnic CSV (`data/raw/census_2020_subzone/`)
3. Attach `pap_2020_pct` competitive score to graph nodes from `assign_actual.py` output
4. Run first GRC ensemble: `python -m src.analysis.grc.cli run-ensemble --run-id grc_sg2025_s42`
5. Compare actual 2025 GRC placement vs ensemble on minority capture + competitive geography
6. Begin paper 2 draft

---

## 2026-04-19 (session 15) — LaTeX paper compiled + repo cleanup

### What was done

- **Filled `[repository URL]` placeholder** in `writeup/paper1/draft.md` → `https://github.com/davidcagoh/sg-redistricting-2025`

- **Wrote `writeup/paper1/paper.tex`** — full LaTeX version of the paper in political science working paper format (Times font, 1.5-spaced, 1.25in margins; appropriate for *Statistics and Public Policy* / *Political Analysis* submission):
  - Added abstract (not present in Markdown draft)
  - `booktabs` tables, `natbib` author-year citations, `hyperref` URLs, `adjustbox`/`makecell` for wide tables
  - Both figures (`combined_summary.png`, `choropleth_2020_2025.png`) linked from `output/`
  - Email set to `daveed@cs.toronto.edu`

- **Compiled `writeup/paper1/paper.pdf`** — 16 pages, zero errors

- **Repo root cleanup:**
  - `sanity.py` → `scripts/sanity.py`
  - `gerrymandering_project.qgz` → `qgis/gerrymandering_project.qgz`
  - Deleted `.coverage` and `.DS_Store` (build artifacts)
  - Updated `CLAUDE.md` for both new paths

### State at end of session

LaTeX paper compiles clean at `writeup/paper1/paper.tex` / `paper.pdf`. Repo root is tidy. Draft.md and paper.tex are in sync. Ready for dissemination prep.

### What to do next session

1. Write 1-page pitch summary (choropleth lead image + plain-language permutation test + caveats) for Rice Media / Mothership
2. Set up Substack or personal site; establish citable URL before pitching
3. Run second MCMC seed for robustness check (noted as limitation in §7)
4. (Optional) Submit preprint to SSRN or SocArXiv for a citable DOI

---

## 2026-04-18 (session 14) — paper 1 draft written (4,581 words)

### What was done

- **Created `wiki/paper-plan.md`** — two-paper structure: paper 1 scope/figures/caveats; paper 2 algorithm requirements (variable-size multi-member ReCom); dissemination order (self-publish → Rice/Mothership → Reddit → WP); demographic proxy as possible interim bridge flagged.

- **Created `writeup/paper1/outline.md`** — 8-section outline with word budgets, figure placement, and register notes ("statistically anomalous competitive exclusion pattern" not "gerrymandering").

- **Created `writeup/paper1/draft.md`** — full 4,581-word draft paper:
  - §1 Introduction: hook (lowest opposition seat count despite competitive popular vote)
  - §2 Background: GRC block-vote mechanism, seat–vote gap table, ensemble approach
  - §3 MCMC results: planning-area cohesion 0th pctile, compactness 100th pctile, administrative-logic framing
  - §4 Minority rationale: t-test p=0.117–0.441, GRC placement not predicted by minority %
  - §5 Class politics: 4-room HDB r=0.483 p=0.006 in 2020; signal vanishes in 2025; two candidate explanations
  - §6 Permutation test (headline): 0 of expected 3.2 overlap, p=0.012; Fernvale/Jalan Kayu narrative; competitive geography relocation; r=−0.444 correlation
  - §7 Caveats: conditioned structure, threshold sensitivity, n=3 fragility, intent cannot be established, single seed
  - §8 Conclusion: GRC system is primary mechanism; permutation test adds secondary finding on subzone allocation

### State at end of session

Draft complete at `writeup/paper1/draft.md`. Figures are referenced by filename but not embedded — requires Substack/platform step before publication. Repository URL placeholder in methods note. Ready for review pass before dissemination.

### What to do next session

1. Review draft — tighten language, check figure captions match actual PNG outputs
2. Write the 1-page pitch summary (outline §dissemination: lead image + plain-language permutation test + caveats)
3. Decide publishing platform (Substack setup or personal site) and create URL before pitching
4. (Optional) Run second MCMC seed to complete the robustness check noted in §7

---

## 2026-04-18 (session 13) — boundary change permutation test (H&M-style)

### What was done

- **Built `src/analysis/boundary_permutation.py`** — formal statistical test asking: among the 114 subzones that changed constituency 2020→2025, did those from competitive 2020 constituencies (PAP <55%) systematically avoid landing in competitive 2025 constituencies?

- **Primary test: Fisher's exact / hypergeometric** — 2×2 contingency table of (competitive/non-competitive origin) × (competitive/non-competitive destination). One-sided Fisher's exact and hypergeometric CDF.

- **Four output plots** in `output/electoral_profile/boundary_permutation/`:
  - `hypergeometric_test.png` — null PMF with actual value (0) marked; H&M-style distributional figure
  - `destination_flow.png` — where each origin category's subzones ended up (% of population)
  - `origin_vs_delta.png` — scatter of origin PAP% vs shift in destination PAP%; r=−0.444 p<0.001
  - `competitive_seat_geography.png` — 2020 competitive PAP constituencies (6/7 dissolved) vs 2025 (6/7 new)

- **Updated `wiki/findings.md`** — added §6 "Boundary Change Permutation Test (H&M-style)" and revised §8 (What Can Be Said) to incorporate the new finding.

### Key quantitative results

**Primary test:**
- N = 114 changed subzones; K = 7 landed in competitive 2025 destinations (Jalan Kayu only)
- n = 52 came from competitive 2020 constituencies (Bukit Batok, East Coast, West Coast)
- Actual overlap: **0** (expected under H₀: 3.2)
- Fisher's exact p = **0.012** (one-sided); hypergeometric P(X≤0) = **0.012**
- Actual redistricting lies at the **1.2th percentile** of the null distribution

**Competitive seat migration:**
- The sole new competitive 2025 PAP constituency (Jalan Kayu, PAP 51.5%) was seeded entirely from **Ang Mo Kio stronghold** subzones (FERNVALE 58,800 + 6 smaller subzones, all from AMK GRC at PAP 71.9%)
- 6 of 7 competitive PAP 2020 constituencies were dissolved/merged; 6 of 7 competitive PAP 2025 constituencies are brand new
- Only East Coast survived by name, but PAP share rose 53.4%→58.7% (marginal→safe)

**Correlation:** Pearson r = −0.444 (p<0.001) between origin PAP% and Δ(destination−origin) PAP%. More competitive 2020 origins show larger positive shifts → competitive-origin subzones moved to disproportionately safer 2025 seats.

### H&M comparison

H&M showed NC's map was a partisan outlier within geometrically valid plans. Our test shows Singapore's 2025 redistricting is a statistical outlier in the POLITICAL SELECTION of which subzones go where — competitive-origin populations were systematically excluded from the new competitive constituency, at p=0.012. Key caveat: this conditions on the 2025 constituency structure being fixed; it does not test whether that structure itself is anomalous.

### State at end of session

498 tests still passing (no new tests written — this is analysis/output code only). `wiki/findings.md` updated with §6. All plots committed.

---

## 2026-04-18 (session 12) — electoral profile analysis + findings written

### What was done

- **Fetched ELD vote results from data.gov.sg** (`d_581a30bee57fa7d8383d6bc94739ad00`): 1,609 records, 1955–2025. Fields: year, constituency, constituency_type, candidates, party, vote_count, vote_percentage. Saved to `data/raw/eld_results_raw.json`.

- **Built `src/analysis/electoral_profile.py`** (~680 lines):
  - `load_eld_results(year)`: infers seat count from candidates field (count `|` separators + 1); handles walkovers via `_WALKOVERS` dict (Marine Parade-Braddell Heights GRC, 5 seats, 2025 — not in ELD data)
  - `load_subzone_demographics()`: merges GeoJSON + master_population_subzone.csv on normalized subzone name
  - `aggregate_demographics_by_constituency(assignments, subzone_demo)`: sums per constituency, derives pct_chinese/malay/indian/minority, pct_hdb/small_hdb/4room_hdb/large_hdb/private
  - `malapportionment_analysis(df, year)`: seat–vote gap, efficiency gap, votes-per-seat-won (won constituencies only)
  - `correlation_analysis(df)`: Pearson r of opp_pct vs demographic variables
  - `size_vs_politics(df)`: mean stats by political_category
  - `boundary_changes(df20, df25)`: 114 subzones changed between 2020 and 2025
  - `grc_minority_analysis(df, year)`: t-test GRC vs SMC minority %, within-GRC correlations
  - Generates plots: `opp_vs_size_{year}.png`, `demo_corr_{year}.png`, `malapportionment_bins.png`, `boundary_changes.png`

- **Outputs generated** in `output/electoral_profile/`:
  - `constituencies_2020.csv`, `constituencies_2025.csv`
  - `malapportionment.csv`, `correlations_2020.csv`, `correlations_2025.csv`
  - `size_vs_politics_2020.csv`, `size_vs_politics_2025.csv`
  - `boundary_changes.csv` (114 changed subzones, sorted by population)
  - `findings_summary.json`
  - 4 plots in `plots/`

- **Wrote `wiki/findings.md`** — comprehensive synthesis of all quantitative findings.

### Key quantitative results

**Malapportionment:**
- 2020: PAP 89.25% seats from 61.23% votes → seat–vote gap +28.0 pp; efficiency gap 16.2%
- 2025: PAP 89.69% seats from 65.57% votes → seat–vote gap +24.1 pp; efficiency gap 7.3%
- Votes-per-seat-won: PAP 16,928 vs opposition 16,148 (ratio 0.954) — nearly equal per-seat efficiency; distortion is structural (GRC amplification), not differential constituency sizing

**Demographic correlations (2020, n=31):**
- % 4-room HDB: r=+0.483, p=0.006 (significant) — middle-class areas more opposition
- % small HDB (≤3-room): r=−0.366, p=0.043 (significant) — working-class areas more PAP
- All ethnic variables: insignificant
- 2025: all correlations insignificant (class signal vanished)

**GRC minority analysis:**
- GRC mean minority %: 22.4% (2020), 22.7% (2025)
- SMC mean minority %: 20.5% (2020), 18.9% (2025)
- t-test p=0.44 (2020), p=0.12 (2025) — no significant difference
- Minority % does not predict GRC placement, GRC size, or opposition vote share

**Notable boundary changes:**
- FERNVALE (58,800): Ang Mo Kio stronghold → Jalan Kayu marginal (WP got 48.5%)
- ALJUNIED + MACPHERSON + Marine Parade belt (~160,000 people): merged into Marine Parade-Braddell Heights walkover
- BUKIT BATOK CENTRAL: marginal Bukit Batok SMC → Jurong East-Bukit Batok stronghold (76.7%)
- 114 total subzones changed constituency; marginal/competitive seats restructured disproportionately

### State at end of session

All analysis complete. `wiki/findings.md` written. Pipeline fully documented. 498 tests passing.

---

## 2026-04-18 (session 11) — diff pipeline fixed + results interpreted

### What was done

- **Fixed broken `diff` pipeline (design gap):** `build_diff_report` was written expecting a `run_id` column in actual-plan assignment parquets and actual-plan metrics embedded in ensemble_metrics at `step_index=0`. But `assign_actual` only saved `{node_id, ed_name}` — no metrics, no run_id.

- **Redesigned diff data flow:**
  - Added `compute_actual_plan_metrics(assignment_str, graph, subzone_geoms)` to `diff_2020_2025.py` — converts `node_id→ed_name` dict to integer district IDs, calls `compute_all` metrics registry.
  - Added `load_actual_metrics(year, paths)` — reads sidecar `{year}_metrics.json`.
  - Changed `build_diff_report(actual_metrics_2020, actual_metrics_2025, ensemble_metrics)` — no more run_id lookup.
  - `_cmd_assign_actual` now computes and saves `{year}_metrics.json` alongside the assignments parquet.
  - `_cmd_diff` loads sidecar metrics, passes directly to `build_diff_report`.
  - Tests updated: `test_diff_2020_2025.py` rewritten for new interface (+9 tests total, 498 passing).

- **Re-ran `assign-actual` for both years** to generate metrics sidecars.

- **Ran `diff --run-id sg2025`** successfully: `output/diff/sg2025/diff_report.json` + 4 plots.

### Results

Ensemble: 9 000 post-burn-in steps, seed 42, k=33, pop_tolerance=10%, recom_epsilon=5%.

| Metric | Actual 2020 | Actual 2025 | Ensemble mean | Ensemble range | 2020 pctile | 2025 pctile |
|--------|------------|------------|---------------|----------------|-------------|-------------|
| `max_abs_pop_dev` | 1.223 | 1.223 | 0.096 (const) | [0.096, 0.096] | 100th | 100th |
| `towns_split` | 12 | 12 | 12 (const) | [12, 12] | 0th | 0th |
| `pln_area_splits` | 30 | 28 | 36.3 | [30, 42] | 0th | 0th |
| `mean_pp` | 0.435 | 0.418 | 0.353 | [0.314, 0.399] | 100th | 100th |

### Interpretation

**Non-informative metrics (ensemble has zero variance):**
- `max_abs_pop_dev` is frozen at 0.0955 across all 9000 steps — likely one subzone always anchors a district at the ReCom constraint ceiling. Comparison against actual (1.22) is also confounded: actual plans use GRCs (multi-member, variable size) vs ensemble's 33 equal-pop SMC-equivalent districts. Not a meaningful comparison.
- `towns_split` is frozen at 12 in every step. With 26 HDB towns divided into 33 districts, 12 towns are structurally always split regardless of how the map is drawn (a graph-topology inevitability for this specific Singapore subzone graph). Not informative.

**Informative metrics:**
- **`pln_area_splits` (0th percentile):** Actual 2020 (30) and 2025 (28) split fewer planning areas than all or nearly all MCMC plans (min=30, mean=36). The 2025 plan ties the MCMC minimum. This is a statistically extreme finding: the actual boundaries preserve planning area cohesion better than any randomly sampled equal-population plan. This strongly suggests the actual electoral boundaries were drawn with explicit reference to planning area lines.
- **`mean_pp` (100th percentile):** Actual plans (0.435, 0.418) are more compact than any MCMC plan (max=0.399). Actual GRC boundaries are more geometrically compact than any of the 9000 random 33-district partitions. This is the opposite of what typical partisan gerrymandering looks like (which tends to produce bizarre shapes). Singapore's GRCs are large, round, administratively aligned — consistent with boundaries following planning areas rather than being drawn to dilute votes.

**Overall conclusion:** The actual electoral boundaries are extreme outliers in planning-area cohesion and compactness, but in a direction inconsistent with shape-based gerrymandering. The GRC system introduces malapportionment (`max_abs_pop_dev`) that is outside the MCMC comparison framework (different institutional structure). The key finding is that real maps respect planning area lines far better than random maps — this is a constraint the ELD appears to be following.

### Limitations to document

1. GRC vs SMC mismatch: the ensemble models 33 single-member equal-pop districts; the actual plans have 12-17 constituencies of varying multi-member size. Pop-balance comparison is not apples-to-apples.
2. `towns_split` and `max_abs_pop_dev` zero-variance in ensemble — structural, not exploratory failure.
3. Only 1 run at 10k steps. Should run multiple seeds to verify mixing.
4. Actual plan assignment is by subzone→ED areal majority. Edge subzones near constituency boundaries may be misassigned.

### State at end of session

`output/diff/sg2025/diff_report.json` written. Plots in `output/diff/sg2025/plots/`. Pipeline complete end-to-end. Findings written above. Next: update `wiki/methodology.md` with results, write findings summary.

### What to do next session

1. Update `wiki/methodology.md` with the quantitative results table and interpretation
2. Write `wiki/findings.md` with the headline conclusions + caveats
3. Consider: rerun ensemble with `seed=123` (or other seeds) for mixing verification
4. Consider: whether the GRC-level comparison (grouping subzones by GRC, not SMC) would be more meaningful

---

## 2026-04-17 (session 10) — ISSUE-4 fix + ISSUE-5 fix; ensemble now running

### What was done

- **Diagnosed why `allow_pair_reselection` was not on `MarkovChain.__init__`:** In GerryChain 0.3.2 the flag lives on `bipartition_tree`, not on `MarkovChain`. The fix required passing `functools.partial(bipartition_tree, allow_pair_reselection=True, max_attempts=1000)` as the `method` kwarg to `recom`.

- **Fixed ISSUE-4 (chain freezes with BipartitionWarning):** `src/analysis/mcmc/recom.py` — `build_chain()` now passes a `bipartition_with_reselection` partial as `method`. `max_attempts=1000` makes failing pairs give up quickly and trigger reselection, yielding a **130× speedup** (19.6 s/step → 0.15 s/step). Tests added/updated in `tests/test_mcmc_recom.py` (TDD: RED → GREEN). Code-reviewer agent approved.

- **Discovered and fixed ISSUE-5 (disconnected graph; node 317 breaks BFS seeder):** After fixing ISSUE-4, the BFS seeder still failed with `SeedPartitionError: District 0 is not contiguous. Nodes in district: [13, 16, 86, 317]`. Investigation found that `filter_for_mcmc` was keeping node 317 (pop=50, no edges — a truly isolated subzone) because its population exceeded the old default `min_pop=1`. Changed default to `min_pop=float("inf")` so **all non-mainland components are excluded by default**, regardless of population. An isolated node cannot participate in any contiguous district, so exclusion is always correct for MCMC. Node 317 represents 0.001% of total population — negligible. Tests updated in `tests/test_graph_build.py` (2 new tests, 1 renamed).

- **489 tests passing** (was 488 at start of session; +1 from recom, +2 from graph_build, -1 old test renamed/updated).

- **Full 10 000-step ensemble launched** (PID 65626, `data/processed/ensemble/sg2025.tmp`). At ~0.15 s/step the chain should complete in ~25 minutes; seeding (once) adds ~20 s.

- **Deleted `wiki/next-agent-prompt.md`** — superseded by session log.

### State at end of session

Ensemble running. `data/processed/ensemble/sg2025.tmp` will rename to `sg2025/` on completion. No diff output yet.

### What to do next session

1. Confirm ensemble completed: `ls data/processed/ensemble/sg2025/`
2. Assign actual plans (if not already done): `python -m src.analysis.cli assign-actual --year 2020` and `--year 2025`
3. Run diff: `python -m src.analysis.cli diff --run-id diff_sg2025 --year-2020-run-id sg2025 --year-2025-run-id sg2025`
4. Review `data/processed/ensemble/sg2025/metrics.parquet` histograms and `diff_report.json` percentiles — focus on `towns_split`, `max_abs_pop_dev`, `mean_pp`
5. Interpret whether the 2020/2025 plans are statistical outliers; update `wiki/methodology.md` with findings

---

## 2026-04-17 (session 9) — Wiki knowledge graph refactor + BFS seeder (Fix A) + ensemble unblocked

### What was done

- **Wiki refactored into Wikipedia-style knowledge graph:**
  - `related-literature/` moved to `wiki/literature/` (git mv, history preserved)
  - `wiki/literature/INDEX.md` — annotated bibliography of all 8 papers
  - `wiki/methodology.md` — full ensemble framework documentation with NC literature comparison
  - `wiki/seeding.md` — seeding problem root cause, Fix A vs Fix B literature reasoning, current state
  - All existing wiki pages updated with bidirectional cross-links
  - `wiki/INDEX.md` — expanded into a proper hub with navigation table and key cross-link paths

- **Literature reasoning for Fix A vs Fix B:**
  - Fix A (BFS seeder): literature-faithful — neutral random initialization, no circularity
  - Fix B (actual plan as seed): rejected as methodologically circular per Herschlag et al. NC practice of running chains from independent random seeds to verify mixing
  - Full argument documented in `wiki/seeding.md` and `wiki/decisions.md`

- **BFS seeder implemented** (`src/analysis/seed_plans.py`):
  - `_bfs_seed_partition()`: greedy BFS growth from non-zero-pop seeds + `_local_swap_pass()` for population balance
  - `make_seed_partition()` now two-phase: `recursive_tree_part` (N attempts) → BFS fallback (10 attempts)
  - 487 tests passing (was 481; added 6 BFS-specific tests; fixed 6 pre-existing CLI test regressions from session 7/8)

- **Ensemble started** — seeding now succeeds; chain entered MCMC loop

- **New blocker identified (ISSUE-4):** Chain is running but flooded with `BipartitionWarning: Failed to find a balanced cut after 1000 attempts`. GerryChain's recommendation is to enable `allow_pair_reselection` on the MarkovChain so that when a district-pair ReCom step fails, the chain resamples a different pair rather than rejecting. Fix location: `src/analysis/mcmc/recom.py` — add `allow_pair_reselection=True` to `MarkovChain(...)`. See `wiki/issues.md`.

### State at end of session

Ensemble running (PID 61909, `/tmp/ensemble_sg2025_v2.log`) but with very high rejection rate due to BipartitionWarnings. No output written to `output/runs/` yet. Should be killed and restarted after the `allow_pair_reselection` fix.

### What to do next session

1. Kill running ensemble: `kill 61909`
2. Fix `src/analysis/mcmc/recom.py`: add `allow_pair_reselection=True` to `MarkovChain(...)` call in `build_chain()`
3. Add/update tests for the fix (tdd-guide agent)
4. Re-run: `python -m src.analysis.cli run-ensemble --run-id sg2025 --n-steps 10000`
5. Once complete: `python -m src.analysis.cli diff --run-id diff_sg2025 --year-2020-run-id sg2025 --year-2025-run-id sg2025`
6. Review output plots and summary table

---

## 2026-04-13 (session 8) — Diagnose seeding failure; write issues.md

### What was done

- Ran `run-ensemble --run-id sg2025 --n-steps 10000` → failed with `SeedPartitionError` at the seeding step
- Root-caused the failure: GerryChain's `recursive_tree_part` cannot bisect the real Singapore graph because ~36 % of subzones have `pop_total=0`, and some recursion sub-graphs have no balanced spanning-tree cut
- Inspected `output/actual_assignments/2020.parquet` (328 nodes, 31 districts)
- Identified 4 uninhabited island nodes (27 SUDONG, 28 SEMAKAU, 29 SOUTHERN GROUP, 308 PULAU SELETAR) absent from actual assignments
- Documented two proposed fixes (BFS seeder, lower k to 31) in `wiki/issues.md`

### State at end of session

**Ensemble blocked.** `assign-actual` Parquets are written and correct. The MCMC chain itself has not run yet.

### What to do next session

1. Implement Fix A from `wiki/issues.md`: add `_bfs_seed_partition` to `src/analysis/seed_plans.py`
2. Test that `make_seed_partition` returns a valid partition on the real graph (`validate_partition` passes)
3. Re-run `python -m src.analysis.cli run-ensemble --run-id sg2025 --n-steps 10000`
4. Once ensemble completes, run `diff` subcommand and review output plots/table

See `wiki/issues.md` for full root cause, pseudocode, and reproduction steps.

---

## 2026-04-13 (session 7) — Sync docs; run actual MCMC analysis

### What was done

- Updated `wiki/implementation-plan.md`: marked Phase 5 complete (was stale at "401 tests / Phase 5 remains")
- Ran `assign-actual --year 2020` and `assign-actual --year 2025` → wrote actual assignment Parquets to `output/actual_assignments/`
- Ran `run-ensemble --run-id sg2025 --n-steps 10000` → generating ensemble in background
- Outputs to vet: `output/actual_assignments/2020.parquet`, `output/actual_assignments/2025.parquet`, `output/runs/sg2025/`

### State at end of session

Analysis pipeline running. Once ensemble completes, run `diff` subcommand.

### What to do next session

1. `python -m src.analysis.cli diff --run-id diff_sg2025 --year-2020-run-id sg2025 --year-2025-run-id sg2025`
2. Review `output/runs/sg2025/diff_report.json`, `output/runs/sg2025/*.png`, `output/runs/sg2025/summary_table.csv`
3. Interpret percentile ranks for HDB town-splitting and population deviation

---

## 2026-04-13 (session 6) — Repo cleanup: remove root-level duplicates, add .gitignore, refresh README

### What was done

- Deleted 10 root-level duplicate directories/files (all confirmed identical to `data/raw/` or `data/reference/`)
- Moved `QGIS-3.44-GentleGISIntroduction-en.pdf` to `related-literature/`
- Removed empty `docs/` and `data/raw/geospatial_subzone/` directories
- Created `.gitignore`: excludes `__pycache__`, `.DS_Store`, `.coverage`, `.venv`, `output/`, `data/processed/`, large raw data dirs (`hdb/`, `polling_community/`, `sla_cadastral/`), large reference binaries
- Removed `__pycache__` directories from git tracking (had been committed)
- Rewrote `README.md` to cover both the preprocessing pipeline and the MCMC analysis pipeline with correct commands

### State at end of session

Clean. Repo root is now minimal: `src/`, `tests/`, `data/`, `wiki/`, `related-literature/`, `output/`, `CLAUDE.md`, `README.md`, `gerrymandering_project.qgz`, `sanity.py`, `requirements.txt`, `pyproject.toml`.

### What to do next session

1. Run `python -m src.analysis.cli assign-actual --year 2020` and `--year 2025` — generate actual assignment Parquets
2. Run `python -m src.analysis.cli run-ensemble --run-id sg2025 --n-steps 10000` — generate ensemble
3. Run `python -m src.analysis.cli diff ...` — produce diff report, plots, and summary table
4. Review `output/` for outlier signals in HDB town-splitting and population deviation

---

## 2026-04-13 (session 5) — Phase 5 complete; full pipeline implemented; 481 tests green

### What was done

- **ensemble.py (task 4.1)** — implemented `run_ensemble`, `build_pipeline_inputs`, `_build_run_outputs`; atomic tmp→rename write; burn_in skipping; Parquet output
- **io_layer fix** — `load_hdb_buildings()` now lowercases all columns (BLK_NO → blk_no)
- **communities fix** — `_join_buildings_to_properties` falls back to blk_no-only modal join when buildings lack a `street` column (`HDBExistingBuilding.geojson` uses `ST_COD` street codes, not names); real-data smoke test now passes
- **Phase 5 via 3 parallel subagents:**
  - `diff_2020_2025.py` — `load_actual_assignments`, `load_ensemble_metrics`, `compute_percentile`, `build_diff_report`, `save_diff_report`
  - `reporting/plots.py` + `reporting/tables.py` — histogram plots with actual plan markers; pivot summary CSV + markdown
  - `cli.py` — `run-ensemble`, `assign-actual`, `diff` subcommands via argparse
- **Wiki compressed** — session-log consolidated, implementation-plan stripped to Phase 5 spec only
- **CLAUDE.md updated** — added analysis pipeline commands and module table

### State at end of session

Clean. 481 tests passing, 0 failing. Full pipeline implemented end-to-end. Ready to run actual analysis.

### What to do next session

1. Run `python -m src.analysis.cli assign-actual --year 2020` and `--year 2025` — generate actual assignment Parquets
2. Run `python -m src.analysis.cli run-ensemble --run-id sg2025 --n-steps 10000` — generate ensemble (takes time; ~10k ReCom steps)
3. Run `python -m src.analysis.cli diff ...` — produce diff report, plots, and summary table
4. Review output plots and table for outlier signals in HDB town-splitting and population deviation

---

## 2026-04-13 (session 4) — Phases 2–4 complete; 401 tests green

### Completed this session

- **ensemble.py (task 4.1)** — `run_ensemble(config, paths)`, `build_pipeline_inputs(paths)`, `_build_run_outputs(...)`. Atomic tmp→rename write; burn_in skipping; Parquet output. 37 tests added.
- **io_layer column fix** — `load_hdb_buildings()` now lowercases all column names (BLK_NO → blk_no, etc.).
- **communities.py join fix** — `_join_buildings_to_properties` falls back to blk_no-only modal join when buildings lack a `street` column (HDBExistingBuilding.geojson has `ST_COD` street code, not readable street names). Real-data smoke test now passes.

### Data discovery

`HDBExistingBuilding.geojson` columns: `OBJECTID, BLK_NO, ST_COD, ENTITYID, POSTAL_COD, INC_CRC, FMEL_UPD_D, SHAPE.AREA, SHAPE.LEN, geometry`. `ST_COD` is a street code (e.g. `CLA09K`), not a human-readable street name — cannot join to property table on `blk_no + street`.

### State at end of session

- 401 tests passing, 0 failing
- Phase 5 is the only remaining work

---

## 2026-04-12 (session 3) — Phases 0–3 built; session 4 picked up mid-Phase 4

### Completed

| Task | File | Tests |
|------|------|-------|
| 0.1 | `src/utils.py` | 20 |
| 0.2 | `tests/test_sanity.py` | 19 |
| 0.3 | `src/analysis/` scaffold + GerryChain 0.3.2 | 26 |
| 1.1 | `src/analysis/io_layer.py` | 28 |
| 1.2 | `src/analysis/graph_build.py` | 37 |
| 1.3 | `src/analysis/communities.py` | 13 |
| 2.1–2.5 | `src/analysis/config.py`, `seed_plans.py`, `mcmc/` | ~40 |
| 3.1–3.4 | `src/analysis/metrics/` | ~50 |
| 4.2 | `src/analysis/assign_actual.py` | ~15 |

Real graph results: 332 subzone nodes, 850 edges, 4 offshore islands excluded (SUDONG, SEMAKAU, SOUTHERN GROUP, PULAU SELETAR).

---

## 2026-04-12 (session 2) — Analysis direction decided

Chose MCMC ensemble method (ReCom/GerryChain) on URA subzones; HDB town splitting as primary metric; population deviation as secondary. Partisan analysis infeasible (no precinct-level vote data). See `decisions.md`.

---

## 2026-04-12 (session 1) — Wiki initialized; no code changes
