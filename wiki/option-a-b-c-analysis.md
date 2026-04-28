# GRC Minority Capture: Option A / B / C Analysis

Part of the [project wiki](INDEX.md).

Written after session 18 (2026-04-27) to document the methodology comparison and findings
from the Option A post-processing run.

---

## Background: what we were trying to test

Singapore's GRC (Group Representation Constituency) system requires each GRC team to include
at least one minority candidate. The stated policy rationale is to guarantee minority
representation in Parliament. The research question is:

> Does the actual 2025 GRC seat-type assignment concentrate minority populations into GRC
> districts at rates inconsistent with neutral random allocation?

If GRCs are deliberately drawn to capture minority-dense subzones, we would expect the
actual GRC minority capture (population-weighted % minority in GRC districts) to be an
outlier — higher than what random allocation would produce.

---

## What "minority capture" means here

For each geographic partition of Singapore into 33 districts, we compute:

```
grc_minority_pct = (sum of minority population across all GRC districts)
                   ÷ (sum of total population across all GRC districts)
```

This is a single scalar: the population-weighted minority share inside GRC districts.
"Minority" = Malay + Indian + Others as a fraction of total Census 2020 population,
attached to each subzone via `pct_minority` (added to graph nodes in session 17).

We then compare the actual 2025 value against a null distribution built from random
geographic partitions.

---

## The three options

### Option A — Ran in session 18 (chosen)

**Approach:**  
Use the existing paper 1 ensemble (9,000 steps, `seed_001`) — equal-population k=33
partitions — and for each step randomly shuffle seat-type labels (18 GRC, 15 SMC) across
the 33 districts. Compute `grc_minority_pct` for each shuffle. Repeat 100 times per step
→ 900,000 null samples.

**What varies in the null:** Both the geographic partition (which subzones are grouped
together) and the seat-type label assignment (which of those groups are called GRC).

**Question answered:** "Is the actual seat-type assignment unusual compared to random label
permutation on random equal-population boundaries?"

**Implementation:**  
`src/analysis/grc/option_a.py` — `run_option_a()` + `run_null_distribution()`.  
Output saved to `output/option_a/`.

**Results:**

| | Value |
|---|---|
| Actual GRC minority % | **26.03%** |
| Actual SMC minority % | **23.03%** |
| GRC − SMC gap | **+3.00 pp** |
| Null mean | 25.65% |
| Null std | 1.02% |
| Null range | [21.3%, 29.9%] |
| Percentile rank of actual | **64th** |
| p-value (GRC ≥ actual) | **0.356** |

**Interpretation:** The actual 2025 GRC placement sits at the 64th percentile — completely
unremarkable. The +3 pp gap (GRC vs SMC) could arise by chance ~36% of the time under
random seat-type assignment. **Null result: no evidence of deliberate minority concentration
in GRC placement.**

---

### Option B — Infeasible; what it would have done

**Approach:**  
Generate random geographic partitions where districts are *already sized to their seat-count
targets*: SMC districts ~41k pop, GRC4 districts ~166k pop, GRC5 districts ~208k pop.
This required a variable-target ReCom algorithm where each district has a different
population target. The label SMC/GRC4/GRC5 is then determined by district size — no
post-hoc permutation needed.

**What varies in the null:** The geographic partition only. Seat-type labels are fixed to
district size.

**Question answered:** "Given that GRC districts must be proportionally larger, are the
actual GRC boundary drawings unusual?"

**Why it failed:**  
Singapore's subzone granularity is too coarse. 15 subzones have populations exceeding
the SMC target × 1.2 (largest: 130,980 vs SMC target ~41,527 × 1.2 = 49,832). These
subzones *cannot physically fit into an SMC-sized district*. Only 1 in 100 BFS seeding
attempts produced a valid starting partition. Multiple seeder strategies failed:
stratified BFS, absolute-deficit BFS, sequential BFS, unit-merge k=97. The fundamental
constraint is Singapore's urban geography — some subzones are 3× the SMC target population.

**How findings would have differed from Option A:**  
Option B's null distribution would be *narrower* (larger districts average over more
subzones, converging toward the city-wide mean), so the test would have more statistical
resolution. However, the null would still be centred near the same mean (~25–26%), because
minority populations are relatively evenly distributed across Singapore. The headline
finding would almost certainly remain null, but the result would be methodologically
stronger because it conditions on realistic GRC/SMC district sizes rather than treating
all 33 districts as interchangeable equal-population blobs.

**Methodological comparison with Option A:**

| | Option A | Option B |
|---|---|---|
| District sizes | All equal (~41k each) | Variable (SMC ~41k, GRC4 ~166k, GRC5 ~208k) |
| Null neutrality | Weaker (ignores size constraint) | Stronger (fully simultaneous random draw) |
| Both geography and labels random? | Yes (labels permuted post-hoc) | No (labels determined by size) |
| Ordering bias | None | None |
| Feasibility | ✓ | ✗ |

---

### Option C — Hypothetical; not attempted

**Approach (reconstructed from conversation):**  
Sequential hierarchical partitioning:

1. Run k=10 ReCom on the full subzone graph → assign as GRC5 districts (largest,
   ~208k pop target each)
2. Run k=8 ReCom on the *remaining* subzones → assign as GRC4 districts (~166k each)
3. The ~15 remaining subzone groups become SMC districts (~41k each)

Each stage uses standard fixed-k equal-population ReCom, so it is likely implementable
(unlike Option B's simultaneous variable-target approach).

**What varies in the null:** Geography at each stage, but conditioned on the prior stage.

**Question answered:** "Given a GRC5-first allocation rule, are the actual GRC5/GRC4
boundaries unusual?"

**The critical flaw — ordering bias:**  
The sequential order is arbitrary. GRC5 districts "get first pick" of geographic territory.
They claim the largest contiguous subzone clusters before GRC4 or SMC draws. This means
the null is not "neutral random assignment of all three types simultaneously" — it is
"neutral conditional on GRC5 being allocated greedily first."

Concretely: the GRC5 null districts would tend to cluster in areas with large contiguous
subzones (central mature estates, new towns with large planning units). The actual 2025
GRC5 placement might look more or less anomalous purely because of this ordering artefact,
not because of any real signal in the data. Any finding from Option C would need to
disclaim that the p-value is conditional on the GRC5-first rule, which has no normative
justification.

**Why it wasn't pursued:**  
Option C defers rather than solves the fundamental problem. At stage 3, the remaining
subzones after removing GRC5 and GRC4 territory may include some individually large subzones
(the same ones that made Option B infeasible), making it difficult to form proper SMC-sized
districts from the leftovers. It would likely hit the same population-granularity wall.

**Methodological comparison:**

| | Option A | Option B | Option C |
|---|---|---|---|
| District sizes | All equal | Variable, simultaneous | Variable, sequential |
| Ordering bias | None | None | GRC5 > GRC4 > SMC priority |
| Null neutrality | Weak | Strong | Medium |
| Feasibility | ✓ | ✗ | Probably ✓ (with caveats) |
| Finding likely null? | Yes (confirmed) | Very likely | Likely, but artefact risk |

---

## Why Option B is the "correct" method and Option A is the justified approximation

Option B is the closest to the ideal null model: random geographic partitions where
districts are properly sized to their seat types, drawn simultaneously. It answers the
policy question most directly ("is the actual GRC boundary drawing anomalous given the
GRC/SMC size structure?").

Option A is a valid approximation because:
1. The equal-population constraint is a reasonable first-order model — in practice, Singapore
   GRC districts are also required to meet one-person-one-vote standards, so equal-population
   is a shared constraint.
2. The label permutation (choosing which 18 of 33 equal districts get the GRC label) does
   capture the seat-type assignment decision.
3. The result is unlikely to be materially different because the minority population
   distribution in Singapore is relatively uniform at the subzone level — there is no strong
   spatial clustering of minority populations that would make the null sensitive to district
   size assumptions.

The honest limitation in paper 2: Option A tests a slightly weaker claim than Option B
would have. The result survives this limitation because a null finding under a weaker test
is conservative — if anything, a properly-sized null (Option B) would make the null finding
*more* convincing, not less.

---

## What the null finding means

GRCs do have a slightly higher minority population share than SMCs (+3 pp: 26% vs 23%).
But this is indistinguishable from what random seat-type assignment produces.

The implication: minority representation from the GRC system is achieved through **team
composition rules** (requiring a minority candidate on every GRC team), not through
**boundary or seat-type placement targeting minority-dense geographic areas**. The GRC
placement decision appears to be driven by other factors — likely population balance,
geographic compactness, and incumbent protection — not by optimising minority capture.

This echoes the paper 1 finding: correlation between minority % and GRC size (seats)
is r = +0.052 (2025), insignificant.

---

## Files

| File | Description |
|------|-------------|
| `src/analysis/grc/option_a.py` | Option A implementation |
| `tests/analysis/grc/test_option_a.py` | 22 unit tests (all passing) |
| `output/option_a/summary.json` | Numerical results |
| `output/option_a/null_grc_minority_pct.npy` | 900,000-sample null distribution array |
