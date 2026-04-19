# Paper Plan

Part of the [project wiki](INDEX.md).

---

## Two-paper structure

### Paper 1 — current findings (ready to write)

**Working title:** "Boundary Changes and Competitive Seat Exclusion in Singapore's 2025 Redistricting: An Ensemble-Based Test"

**Core claim:** Singapore's 2020→2025 redistricting produced a statistically anomalous pattern of competitive exclusion: subzones drawn from competitive 2020 constituencies were systematically channelled away from competitive 2025 destinations (p = 0.012). The new competitive seat (Jalan Kayu) was built entirely from Ang Mo Kio stronghold population.

**Secondary claims:**
- Seat–vote gap: 61% vote share → 89% of seats, driven by GRC block-vote amplification not boundary shape manipulation
- GRC placement does not predict minority population concentration (GRC rationale unsupported)
- Class politics (4-room HDB) predicted opposition vote share in 2020 (r = 0.483, p = 0.006); signal vanished in 2025
- MCMC ensemble: actual boundaries are extreme outliers in planning-area cohesion (0th percentile) and compactness (100th percentile) — consistent with administrative logic, not partisan shape manipulation

**Target length:** ~4,000–6,000 words (policy paper / long-form journalism register, not academic journal)

**Figures:**
- `output/electoral_profile/boundary_permutation/combined_summary.png` — headline figure (hypergeometric PMF + seat geography)
- `output/electoral_profile/boundary_permutation/choropleth_2020_2025.png` — geographic map
- `output/electoral_profile/boundary_permutation/origin_vs_delta.png` — scatter r = −0.444
- Seat–vote gap table (§2 of findings.md)
- GRC minority rationale table (§4 of findings.md)

**Honest limitations to include:**
- Test conditions on 2025 structure being fixed; does not test whether the structure itself is anomalous
- Only 3 competitive constituencies in 2020; result is threshold-sensitive
- Cannot establish intent; consistent with administrative rebalancing
- Single MCMC seed (limitation 7)

---

### Paper 2 — future work (algorithm needed first)

**Working title:** "A Variable-Size Multi-Member Ensemble Method for Testing Partisan Gerrymandering in GRC-Style Electoral Systems"

**Core contribution:** A GerryChain-equivalent algorithm that supports variable-size multi-member districts (k seats per district), enabling ensemble-based outlier tests for parliamentary systems with block-vote multi-member constituencies (Singapore GRCs, UK multi-member wards, etc.).

**Why paper 1 cannot do this:** GerryChain requires equal-population single-member districts. Testing whether the GRC placement itself (which areas get 3-seat vs 5-seat GRCs, and how seats are allocated) is anomalous requires a model that can generate random variable-seat configurations with a neutral baseline — which does not currently exist.

**What paper 2 would enable:** A direct H&M-style test of GRC seat-count allocation against a null distribution of neutral configurations, instead of conditioning on the 2025 structure as fixed.

**Research dependencies:**
- New partition algorithm: ReCom variant with variable target populations per district
- Neutral criteria for seat-count assignment (a hard normative question)
- Validation on known gerrymandering cases

---

## Dissemination plan (Paper 1)

**Priority order:**

1. **Self-publish** — Substack or a personal site. Creates a citable, shareable URL before pitching anywhere.
2. **Rice Media or Mothership** — Data-driven Singapore politics pieces fit their editorial profile. Pitch with the choropleth map as lead image.
3. **Reddit r/singapore** — Seed after a published link exists.
4. **Opposition MP (Workers' Party)** — WP MPs (Pritam Singh, Jamus Lim, etc.) can raise findings in Parliament. They need a citable published source, not raw analysis. Approach after step 1–2.
5. **Academic journal** (optional, slow track) — *Electoral Studies*, *Political Geography*, or *Asian Journal of Political Science*. Requires additional rigour (peer review caveats, literature review, formal methods section). Not a blocker for impact.

**What to prepare for pitch:**
- 1-page summary with the headline figure
- Plain-language explanation of the permutation test (non-technical audience)
- Clear caveats framed as intellectual honesty, not weakness

---

## Open methodological questions (for paper 2 scoping)

See also [open-questions.md](open-questions.md) §5 (GRC multi-member structure in ensemble generation).

- What is the neutral baseline for seat-count assignment per district? Population-proportional? Fixed government formula?
- Can the variable-size ReCom be validated on toy cases before applying to Singapore?
- Is the demographic proxy approach (OLS regression of competitive seat count on HDB demographics, applied to ensemble plans) a valid interim test? If yes, this could appear as a section in paper 1 rather than waiting for paper 2.
