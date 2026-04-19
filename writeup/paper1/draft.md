# Boundary Changes and Competitive Seat Exclusion in Singapore's 2025 Redistricting: An Ensemble-Based Test

**David Goh**
April 2026

---

## 1. Introduction

Singapore's 2025 general election produced a striking result: the ruling People's Action Party won 87 of 97 parliamentary seats — its highest proportion since 2015 — while receiving 65.6% of the popular vote. The Workers' Party, the only credible opposition, held its two existing Group Representation Constituencies but gained no new ground despite fielding a full slate and running a disciplined campaign. The opposition seat count was the lowest in two decades of contested elections.

The election took place less than three weeks after the Electoral Boundaries Review Committee released its report. Singapore's boundaries are redrawn before every general election, and 2025 was no exception: 114 of 332 planning subzones changed their constituency allocation, affecting approximately 1.3 million residents. Several high-profile marginal seats from 2020 — constituencies where the PAP's margin was slim enough to be plausibly at risk — were restructured or dissolved.

This paper asks a specific, narrow question: was the allocation of those 114 changed subzones politically anomalous?

The question is narrow by design. We are not asking whether Singapore's electoral system is fair. It is not, in the sense that it consistently produces large seat majorities from moderate vote pluralities — but as we will show, that effect is structural, driven by the Group Representation Constituency block-vote mechanism rather than by how boundaries are drawn. Nor are we asking whether boundaries were drawn to create misshapen partisan districts in the manner of American partisan gerrymandering. The evidence on that point runs the other way.

The specific question — were the changed subzones assigned in a way that is consistent with a neutral redistribution? — can be answered with a statistical test. Using an approach inspired by Herschlag and Mattingly's (2018) ensemble analysis of North Carolina's congressional map, we generate a null distribution for what competitive-origin subzone allocations would look like under random redistribution, and we measure where Singapore's actual redistricting falls within that distribution.

The answer is: at the 1.2nd percentile. Among 114 subzones that changed constituency, not one from a competitive 2020 constituency ended up in a competitive 2025 constituency — when 3.2 would be expected by chance. The exact probability of this result under the null hypothesis is p = 0.012.

The anomaly has a specific structure, which we describe in detail. The new competitive seat in 2025 was built from stronghold population, not from the populations of the three dissolved competitive constituencies. Those populations were absorbed into safe or walkover districts. The competitive electoral geography was, in effect, reset: the places that were battlegrounds in 2020 are no longer battlegrounds in 2025, and the new battlegrounds are in entirely different communities.

What this finding cannot show is also worth stating up front. It cannot establish intent. The same pattern is consistent with administrative population rebalancing that happened to relocate competitive seats geographically. The test demonstrates that the pattern is statistically unlikely under randomness; it cannot distinguish a deliberate strategy from coincidence. We return to this distinction throughout.

---

## 2. Background

### 2a. The Group Representation Constituency system

Singapore's parliament uses a hybrid of single-member constituencies (SMCs) and Group Representation Constituencies (GRCs). GRCs are multi-member constituencies where a team of 3 to 5 candidates stands together, and the team that wins a plurality takes all seats in the constituency. Since 1988, GRCs have been justified primarily on ethnic representation grounds: each GRC team must include at least one candidate from an ethnic minority group (Malay, Indian, or Other), which the government argues prevents minority communities from being locked out of parliament by simple-majority single-member voting.

The structural consequence of the GRC system is that it amplifies pluralities into seat bonuses. A party that wins a 5-seat GRC by a single vote wins 5 seats; a party that loses by a single vote wins zero. This winner-takes-all property, applied at the constituency level across seats that range in size from 1 to 5, means that the seat-share-to-vote-share ratio is considerably higher in Singapore than in a comparable single-member-plurality system like the UK's.

In a standard single-member-plurality system, a 60% national vote share would typically produce approximately 60–70% of seats, depending on the geographic concentration of the vote. In Singapore, 60–65% of the vote produces roughly 89% of seats. This is not because the boundaries are drawn to waste opposition votes in the way that American partisan gerrymandering operates. It is because a 5-seat GRC won 55–45 produces a 5:0 seat split, not a 3:2 split.

### 2b. Singapore's seat–vote gap in numbers

The scale of seat magnification in recent elections:

| Year | PAP vote share | PAP seat share | Seat–vote gap | Efficiency gap |
|------|---------------|---------------|---------------|----------------|
| 2020 | 61.2% | 89.3% | +28.0 pp | 16.2% |
| 2025 | 65.6% | 89.7% | +24.1 pp | 7.3% |

The efficiency gap — a measure developed to quantify partisan gerrymandering in the US context — was 16.2% in 2020. For reference, the US Supreme Court in *Rucho v. Common Cause* (2019) examined maps with efficiency gaps in the 10–16% range as potential constitutional violations. Singapore's 2020 efficiency gap falls in that range, though the institutional mechanism is different: it is the block-vote system, not boundary manipulation, that drives it.

The votes-per-seat-won figure is more instructive. In 2020, the PAP won each seat with an average of 16,928 votes; opposition parties won each seat with an average of 16,148 votes. The ratio is 0.95 — essentially equal. This is not what partisan gerrymandering looks like. Gerrymandering, as practised in the United States, works by over-concentrating opposition votes in a small number of constituencies (packing) or spreading them thinly across many constituencies where they cannot win (cracking). Both techniques would show up as a significant disparity in votes-per-seat. The near-parity in Singapore means the seat–vote gap is produced elsewhere — in the multi-seat block-vote mechanism, not in the geographic drawing of district lines.

### 2c. The ensemble approach

Herschlag and Mattingly (2018) introduced the use of Markov Chain Monte Carlo (MCMC) sampling to evaluate whether a specific redistricting plan is an outlier within the space of geometrically valid alternatives. The key insight is that judging a single map as "fair" or "gerrymandered" requires a reference class: what would redistricting look like if it were done neutrally? MCMC sampling generates that reference class by randomly exploring the space of plans satisfying stated constraints — equal population, geographic contiguity, and whatever other neutral criteria apply — and measuring where the actual plan falls in the resulting distribution.

Our implementation adapts this approach to Singapore. We run a 9,000-step ReCom MCMC chain on Singapore's 332 subzones, treating them as the basic building blocks of electoral districts, with equal-population and contiguity as the primary constraints. This generates an ensemble of 9,000 alternative ways to draw 33 constituency-sized units from the same subzones, producing a null distribution against which the actual plans can be compared.

The boundary change permutation test (Section 6) follows the same logic but asks a different question: not "where does the actual boundary configuration fall among all possible configurations?" but rather "given that 114 specific subzones changed constituency, was the allocation of those subzones to destinations politically anomalous?" This is a simpler test with fewer modelling assumptions, which is why we treat it as the headline finding rather than the MCMC results.

---

## 3. MCMC Ensemble Results

Running the MCMC ensemble against both the 2020 and 2025 actual plans produces two striking results and two uninformative ones.

| Metric | Actual 2020 | Actual 2025 | Ensemble mean | Ensemble range | 2020 pctile | 2025 pctile |
|--------|------------|------------|---------------|----------------|-------------|-------------|
| Population deviation | 1.223 | 1.223 | 0.096 | [0.096, 0.096] | 100th | 100th |
| HDB towns split | 12 | 12 | 12 | [12, 12] | 0th | 0th |
| **Planning area splits** | **30** | **28** | **36.3** | [30, 42] | **0th** | **0th** |
| **Compactness (Polsby-Popper)** | **0.435** | **0.418** | **0.353** | [0.314, 0.399] | **100th** | **100th** |

*Table 1: MCMC ensemble metrics. Ensemble drawn from 9,000 post-burn-in ReCom steps, k=33 districts, population tolerance 10%.*

The population deviation result is uninformative because the actual plan uses variable-size GRCs (3–5 seats) while the ensemble models equal-population single-member districts. These are structurally incompatible comparisons. The HDB town-split result shows zero variance across the ensemble — all 9,000 randomly drawn plans split exactly 12 towns, which is also the actual figure. This tells us little beyond the fact that the subzone graph geometry constrains this metric tightly.

The two informative results are striking. **Planning area cohesion**: the 2020 actual plan ties the ensemble minimum (30 planning area splits); the 2025 plan falls *below* the minimum (28 splits), achieving better planning-area cohesion than any of the 9,000 randomly generated maps. **Compactness**: both actual plans are more compact than every plan in the ensemble — more geometrically rounded, not the elongated, snaking shapes that characterise partisan gerrymandering in the American literature.

Together, these results strongly imply that the actual boundaries were drawn with explicit reference to URA planning area lines as an organising constraint, producing constituencies that are administratively coherent and geographically compact. This is the opposite of what partisan boundary manipulation looks like. The GRC system's seat-magnification effects come from the block-vote mechanism, not from the shape of the boundaries.

**Caveat on MCMC interpretation**: The GRC vs SMC institutional mismatch is not a minor limitation. The ensemble generates equal-population single-member units; the actual plans have multi-member constituencies of different sizes. Direct metric comparisons should be interpreted cautiously, and the results should be replicated with at least two to three independent MCMC seeds to confirm ensemble mixing.

---

## 4. The Minority Representation Rationale

The official justification for the GRC system is ethnic minority representation. By requiring each GRC team to include a minority candidate, the government argues, the system ensures that minority communities — Malay, Indian, and Others — are represented in parliament even in areas where they do not form a local majority.

If this rationale were the primary driver of GRC placement and sizing, we would expect GRCs to be placed in areas with higher minority concentrations. We test this directly.

| Year | GRC mean minority % | SMC mean minority % | t-test p-value |
|------|--------------------|--------------------|----------------|
| 2020 | 22.4% | 20.5% | 0.441 |
| 2025 | 22.7% | 18.9% | 0.117 |

*Table 2: Minority population (Malay + Indian) in GRC vs SMC constituencies.*

The difference between GRC and SMC minority percentages is not statistically significant in either year. GRCs are not placed in areas with meaningfully higher minority populations. Additional tests find no significant relationship between minority percentage and GRC size (r = +0.214, p = 0.16 in 2020), and no relationship between minority percentage and opposition vote share.

To be precise about what this does and does not show: the finding closes off the ethnic rationale as the *primary empirical driver* of where GRCs are placed and how large they are. It does not prove that ethnic representation is not an outcome of the GRC system — minority candidates do in fact win seats under GRC rules. It means that the system's structure cannot be explained by the ethnic logic alone, because GRCs are not concentrated in minority-heavy areas.

The finding also fits with the broader picture: a system that places multi-member constituencies without reference to minority population concentration is a system whose constituency allocation is driven by something else. What that something else is — administrative logic, incumbency protection, competitive geography — is what the rest of this paper examines.

---

## 5. Class Politics and Electoral Geography

One of the cleanest empirical findings from the 2020 election is a strong class-politics gradient. Using HDB flat type as a proxy for socioeconomic status — a reasonable proxy in Singapore's context, where flat type is a direct function of income at point of purchase — we find the following correlations with opposition vote share across the 31 contested 2020 constituencies:

| Variable | Pearson r | p-value |
|----------|-----------|---------|
| % 4-room HDB | **+0.483** | **0.006** |
| % Small HDB (≤3-room) | **−0.366** | **0.043** |
| % Indian | −0.302 | 0.099 |
| % Minority (Malay+Indian) | −0.174 | 0.349 |

*Table 3: Correlations with opposition vote share, 2020 contested constituencies (n=31).*

Middle-class areas — constituencies with higher proportions of 4-room flats — supported the opposition significantly more. Working-class areas — higher proportions of ≤3-room flats — supported the PAP more. Minority population had no significant effect. This is a coherent sociological signal: the HDB flat-type gradient tracks economic security, and voters with lower economic security may have stronger incentive to support an incumbent party that controls public housing, welfare, and employment support.

By 2025, this signal had entirely vanished. Across all 30 contested 2025 constituencies, no demographic variable achieves statistical significance. The highest correlation is 4-room HDB at r = +0.32 (p = 0.084), a notable weakening from r = +0.483.

There are two plausible explanations for the vanishing signal, and they are not mutually exclusive. The first is electoral: PAP's vote share rose broadly across Singapore in 2025, possibly reflecting a rally-round-the-government response to economic uncertainty or geopolitical tension, which would compress variance in vote shares and weaken any underlying correlation. The second is structural: boundary changes redistributed the class concentrations that produced the 2020 signal. If middle-class HDB subzones were moved from competitive constituencies into safe or walkover ones, the remaining contested constituencies would look demographically more homogeneous.

We cannot definitively adjudicate between these explanations with available data. What we can say is that the class signal was real in 2020, it is gone in 2025, and the boundary changes we document in Section 6 are at least consistent with a structural redistribution of class-geography.

---

## 6. The Boundary Change Permutation Test

This is the headline finding.

### 6a. The question

114 of Singapore's 332 subzones changed their constituency allocation between the 2020 and 2025 elections. A subzone is the basic unit of Singapore's urban planning geography — a named precinct of roughly a few thousand to sixty thousand residents, drawn by the Urban Redevelopment Authority for administrative purposes.

Of these 114 changed subzones, 52 came from constituencies where the PAP's vote share was below 55% in 2020 — constituencies where the outcome was genuinely competitive by any reasonable standard. We call these "competitive-origin" subzones. In 2020, the competitive PAP constituencies (PAP <55%) were Bukit Batok SMC (54.8%), East Coast GRC (53.4%), and West Coast GRC (51.7%).

Of the same 114 changed subzones, 7 ended up in constituencies where the PAP's vote share was below 55% in 2025 — the new competitive seats. In 2025, only one PAP constituency crossed this threshold: Jalan Kayu SMC (51.5%), where the Workers' Party came within 1.5 percentage points of winning.

The question: how many of the 52 competitive-origin subzones ended up in competitive-destination constituencies?

### 6b. The null distribution

Under random redistribution — if the 114 changed subzones were assigned to their 2025 constituencies without reference to the political characteristics of their origins — we would expect the overlap between competitive origins and competitive destinations to follow a hypergeometric distribution. The expected value is:

$$E[\text{overlap}] = \frac{52 \times 7}{114} = 3.19$$

In other words, if the redistribution were random, roughly 3 of the competitive-origin subzones would be expected to land in competitive 2025 constituencies by chance alone.

### 6c. The actual result: zero

The actual redistricting produced zero overlap.

| | Competitive 2025 destination | Non-competitive 2025 destination | Total |
|---|---|---|---|
| Competitive 2020 origin | **0** | 52 | 52 |
| Non-competitive origin | 7 | 55 | 62 |
| Total | 7 | 107 | 114 |

*Table 4: Competitive-origin vs competitive-destination overlap among 114 changed subzones.*

Not one of the 52 subzones drawn from competitive 2020 constituencies ended up in a competitive 2025 constituency. Fisher's exact test (one-sided): p = 0.012. Hypergeometric CDF P(X ≤ 0): p = 0.012. The actual redistricting lies at the 1.2nd percentile of the null distribution for this statistic — it is a result that would occur by chance approximately 1.2% of the time.

**[Figure 1: combined_summary.png — hypergeometric PMF with actual result marked at X=0, plus seat geography panels]**

### 6d. Where the new competitive seat came from

The one competitive PAP constituency in 2025 that received changed subzones is Jalan Kayu SMC. All 7 subzones feeding into Jalan Kayu came from Ang Mo Kio GRC — which the PAP won with 71.9% of the vote in 2020. A PAP stronghold.

The largest single transfer was FERNVALE, a subzone of 58,800 residents — the single largest subzone move of the entire redistricting exercise. Fernvale was extracted from Ang Mo Kio GRC and placed into the newly formed Jalan Kayu SMC. Jalan Kayu subsequently became the closest-fought seat in the 2025 election, with the Workers' Party winning 48.53% of the vote.

The new competitive seat was, in effect, manufactured from stronghold population. This is not intrinsically suspicious — new constituencies do need to come from somewhere, and somewhere must have been a non-competitive source. But the pattern becomes meaningful when set against what happened to the populations of the three dissolved competitive constituencies.

The competitive constituencies from 2020 were not dissolved into Jalan Kayu. They were absorbed into safe and stronghold territory:

- **West Coast GRC** (PAP 51.7% in 2020): largely merged into West Coast-Jurong West (PAP 60.0% in 2025) and other safe GRCs
- **Bukit Batok SMC** (PAP 54.8% in 2020): dissolved; Bukit Batok Central subzone moved into Jurong East-Bukit Batok GRC (PAP 76.7% in 2025)
- **East Coast GRC** (PAP 53.4% in 2020): survived by name but its PAP share rose to 58.7% in 2025, moving from marginal to safe

The populations of the competitive seats — the communities where the election had actually been close — went to constituencies where the PAP's margin is comfortable or overwhelming. The populations of the PAP's safest territory seeded the one new competitive seat.

### 6e. The relocation of competitive electoral geography

The scale of the competitive-geography shift is worth examining directly. In 2020, there were 7 constituencies where the PAP received less than 60% of the vote — constituencies that could plausibly become competitive with a modest swing. Of these:

- 6 were dissolved, merged, or substantially restructured by the 2025 redistricting
- 1 survived by name (East Coast GRC) but moved from 53.4% to 58.7%

In 2025, there are also 7 constituencies where the PAP received less than 60% of the vote. Of these:

- 6 are entirely new constituencies that did not exist in 2020 under those names or in those configurations
- 1 survived (East Coast, now in a different form)

The competitive electoral landscape has been effectively relocated. The communities that were competitive in 2020 are no longer competitive in 2025. The communities that are competitive in 2025 are different communities — Jalan Kayu in the northeast, Sembawang West, Punggol — that were not competitive in 2020. If competitive voters are defined geographically, they are in new places. If they are defined by community, the communities that were previously competitive have been distributed into safe districts.

**[Figure 2: choropleth_2020_2025.png — geographic map of PAP vote share by constituency, 2020 and 2025 side by side]**

### 6f. A correlation across all changed subzones

Extending the analysis beyond the binary competitive/non-competitive threshold, we compute for each of the 114 changed subzones the relationship between its origin constituency's PAP vote share and the shift in PAP vote share between its origin and destination.

Pearson r between origin PAP% and Δ(destination − origin) PAP% = **−0.444 (p < 0.001)**.

More competitive origin constituencies are associated with larger upward shifts in PAP vote share at the destination. The most competitive subzones moved to the most disproportionately safer seats.

This is consistent with what the binary test finds: competitive-origin subzones were systematically redirected to non-competitive destinations, and the magnitude of the "safety increase" correlates with how competitive the origin was.

---

## 7. Caveats and Limitations

We have been careful to frame the findings above in specific, bounded terms. This section makes the limits explicit.

**The test conditions on the 2025 structure being fixed.** The boundary change permutation test asks whether the allocation of the 114 changed subzones was anomalous, taking the 2025 constituency structure as given. It does not test whether the 2025 structure itself — which constituencies exist, how many seats each has, where GRCs are placed — is anomalous. Testing the GRC placement decision requires an ensemble model that can generate random variable-size multi-member district configurations, which does not currently exist. The permutation test is a test of one layer of the redistricting decision; it cannot see through to the layer above.

**The result is sensitive to the competitive threshold.** We define "competitive" as PAP vote share below 55%. This is a reasonable threshold — it represents constituencies where a modest swing could change the result — but it is a choice. With a tighter threshold (PAP <52%), the 2020 competitive set shrinks and the test loses power. With a broader threshold (PAP <60%), the 2025 competitive set expands and the zero-overlap result would likely change — there are more competitive 2025 destinations for the competitive-origin subzones to land in. Readers should treat the specific p-value of 0.012 as a function of this threshold definition, not as a precise universal probability.

**The 2020 competitive set is small: n=3 constituencies.** With only three competitive constituencies in 2020 (Bukit Batok, East Coast, West Coast), the entire competitive-origin set of 52 subzones comes from just three electoral units. This makes the result fragile to misclassification at the margin: if East Coast's 2020 result (53.4%) is better characterised as "safe" rather than "competitive," the competitive-origin set shrinks substantially.

**Intent cannot be established.** The boundary change permutation test identifies a statistically anomalous pattern, not a cause. The same pattern could be produced by administrative population rebalancing — a genuine effort to equalise constituency sizes and maintain planning-area cohesion — that happened, as a side effect, to relocate competitive seats geographically. Singapore's population grew unevenly between 2020 and 2025; new housing developments in Punggol and Sembawang may have required the addition of new northern constituencies, which would explain why the new competitive seats are in those areas. We cannot rule this out, and we do not attempt to.

What the permutation test establishes is that the observed pattern is unlikely to have arisen by chance, and that it has a specific structure — competitive origins excluded from competitive destinations — which is the kind of structure that would arise from deliberate competitive-seat management. The test cannot distinguish between "deliberate strategy" and "administrative coincidence with the same statistical signature."

**Single MCMC seed.** The MCMC ensemble results in Section 3 were generated with a single random seed (seed 42). The results should be verified with at least 2–3 independent seeds to confirm that the chain mixed adequately and the percentile rankings are stable. This is a standard robustness check that the current analysis has not completed.

**Subzone-level analysis misses within-constituency variation.** Our demographic data is at the subzone level; we do not have precinct-level data. This means we cannot observe within-constituency demographic heterogeneity, and our demographic correlations are at the constituency level (n=31 in 2020), which limits statistical power.

---

## 8. Conclusion

This paper has examined Singapore's 2025 redistricting from three angles: an MCMC ensemble comparison, a demographic analysis, and a boundary change permutation test.

The MCMC results tell the clearest story about what Singapore's redistricting is *not*. The actual constituency boundaries are extreme outliers in planning-area cohesion and geometric compactness — but they are outliers in a direction consistent with administrative logic, not partisan boundary manipulation. Singapore does not have a gerrymander in the conventional sense of bizarrely shaped districts optimised to concentrate or dilute votes. Its boundaries follow planning areas. The large seat bonuses the PAP receives from its vote share come from the GRC block-vote mechanism, not from the geographic drawing of district lines.

The demographic analysis locates a genuine empirical signal that has since disappeared. In 2020, middle-class HDB areas (4-room flats) significantly predicted opposition vote share; by 2025 that signal had vanished. Whether this reflects a uniform PAP swing across all socioeconomic groups, or a redistribution of class geography through boundary changes, cannot be resolved with available data.

The boundary change permutation test is the new finding. Among 114 subzones that changed constituency, those originating in competitive 2020 constituencies were systematically excluded from competitive 2025 constituencies. Not one of 52 competitive-origin subzones ended up in a competitive 2025 constituency, against an expected value of 3.2 under random redistribution. Fisher's exact p = 0.012.

The structure of the anomaly is specific. The one new competitive seat in 2025 (Jalan Kayu) was seeded entirely from Ang Mo Kio stronghold population. The populations of the three dissolved competitive constituencies — the communities where elections had actually been close — were absorbed into safe or walkover districts. The competitive electoral geography was relocated: in 2025, the competitive seats are in entirely different communities from 2020.

Whether this reflects deliberate strategy or administrative coincidence, we cannot say. The data demonstrates the pattern is statistically anomalous. It does not demonstrate intent. Both conclusions deserve to be stated plainly.

What the findings do support is a more focused critique than "gerrymandering." The primary mechanism producing large PAP seat majorities from plurality vote shares is the GRC block-vote system, not boundary drawing. The secondary mechanism — the one identified by the permutation test — is the management of which communities become competitive, through the selective allocation of changed subzones. These are separable claims. The first is well-established in the political science literature; the second is what this paper adds.

The Singapore electoral system's central anomaly is structural and institutional, not geographic. The boundaries are, in a meaningful sense, not the story. The boundaries are the frame; the GRC block-vote rule is the mechanism that operates within the frame. Understanding how the frame gets adjusted — which communities end up in competitive versus safe constituencies — is a tractable empirical question, and this paper provides an initial answer.

---

## Methodological note

**Data.** Electoral results from the Elections Department Singapore (ELD) via data.gov.sg. Subzone geographic boundaries from the Urban Redevelopment Authority (URA) Master Plan 2019. Census demographics from Singapore Census of Population 2020, at subzone level. HDB flat-type counts from HDB property table. All data is publicly available.

**MCMC ensemble.** Implemented using GerryChain (Metric Geometry and Gerrymandering Group, MIT). 9,000 post-burn-in ReCom steps, k=33 districts, population tolerance 10%, random seed 42. Subzone adjacency graph: 332 nodes, 850 edges (rook contiguity).

**Permutation test.** Hypergeometric test and Fisher's exact test. Competitive threshold: PAP vote share <55% in the relevant election year. All computations in Python using `scipy.stats`.

**Code and data.** Available at [repository URL].

---

## References

Herschlag, G., Kang, H. S., Luo, J., Graves, C. V., Bangia, S., Ravier, R., & Mattingly, J. C. (2020). Quantifying gerrymandering in North Carolina. *Statistics and Public Policy*, 7(1), 30–38.

McGhee, E. (2014). Measuring partisan bias in single-member district electoral systems. *Legislative Studies Quarterly*, 39(1), 55–85.

Singapore Elections Department. (2020, 2025). *Parliamentary General Election results*. data.gov.sg.

Urban Redevelopment Authority. (2019). *Master Plan 2019 Subzone Boundary*. data.gov.sg.
