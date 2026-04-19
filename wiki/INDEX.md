# Project Wiki — Singapore Electoral Redistricting Analysis

## Status (2026-04-19, session 15)

**Paper 1 compiled to PDF.** `writeup/paper1/paper.tex` is a clean LaTeX build (16 pages). Repo root reorganised. Ready for dissemination prep.

| Phase | Status |
|-------|--------|
| Phase 0: Foundations | ✅ complete |
| Phase 1: Graph | ✅ complete (332 nodes → 327 after filtering) |
| Phase 2: MCMC skeleton | ✅ complete |
| Phase 3: Metrics | ✅ complete |
| Phase 4: Ensemble driver | ✅ complete |
| Phase 5: Diff + Reporting | ✅ complete |
| **Electoral profile analysis** | ✅ complete — findings.md |
| **Boundary permutation test** | ✅ complete — p=0.012 |
| **Paper 1 draft** | ✅ complete — writeup/paper1/draft.md |
| **Paper 1 LaTeX / PDF** | ✅ complete — writeup/paper1/paper.pdf |
| **Publication prep** | 🔴 not started — needs platform + pitch summary |

## Next steps (immediately actionable)

1. Write 1-page pitch summary for Rice Media / Mothership (choropleth lead image, plain-language permutation test)
2. Set up Substack or personal site; establish citable URL before pitching
3. Run second MCMC seed for robustness check (noted as limitation in §7)
4. (Optional) Submit to SSRN or SocArXiv for a citable DOI

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
