# Findings

This document synthesises the quantitative results from two independent analyses:
1. **MCMC ensemble comparison** — how does the actual electoral map compare to 9,000 randomly-drawn equal-population plans using the same subzone building blocks?
2. **Electoral profile analysis** — what do ELD vote results (1955–2025) reveal about malapportionment, demographic correlations, and boundary changes?

Data sources: URA subzone GeoJSON, Census 2020 subzone population, ELD results from data.gov.sg, HDB building/property tables.

---

## 1. MCMC Ensemble Results

Ensemble: 9,000 post-burn-in ReCom steps, seed 42, k=33 districts, pop_tolerance=10%.

| Metric | Actual 2020 | Actual 2025 | Ensemble mean | Ensemble range | 2020 pctile | 2025 pctile |
|--------|------------|------------|---------------|----------------|-------------|-------------|
| `max_abs_pop_dev` | 1.223 | 1.223 | 0.096 | [0.096, 0.096] | 100th | 100th |
| `towns_split` | 12 | 12 | 12 | [12, 12] | 0th | 0th |
| `pln_area_splits` | 30 | 28 | 36.3 | [30, 42] | **0th** | **0th** |
| `mean_pp` | 0.435 | 0.418 | 0.353 | [0.314, 0.399] | **100th** | **100th** |

### Interpretation

**Non-informative metrics:** `max_abs_pop_dev` and `towns_split` are structurally constant across the ensemble (zero variance across all 9,000 steps). Both comparisons against the actual plan are therefore uninformative. The population deviation result is also confounded: the actual plan uses variable-size GRCs; the ensemble models 33 equal-population single-member districts. These are different institutional structures, not comparable.

**Planning area cohesion (`pln_area_splits`, 0th percentile):** The 2020 plan (30 splits) ties the ensemble minimum; the 2025 plan (28 splits) falls below the ensemble minimum — i.e., it achieves better planning-area cohesion than any of the 9,000 randomly drawn maps. This is a statistically extreme result. It strongly implies the actual boundaries were drawn with explicit reference to URA planning area lines as a constraint.

**Compactness (`mean_pp`, 100th percentile):** Both actual plans are more compact than every ensemble plan. The actual GRC boundaries are large, geometrically round, and administratively aligned — the opposite of the bizarre elongated shapes that typify partisan gerrymanders in the US context. High compactness is consistent with boundaries following planning areas rather than being drawn to dilute votes by shape.

**Overall MCMC conclusion:** The actual map is an extreme outlier in planning-area cohesion and compactness, but in a direction that reflects administrative logic, not shape manipulation. The GRC institutional structure (multi-member, block-vote constituencies of different sizes) is the primary source of malapportionment effects, not the geographic drawing of boundaries per se.

---

## 2. Malapportionment

| Year | PAP seats | PAP seat share | PAP vote share (contested) | Seat–vote gap | Efficiency gap |
|------|-----------|---------------|---------------------------|---------------|----------------|
| 2020 | 83 / 93 | 89.25% | 61.23% | **+28.0 pp** | **16.2%** |
| 2025 | 87 / 97 | 89.69% | 65.57% | **+24.1 pp** | **7.3%** |

- **Seat–vote gap**: PAP received 28 percentage points more seats than votes in 2020, and 24 pp more in 2025. Under proportional representation, PAP would have won ~57 of 93 seats in 2020 (not 83).
- **Efficiency gap**: 16.2% in 2020; the US Supreme Court has considered >8% a potential constitutional red flag in partisan gerrymandering cases. The 2025 figure (7.3%) falls below this threshold, partially because PAP's vote share rose.
- **Votes per seat won**: PAP 16,928 vs opposition 16,148 in 2020 (ratio 0.954). The per-seat vote efficiency is nearly equal, meaning the seat–vote distortion is driven primarily by the block-vote GRC structure amplifying seat bonuses from plurality wins, not from deliberately over-concentrating opposition votes in a few constituencies.

---

## 3. Demographic Correlations with Opposition Vote Share

### 2020 (n=31 contested constituencies)

| Variable | Pearson r | p-value | Significant |
|----------|-----------|---------|-------------|
| % 4-room HDB | **+0.483** | 0.006 | Yes |
| % Small HDB (≤3-room) | **−0.366** | 0.043 | Yes |
| % Indian | −0.302 | 0.099 | No |
| % Minority (Malay+Indian) | −0.174 | 0.349 | No |
| Voters per seat | +0.166 | 0.372 | No |
| Seats in constituency | +0.017 | 0.928 | No |

### 2025 (n=30 contested constituencies)

All correlations fall below significance (highest |r|=0.32 for small HDB, p=0.084). The SES gradient weakened significantly between elections.

### Interpretation

The class-politics signal is the strongest empirical finding from the demographic analysis. In 2020, middle-class HDB areas (4-room flats) supported the opposition more; working-class areas (small flats, ≤3-room) supported PAP more. This is consistent with an incumbency advantage concentrated among lower-income voters dependent on public housing and welfare programs, and a more critical middle class.

By 2025, this signal vanished — possibly because PAP's vote share rose uniformly across all SES bands, or because boundary changes (see §5) redistributed the middle-class concentrations.

**Ethnicity does not predict opposition vote share** in either year (minority % r=−0.174 in 2020, +0.112 in 2025, both insignificant). Minority concentration is not a driver of electoral outcomes based on this data.

---

## 4. GRC Minority Rationale

A common stated justification for the GRC system is that bundling constituencies ensures minority (Malay/Indian) representation in Parliament.

| Year | GRC mean minority % | SMC mean minority % | t-test p-value | Significant |
|------|--------------------|--------------------|----------------|-------------|
| 2020 | 22.4% | 20.5% | 0.441 | No |
| 2025 | 22.7% | 18.9% | 0.117 | No |

Additional tests:
- **Minority % vs opposition vote share**: r=−0.084 (2020), r=+0.209 (2025), both insignificant
- **Minority % vs GRC size (seats)**: r=+0.214 (2020), r=+0.052 (2025), both insignificant

**Conclusion:** GRCs are not placed in areas with meaningfully higher minority populations. Minority % does not predict GRC placement, GRC size, or opposition vote share. The data does not support the stated ethnic-representation rationale as the primary driver of GRC placement or sizing. This does not prove an alternative motive, but it means the system's effects cannot be explained by the ethnic rationale alone.

---

## 5. Boundary Changes 2020 → 2025

114 subzones (out of 332) changed constituency between 2020 and 2025. The ten largest by population:

| Subzone | Population | 2020 constituency | 2020 PAP % | 2025 constituency | 2025 PAP % |
|---------|-----------|------------------|------------|------------------|------------|
| FERNVALE | 58,800 | Ang Mo Kio (stronghold, 71.9%) | → | Jalan Kayu (marginal, 51.5%) | PAP barely held |
| YUNNAN | 67,500 | West Coast (marginal, 51.7%) | → | West Coast-Jurong West (safe, 60.0%) | PAP improved |
| ALJUNIED | 39,990 | Jalan Besar (stronghold, 65.4%) | → | Marine Parade-Braddell Heights (walkover) | No contest |
| MACPHERSON | 28,360 | Macpherson (stronghold, 71.7%) | → | Marine Parade-Braddell Heights (walkover) | No contest |
| BUKIT BATOK CENTRAL | 27,290 | Bukit Batok (marginal, 54.8%) | → | Jurong East-Bukit Batok (stronghold, 76.7%) | PAP improved |

### Notable patterns

**FERNVALE (58,800 people) — large subzone moved into a near-loss seat:** Fernvale was extracted from PAP stronghold Ang Mo Kio (71.9%) and placed into the newly formed Jalan Kayu SMC, where the Workers' Party won 48.53% — the closest result in 2025. Fernvale's addition to Ang Mo Kio would not have changed that outcome meaningfully. The move appears to have created a competitive seat rather than suppressed one.

**ALJUNIED + MACPHERSON + several Marine Parade subzones — absorbed into walkover:** Aljunied (Geylang), Macpherson, Marine Parade, Geylang East, and Kembangan subzones (totaling ~160,000 people) were merged into the new Marine Parade-Braddell Heights GRC, which went uncontested. This consolidates a heavily PAP belt into a single large walkover, effectively removing a large block of votes from the contested landscape.

**BUKIT BATOK CENTRAL — moved from marginal to stronghold:** The former Bukit Batok SMC (PAP 54.8% in 2020) was dissolved; Bukit Batok Central subzone moved into Jurong East-Bukit Batok, a new GRC where PAP won 76.7%. The marginal SMC was eliminated rather than contested.

**Overall direction of changes:** Marginal and competitive seats were restructured more often than safe seats. The pattern is more consistent with consolidating fragmented safe-PAP areas and eliminating marginal SMCs than with packing opposition voters — but the evidence is observational and the sample is too small for a definitive conclusion.

---

## 6. Size vs Politics

Mean voters per seat by political category (2020):

| Category | n | Total seats | Mean voters/seat |
|----------|---|-------------|-----------------|
| Stronghold PAP (>65%) | 11 | 36 | 25,648 |
| Safe PAP (55–65%) | 13 | 35 | 25,030 |
| Marginal PAP (<55%) | 4 | 12 | 28,146 |
| Opposition | 3 | 10 | 27,585 |

Opposition constituencies average ~7.5% more voters per seat than PAP strongholds in 2020 (27,585 vs 25,648). Marginal PAP seats are also larger. This is a modest malapportionment signal — the largest constituencies tend to be the most competitive or opposition-held ones. However, the effect size is small and the n is very low (3 opposition constituencies).

---

## 7. What Can Be Meaningfully Said

### What the data supports

1. **Singapore's electoral system produces strong seat-magnification effects.** A 61% vote share produces 89% of seats. This is primarily structural — the GRC block-vote system amplifies pluralities into near-sweeps, as any majoritarian system does at scale.

2. **Electoral boundaries follow administrative (planning area) logic more than random maps.** The 0th-percentile planning-area-split result is statistically robust. Boundaries track planning areas, not partisan geography.

3. **GRCs are not placed in areas with significantly higher minority populations.** The stated ethnic-representation rationale does not predict GRC placement or size in the data.

4. **Class politics predicted opposition support in 2020.** Middle-class HDB areas were significantly more likely to vote opposition; working-class areas more PAP. This signal is sociological, not geographic — it is about who lives where, not how boundaries are drawn.

5. **Several 2025 boundary changes restructured competitive and marginal seats.** Bukit Batok marginal SMC was eliminated; Macpherson stronghold SMC was absorbed into a walkover GRC; marginal West Coast was merged with safe Jurong West.

### What the data does not support

- The MCMC analysis **cannot** demonstrate that Singapore's boundaries are gerrymandered in the conventional sense (irregular shapes optimised for partisan advantage). The compactness and planning-area-cohesion results point the other way.
- The boundary change analysis **cannot** establish intent. Seat restructuring is consistent with both administrative updating (responding to population growth) and strategic boundary manipulation. The 2025 data alone cannot distinguish these.
- The malapportionment per seat **is very modest** when measured by votes-per-seat-won (0.95 ratio). The large seat–vote gap comes from the GRC system's amplification property, not from deliberately over- or under-sized constituencies.

### Where undeclared intentions might exist

The GRC system itself is the structural mechanism that matters most. The data is most consistent with a system designed to guarantee large seat majorities from plurality vote shares — regardless of boundary drawing specifics. The placement of GRCs (which determines where the seat-bonus mechanism applies) is harder to analyse because GRC size varies, nomination costs are high, and the system has no obvious non-partisan benchmark.

The one empirical signal that warrants further investigation: **the pattern of which SMCs get dissolved and which get preserved**. Marginal PAP SMCs (Bukit Batok, Hong Kah North) were eliminated or restructured in 2025, while safe ones persisted. This is a small-sample observation but directionally consistent with boundary drawing that minimises marginal constituencies.

---

## 8. Limitations

1. **GRC vs SMC mismatch in MCMC:** The ensemble models 33 equal-population SMC-equivalent districts; the actual plan has 12–18 variable-size GRCs and SMCs. Direct metric comparisons are structurally compromised for population balance.

2. **No precinct-level data:** Subzone-level census demographics are the finest granularity available. Within-constituency demographic variation is invisible.

3. **Small n for opposition constituencies:** 3 opposition constituencies in 2020 and 2025 makes constituency-level statistics fragile.

4. **Census 2020 demographics applied to 2025 boundaries:** Population and demographic estimates are fixed at 2020; 5 years of building completions and migration are unmodelled.

5. **Walkovers:** Marine Parade-Braddell Heights (2025, 5 seats) went uncontested, removing a large constituency from all contested-vote analyses.

6. **Subzone-to-constituency assignment by areal majority:** Subzones straddling boundary lines may be misassigned. Edge effects are unquantified.

7. **Single MCMC seed:** Results should be verified with at least 3 independent seeds to confirm ensemble mixing.
