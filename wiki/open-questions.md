# Open Questions

## Unresolved

1. **What is the primary analysis goal?**  
   Options: (a) population deviation across constituencies, (b) ethnic composition per GRC/SMC, (c) boundary change diff 2020→2025, (d) elector count vs. population mismatch.  
   _Blocking: nothing can be scoped until this is answered._

2. **How to obtain polling district polygons?**  
   PDFs and ZIPs exist in `data/reference/pdfs_to_digitize/`. Options: manual digitization in QGIS, OCR + polygon extraction, community shapefile (if license permits).  
   _Blocking: elector-level spatial analysis._

3. **Are the community KML polling district files authoritative enough to use?**  
   `ge2025_polling_districts.kml` in `data/raw/polling_community/` may be community-derived. Need to verify accuracy against ELD source before relying on it.

4. **Census–subzone match coverage**  
   Some URA subzones have no Census row (non-residential, small). Is this gap material for the intended analysis?

## Resolved

_None yet._
