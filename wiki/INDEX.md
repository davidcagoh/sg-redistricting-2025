# Project Wiki — Singapore Electoral Redistricting Analysis

## Status (2026-04-17, session 9)

**Ensemble unblocked.** BFS seeder implemented; running `run-ensemble` now.

| Phase | Status |
|-------|--------|
| Phase 0: Foundations | ✅ complete |
| Phase 1: Graph | ✅ complete (332 nodes, 850 edges, 4 islands excluded) |
| Phase 2: MCMC skeleton | ✅ complete |
| Phase 3: Metrics | ✅ complete |
| Phase 4: Ensemble driver | ✅ complete |
| Phase 5: Diff + Reporting | ✅ complete |
| **Seeding fix** | ✅ BFS fallback implemented |
| **Ensemble run** | 🔄 in progress |

## Next steps

1. `python -m src.analysis.cli run-ensemble --run-id sg2025 --n-steps 10000`
2. `python -m src.analysis.cli diff --run-id <diff_id> --year-2020-run-id sg2025 --year-2025-run-id sg2025`
3. Review `output/` — distribution histograms, summary table, percentile ranks

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

- Seeding failure → root cause in [Issues](issues.md#issue-1) → fix rationale in [Seeding](seeding.md) → literature basis in [Literature](literature/INDEX.md#mattingly-ensembles-and-outliers-2018)
- Why HDB towns? → [Decisions](decisions.md#why-hdb-towns) → [Methodology](methodology.md#metrics)
- k=33 vs k=31 → [Decisions](decisions.md) → [Open Questions](open-questions.md#grc-multi-member-structure) → [Seeding](seeding.md#fix-b)
- NC literature → [Literature](literature/INDEX.md#herschlag-quantifying-gerrymandering-in-nc-2018) → [Methodology](methodology.md#what-we-cannot-do-partisan-analysis)
