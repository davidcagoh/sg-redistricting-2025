# Next Agent Handoff Prompt

_Read this file first, then read the wiki pages it references before writing a single line of code._

---

## Project in one sentence

We are adapting the Mattingly/Herschlag MCMC ensemble method (originally used to quantify gerrymandering in North Carolina) to evaluate Singapore's 2020 and 2025 electoral boundary changes. The goal is to determine whether the actual electoral maps are statistical outliers in the space of all maps satisfying the same non-partisan criteria (population balance, contiguity, HDB town preservation, compactness).

## What has been built

A complete analysis pipeline (6 phases, 487 tests passing):

```
data/processed/ → io_layer → graph_build → communities → seed_plans → mcmc/ → metrics/ → ensemble → diff → reporting
```

Everything works end-to-end. The only remaining work is unblocking the MCMC chain so it actually runs, then interpreting the results.

**Read before touching anything:**
- `wiki/INDEX.md` — project status and navigation hub
- `wiki/methodology.md` — what the ensemble does and why
- `wiki/issues.md` — the one blocking issue (ISSUE-4)
- `wiki/session-log.md` — what changed in sessions 8 and 9
- `wiki/seeding.md` — the seeding fix just applied (for context)
- `wiki/literature/INDEX.md` — the NC literature this is based on

---

## What is currently broken (ISSUE-4, blocking)

The ensemble chain runs but produces almost zero accepted proposals. Every ReCom step fails with:

```
BipartitionWarning: Failed to find a balanced cut after 1000 attempts.
If possible, consider enabling pair reselection within your
MarkovChain proposal method to allow the algorithm to select
a different pair of districts for recombination.
```

**Root cause:** Singapore's graph has ~36% zero-population subzones (parks, reservoirs, industrial zones). When ReCom merges two adjacent districts, the merged region often contains a contiguous zero-pop cluster. No spanning-tree cut can balance such a region. Without pair reselection, every such step is rejected — effectively freezing the chain.

**The fix is one line.** In `src/analysis/mcmc/recom.py`, function `build_chain()`, around line 111:

```python
return MarkovChain(
    proposal=proposal,
    constraints=constraints,
    accept=acceptance,
    initial_state=initial_partition,
    total_steps=config.n_steps,
    allow_pair_reselection=True,   # ← ADD THIS
)
```

First verify that `allow_pair_reselection` is actually a valid parameter on this version of GerryChain before touching anything: `python -c "from gerrychain import MarkovChain; help(MarkovChain.__init__)"`. If the parameter name differs, find the correct one.

---

## How to proceed — use agents appropriately

### Step 1: tdd-guide agent — write the test first

Before making the fix, use the tdd-guide agent to write or update the test for `build_chain()` in `tests/test_recom.py`. The test should assert that the `MarkovChain` is constructed with `allow_pair_reselection=True`. Run it RED, then apply the fix.

### Step 2: Apply the fix

Edit `src/analysis/mcmc/recom.py` to add `allow_pair_reselection=True`. Run tests GREEN.

### Step 3: code-reviewer agent

Use the code-reviewer agent on `src/analysis/mcmc/recom.py` after the fix. The change is small but it affects chain correctness.

### Step 4: Kill the stuck process and re-run

```bash
kill 61909   # stop the stuck ensemble (verify with: ps aux | grep src.analysis.cli)
python -m src.analysis.cli run-ensemble --run-id sg2025 --n-steps 10000
```

Watch the log — BipartitionWarnings should become rare or absent. Output should appear in `output/runs/sg2025/` within a few minutes.

### Step 5: Run the diff and interpret results

```bash
python -m src.analysis.cli diff \
  --run-id diff_sg2025 \
  --year-2020-run-id sg2025 \
  --year-2025-run-id sg2025
```

Review:
- `output/runs/sg2025/diff_report.json` — percentile ranks
- `output/runs/sg2025/*.png` — distribution histograms with actual plan markers
- `output/runs/sg2025/summary_table.csv` — metric comparison table

Key metrics to interpret:
- `towns_split` — is Singapore's actual plan an outlier in HDB town splitting?
- `max_abs_pop_dev` — is population balance typical or anomalous?
- `mean_pp` — compactness relative to ensemble
- `pln_area_splits` — planning area fragmentation

---

## Key files

| File | What it does |
|------|-------------|
| `src/analysis/mcmc/recom.py` | **THE FIX GOES HERE** — `build_chain()`, line ~111 |
| `tests/test_recom.py` | Tests for recom.py — write test first |
| `src/analysis/cli.py` | CLI entry — `run-ensemble`, `assign-actual`, `diff` |
| `src/analysis/ensemble.py` | Full pipeline driver |
| `src/analysis/diff_2020_2025.py` | Percentile ranking |
| `src/analysis/reporting/` | plots.py + tables.py |
| `wiki/issues.md` | Full root cause write-up for ISSUE-4 |
| `wiki/methodology.md` | What the metrics mean and why |

---

## What NOT to do

- Do not change `k_districts` from 33 to 31 without reading `wiki/decisions.md` and `wiki/open-questions.md` — this is a deliberate methodological choice with documented tradeoffs
- Do not change the seeding logic in `seed_plans.py` — the BFS fallback was just implemented and tested (487 tests green); `wiki/seeding.md` explains the literature basis
- Do not use the actual 2020 or 2025 plan as the chain seed — this is methodologically circular; see `wiki/seeding.md#fix-b`
- Do not run `git push` without explicit user instruction

---

## Running tests

```bash
pytest --cov=src --cov-report=term-missing -q   # full suite; should be 487 passing
pytest tests/test_recom.py -v                    # just recom tests
```
