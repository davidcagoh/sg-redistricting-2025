# Project Wiki — Singapore Electoral Redistricting Analysis

## Status (2026-04-17, session 9)

**ISSUE-4 blocking.** BFS seeder fixed ISSUE-1. Chain now runs but rejects nearly all proposals due to `BipartitionWarning`. Fix: `allow_pair_reselection=True` in `src/analysis/mcmc/recom.py`.

| Phase | Status |
|-------|--------|
| Phase 0: Foundations | ✅ complete |
| Phase 1: Graph | ✅ complete (332 nodes, 850 edges, 4 islands excluded) |
| Phase 2: MCMC skeleton | ✅ complete |
| Phase 3: Metrics | ✅ complete |
| Phase 4: Ensemble driver | ✅ complete |
| Phase 5: Diff + Reporting | ✅ complete |
| **Seeding fix (ISSUE-1)** | ✅ BFS fallback — 487 tests green |
| **Chain rejection fix (ISSUE-4)** | 🔴 needs `allow_pair_reselection=True` in recom.py |
| **Ensemble run** | 🔴 blocked by ISSUE-4 |

## Next steps (immediately actionable)

1. `kill 61909` — stop stuck ensemble
2. Fix `src/analysis/mcmc/recom.py`: add `allow_pair_reselection=True` to `MarkovChain(...)`
3. Update tests for the fix (use tdd-guide agent)
4. Re-run: `python -m src.analysis.cli run-ensemble --run-id sg2025 --n-steps 10000`
5. Once complete: `python -m src.analysis.cli diff --run-id diff_sg2025 --year-2020-run-id sg2025 --year-2025-run-id sg2025`
6. Review `output/` plots and summary table for HDB town-splitting and population deviation percentiles

---

## Navigation

### Core pages

| Page | Contents |
|------|----------|
| [Methodology](methodology.md) | Ensemble framework, atomic units, metrics, ReCom chain, Singapore adaptations |
| [Seeding](seeding.md) | Seeding failure root cause, Fix A vs Fix B literature basis, current state |
| [Decisions](decisions.md) | Design and methodology decisions with rationale |
| [Open Questions](open-questions.md) | Unresolved methodological and data questions |
| [Issues](issues.md) | Known blockers and bugs with root cause analysis |
| [Implementation Plan](implementation-plan.md) | Phase-by-phase technical specification |
| [Session Log](session-log.md) | Chronological work log |

### Literature

| Page | Contents |
|------|----------|
| [Literature Index](literature/INDEX.md) | Annotated bibliography of all papers |
| [External Links](literature/links.md) | Data sources, related projects |

### Key cross-links

- Seeding failure (resolved) → [Issues](issues.md#issue-1) → [Seeding](seeding.md) → [Literature](literature/INDEX.md#mattingly-ensembles-and-outliers-2018)
- Chain rejection (blocking) → [Issues](issues.md#issue-4) → fix in `src/analysis/mcmc/recom.py:111`
- Why HDB towns? → [Decisions](decisions.md#why-hdb-towns) → [Methodology](methodology.md#metrics)
- k=33 vs k=31 → [Decisions](decisions.md) → [Open Questions](open-questions.md#grc-multi-member-structure) → [Seeding](seeding.md#fix-b)
- NC literature → [Literature](literature/INDEX.md#herschlag-quantifying-gerrymandering-in-nc-2018) → [Methodology](methodology.md#what-we-cannot-do-partisan-analysis)
