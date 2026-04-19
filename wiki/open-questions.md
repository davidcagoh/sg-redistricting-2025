# Open Questions

Part of the [project wiki](INDEX.md). See also: [Decisions](decisions.md) · [Methodology](methodology.md) · [Issues](issues.md)

## Unresolved

1. ~~**What is the primary analysis goal?**~~ — See Resolved.

2. **How to obtain polling district polygons?**  
   PDFs and ZIPs exist in `data/reference/pdfs_to_digitize/`. Options: manual digitization in QGIS, OCR + polygon extraction, community shapefile (if license permits).  
   _Blocking: elector-level spatial analysis._

3. **Are the community KML polling district files authoritative enough to use?**  
   `ge2025_polling_districts.kml` in `data/raw/polling_community/` may be community-derived. Need to verify accuracy against ELD source before relying on it.

4. **Census–subzone match coverage**  
   Some URA subzones have no Census row (non-residential, small). Is this gap material for the intended analysis?

5. **How to handle GRC multi-member structure in ensemble generation?** {#grc-multi-member-structure}  
   US ensemble methods assume single-seat districts. Singapore GRCs hold 3–5 seats each with different target populations. Options: (a) ignore structure — partition into k=33 equal-population units ignoring seat count per unit, (b) fix a seat-count vector and encode target populations per district type. Option (a) loses realism but is tractable. Option (b) requires deciding what the seat-count vector should be — which is itself a policy lever and could be the gamed variable. Related: the actual 2020/2025 plans have 31 districts (not 33); see [Decisions](decisions.md#on-k33-vs-k31) and [Seeding](seeding.md#fix-b) for the k=33 vs k=31 methodological discussion.

6. **What are the HDB town boundaries as a GIS layer?**  
   HDB towns are the natural "communities of interest" for Singapore (analogous to US counties). We have HDB block data in `data/raw/hdb/` but need to confirm whether town-level polygons are derivable or available separately.

## Resolved

1. **What is the primary analysis goal?** — Resolved 2026-04-12.  
   Primary: community-of-interest splitting (HDB towns as communities, counting cross-boundary splits in ensemble vs. actual plan). Secondary: population deviation outlier test. Partisan seat analysis is not feasible due to absence of public precinct-level vote returns. See `decisions.md`.

2. **Why does BFS seeding produce non-contiguous districts on the real graph?** — Resolved 2026-04-17.  
   Node 317 is an isolated subzone (pop=50, no adjacency edges). The old `filter_for_mcmc(min_pop=1)` default kept it, and the BFS remainder-assignment loop assigned it to a non-adjacent district. Fixed by changing `filter_for_mcmc` default to `min_pop=float("inf")`. See `decisions.md`.

3. **Is the 2020→2025 subzone reassignment recoverable from GeoJSON diff?** — Resolved 2026-04-18 (session 13).  
   Yes. `src/analysis/boundary_permutation.py` recovers 114 changed subzones by spatial join of 2020 and 2025 electoral boundary GeoJSONs to URA subzones. Full permutation test built on this assignment. See `findings.md §6`.
