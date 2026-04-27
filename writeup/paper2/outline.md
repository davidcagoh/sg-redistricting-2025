# Paper 2 Outline

**Working title:** GRC Placement as a Policy Lever: Ensemble Analysis of Variable-Size
Multi-Member Constituencies in Singapore's Electoral Redistricting

**Status:** pre-draft. Code infrastructure complete (src/analysis/grc/). Ensemble runs not yet executed.

---

## Research question

Paper 1 identifies the GRC block-vote mechanism as the *primary* driver of Singapore's
seat–vote bonus, and subzone allocation as a *secondary* mechanism. Paper 2 addresses
a third layer that paper 1 explicitly cannot test (§7 Caveats):

> "Testing the GRC placement decision requires an ensemble model that can generate random
> variable-size multi-member district configurations, which does not currently exist."

**Core question:** Given the 2025 seat-count vector (15 SMC + 8 four-seat GRC + 10 five-seat
GRC = 33 districts, 97 seats), are the actual GRC placements outliers in:
1. Minority population capture (the official ethnic-representation rationale)?
2. Competitive seat allocation (extension of paper 1's permutation finding)?
3. Geographic concentration of large GRCs (seat-magnification geography)?

---

## Data already available

- Subzone graph (332 nodes, 850 edges)
- HDB town labels (node attribute `hdb_town`)
- Planning area labels (node attribute `pln_area`)
- Electoral results 2020/2025 (from `electoral_profile.py`)

## Data gaps to fill before running ensemble

- **Minority population fraction per subzone** — need to attach `pct_minority` from
  Census 2020 (`data/raw/census_2020_subzone/`) to graph nodes. The Census has
  Malay + Indian columns that can be summed / divided by total.
- **Competitive score per subzone** — assign each subzone a 2020 PAP vote share from
  its source constituency (available in `assign_actual.py` output).

---

## Planned sections

1. Introduction: the GRC as an amplifier; what paper 1 left unanswered
2. The ensemble design: variable-target ReCom, seat-count vector as fixed input
3. Minority population capture results
4. Competitive subzone allocation results
5. Geographic seat-size distribution
6. Caveats: seat-count vector is fixed (not sampled); minority data at subzone not
   polling-district level; single ethnic proxy (Malay + Indian)
7. Conclusion: what the GRC placement decision does and does not explain

---

## Code

- `src/analysis/grc/` — full variable-size GRC ensemble pipeline
- `python -m src.analysis.grc.cli run-ensemble` — entry point
- Outputs: `data/processed/ensemble/grc/<run_id>/`

## Next steps

1. Attach `pct_minority` to graph nodes from Census subzone data
2. Attach `pap_2020_pct` (competitive score) to graph nodes from assign_actual output
3. Run first GRC ensemble (seed 42, 10k steps)
4. Compare actual 2025 plan against ensemble: minority capture, competitive geography
5. Write draft
