# Project Wiki — Singapore Electoral Redistricting Analysis

## Status (2026-04-27, session 18)

**Paper 1 published (SocArXiv).** Paper 2 analysis underway: Option A null result obtained.

| Phase | Status |
|-------|--------|
| Phase 0–5: Pipeline | ✅ complete |
| **Electoral profile analysis** | ✅ complete — findings.md |
| **Boundary permutation test** | ✅ complete — p=0.012 |
| **Paper 1** | ✅ published on SocArXiv (April 2026) |
| **MCMC robustness** | ✅ complete — seed_001 primary, seed_002 checked |
| **pct_minority on graph nodes** | ✅ complete |
| **Option A: GRC minority capture** | ✅ complete — null result (64th pct, p=0.356) |
| **Paper 2 draft** | 🔴 not started |

## Next steps (immediately actionable)

1. Plot null distribution histogram with actual marker → `output/option_a/figure_null_hist.png`
2. Begin `writeup/paper2/paper.tex` draft (method + null finding + interpretation)
3. Decide framing: does paper 2 lead with the null, or hold it for §4 after method section?

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
| [Findings](findings.md) | All quantitative results (MCMC, malapportionment, demographics, permutation test) |
| [Paper Plan](paper-plan.md) | Two-paper structure, dissemination strategy, paper 2 scope |
| [Option A/B/C Analysis](option-a-b-c-analysis.md) | Method comparison memo: GRC minority capture options, null result, interpretation |

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
