# Project Wiki — Singapore Electoral Redistricting Analysis

## Status (2026-04-17, session 10)

**Ensemble running.** Both ISSUE-4 (BipartitionWarning) and ISSUE-5 (isolated node 317) are fixed. 489 tests green. Chain at ~0.15 s/step; `data/processed/ensemble/sg2025/` writes on completion.

| Phase | Status |
|-------|--------|
| Phase 0: Foundations | ✅ complete |
| Phase 1: Graph | ✅ complete (332 nodes → 327 after filtering; 4 zero-pop islands + node 317 excluded) |
| Phase 2: MCMC skeleton | ✅ complete |
| Phase 3: Metrics | ✅ complete |
| Phase 4: Ensemble driver | ✅ complete |
| Phase 5: Diff + Reporting | ✅ complete |
| **Seeding fix (ISSUE-1)** | ✅ BFS fallback — 489 tests green |
| **Chain rejection fix (ISSUE-4)** | ✅ `allow_pair_reselection=True` + `max_attempts=1000` in recom.py |
| **Isolated node fix (ISSUE-5)** | ✅ `filter_for_mcmc` default `min_pop=float("inf")` |
| **Ensemble run (sg2025, 10 000 steps)** | 🟡 in progress (PID 65626) |
| **Diff + reporting** | 🔴 waiting on ensemble |

## Next steps (immediately actionable)

1. Confirm ensemble completed: `ls data/processed/ensemble/sg2025/`
2. Assign actual plans: `python -m src.analysis.cli assign-actual --year 2020` and `--year 2025`
3. Run diff: `python -m src.analysis.cli diff --run-id diff_sg2025 --year-2020-run-id sg2025 --year-2025-run-id sg2025`
4. Review `data/processed/ensemble/sg2025/` — `metrics.parquet`, `diff_report.json`, `*.png`
5. Focus metrics: `towns_split`, `max_abs_pop_dev`, `mean_pp` — are 2020/2025 plans outliers?

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
