# Project Wiki — Singapore Electoral Redistricting Analysis

## Status (2026-04-13, session 6)

**481 tests passing. Implementation complete. Repo cleaned.**

| Phase | Status |
|-------|--------|
| Phase 0: Foundations | ✅ complete |
| Phase 1: Graph | ✅ complete (332 nodes, 850 edges, 4 islands excluded) |
| Phase 2: MCMC skeleton | ✅ complete (config, seed, constraints, acceptance, recom) |
| Phase 3: Metrics | ✅ complete (population, compactness, splitting, registry) |
| Phase 4: Ensemble driver | ✅ complete (ensemble.py + assign_actual.py) |
| Phase 5: Diff + Reporting | ✅ complete (diff, plots, tables, CLI) |

## Next steps (analysis)

1. `python -m src.analysis.cli assign-actual --year 2020` and `--year 2025`
2. `python -m src.analysis.cli run-ensemble --run-id sg2025 --n-steps 10000`
3. `python -m src.analysis.cli diff --run-id <diff_id> --year-2020-run-id <id> --year-2025-run-id <id>`
4. Review outputs in `output/`

## Wiki files

| File | Contents |
|------|----------|
| `INDEX.md` | This file — status and navigation |
| `session-log.md` | Per-session work log |
| `decisions.md` | Design and methodology decisions |
| `open-questions.md` | Unresolved blockers |
| `implementation-plan.md` | Full 16-task plan with specs |
