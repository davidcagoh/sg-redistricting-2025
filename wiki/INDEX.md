# Project Wiki — Singapore Electoral Redistricting Analysis

## Status (as of 2026-04-12)

Data pipeline is complete. Processed layers are in `data/processed/`. The main open gap is polling district polygons, which exist only as PDFs/KML and require digitization before any elector-level spatial analysis is possible. No analysis or visualization work has started yet.

## Next priorities

1. Digitize / extract polling district polygons
2. Convert raw KML to WGS84 GeoJSON
3. Define the primary analysis question (population deviation, ethnic composition, or boundary change)

## Wiki files

| File | Contents |
|------|----------|
| `INDEX.md` | This file — status and navigation |
| `session-log.md` | Per-session work log (newest entry at top) |
| `decisions.md` | Design and methodology decisions |
| `open-questions.md` | Unresolved blockers and open questions |
