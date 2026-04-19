# Paper 1 Outline

**Working title:** Boundary Changes and Competitive Seat Exclusion in Singapore's 2025 Redistricting: An Ensemble-Based Test

**Register:** Long-form policy/journalism (~4,000–6,000 words). Accessible to an educated non-specialist. Tables and figures inline.

**Headline finding:** Among 114 subzones that changed constituency in 2025, not one from a competitive 2020 constituency ended up in a competitive 2025 constituency — when 3.2 would be expected by chance (p = 0.012).

---

## Structure

### 1. Introduction (~400 words)

- Hook: Singapore's 2025 general election produced its lowest-ever opposition seat count despite a competitive popular vote
- The redistricting question: boundaries were redrawn weeks before the election; 114 of 332 subzones changed constituency
- What we test: using an ensemble approach inspired by Herschlag & Mattingly (2018), we ask whether the allocation of those 114 subzones was politically anomalous
- Preview of findings: yes, at p = 0.012 — and the anomaly has a specific structure

### 2. Background (~600 words)

#### 2a. The GRC system
- Multi-member constituencies (3–5 seats) with block vote
- Official justification: minority representation
- Structural effect: amplifies pluralities into near-sweeps

#### 2b. Singapore's electoral system in numbers
- 2020: 61.2% vote → 89.3% of seats (seat–vote gap: +28 pp, efficiency gap: 16.2%)
- 2025: 65.6% vote → 89.7% of seats (seat–vote gap: +24 pp, efficiency gap: 7.3%)
- These seat magnification effects are primarily structural (block vote), not boundary-driven

#### 2c. The ensemble approach
- Brief: Herschlag & Mattingly (2018) — generate a null distribution of geometrically valid plans; test where the actual plan falls
- Our adaptation: 9,000-step ReCom MCMC on Singapore's 332 subzones; boundary change permutation test on 114 changed subzones

### 3. MCMC ensemble results (~500 words)

- Planning-area cohesion: actual plans fall at 0th percentile — more cohesive than every random plan
- Compactness: 100th percentile — more compact than every random plan
- Interpretation: boundaries follow administrative logic (URA planning areas), not partisan shape manipulation
- Caveat: GRC vs SMC structural mismatch limits direct comparison

**[Table: MCMC metrics — actual vs ensemble]**

### 4. The minority representation rationale (~400 words)

- GRC placement does not predict minority population concentration (t-test p = 0.117–0.441)
- Minority % does not predict GRC size, GRC placement, or vote share
- The stated rationale is not empirically supported as the primary driver of GRC structure
- Note: this does not prove an alternative motive; it closes off one explanation

**[Table: GRC vs SMC minority %, by year]**

### 5. Class politics and demographics (~400 words)

- 2020: 4-room HDB % strongly predicts opposition vote share (r = 0.483, p = 0.006)
- Working-class areas (≤3-room HDB) more pro-PAP (r = −0.366, p = 0.043)
- 2025: signal vanishes (all correlations below significance)
- Possible explanations: uniform PAP swing, or boundary changes redistributed the class signal

### 6. The boundary change permutation test (~900 words) — HEADLINE SECTION

#### 6a. Setup
- 114 subzones changed, 52 from competitive 2020 origins (PAP <55%), 7 destined for competitive 2025 destinations

#### 6b. Null distribution
- Hypergeometric: randomly assign 114 subzones to 2025 structure, keeping totals fixed
- Expected competitive-origin → competitive-destination overlap: 3.19

#### 6c. Result: actual overlap = 0
- Fisher's exact p = 0.012; hypergeometric CDF p = 0.012
- 1.2th percentile of null distribution

**[Figure: combined_summary.png — hypergeometric PMF + seat geography panels]**

#### 6d. What the new competitive seat was actually built from
- Jalan Kayu (PAP 51.5%): seeded entirely from Ang Mo Kio GRC (71.9%), FERNVALE 58,800 residents
- The populations of dissolved competitive seats (West Coast 51.7%, Bukit Batok 54.8%, East Coast 53.4%) went to safe and stronghold constituencies

#### 6e. Competitive seat geography shift
- 2020: 7 competitive PAP seats (PAP <60%); 6/7 were dissolved or merged
- 2025: 7 competitive PAP seats; 6/7 are brand new and geographically relocated
- East Coast survived by name but moved from marginal (53.4%) to safe (58.7%)

#### 6f. Correlation
- r = −0.444 (p < 0.001): more competitive the 2020 origin, the larger the upward PAP% shift at destination

**[Figure: choropleth_2020_2025.png — geographic map]**

### 7. Caveats and limitations (~500 words)

- Test conditions on 2025 structure being fixed; does not test GRC placement itself
- Threshold sensitivity: competitive defined as PAP <55%; expanding to <60% adds destinations
- n=3 competitive 2020 constituencies — result fragile at margin
- Cannot establish intent; the pattern is consistent with administrative population rebalancing
- Single MCMC seed; should be replicated with 2–3 independent seeds
- What would paper 2 need: a variable-size multi-member ensemble algorithm

### 8. Conclusion (~300 words)

- Singapore's redistricting follows administrative boundaries (not partisan shapes) — the boundaries-as-drawn story is the wrong frame
- The GRC block-vote system is the structural mechanism behind seat magnification
- The boundary change permutation test reveals a different and more specific anomaly: competitive-origin populations were systematically excluded from competitive destinations
- The competitive electoral geography was effectively relocated to new communities, while previous competitive zones were absorbed into safe territory
- Whether this reflects deliberate strategy or administrative coincidence cannot be determined — but the pattern is statistically unlikely under randomness

---

## Figures (in order of appearance)

1. **Table 1:** MCMC ensemble metrics — §3
2. **Table 2:** Seat–vote gap 2020 vs 2025 — §2b
3. **Table 3:** GRC vs SMC minority % — §4
4. **Figure 1:** `combined_summary.png` — §6c/6e
5. **Figure 2:** `choropleth_2020_2025.png` — §6e
6. **Figure 3:** `origin_vs_delta.png` (scatter r=−0.444) — §6f (optional; may cut for length)

---

## Notes on register

- Explain the permutation test in plain English before showing the maths
- Lead §6 with the narrative (Jalan Kayu / Fernvale story), then formalise
- Caveats are framed as intellectual honesty: "here is exactly what this cannot show"
- Avoid "gerrymandering" as a conclusion — the data supports "statistically anomalous competitive exclusion pattern"
