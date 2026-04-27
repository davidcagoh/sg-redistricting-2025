"""
forward_cites.py — fetch forward citations (papers that cite each entry) for every
                   item in a .bib file, via the Semantic Scholar graph API.

Usage:
    python forward_cites.py references.bib
    python forward_cites.py references.bib --min-year 2020 --limit 50
    python forward_cites.py references.bib --out forward_cites_report.md

Reads SEMANTIC_SCHOLAR_API_KEY from a .env file in the same directory (or from
the environment).

Install deps once:
    pip install bibtexparser httpx python-dotenv tenacity

Output:
    - Prints a per-entry summary table to stdout.
    - Writes a markdown report next to the .bib with the top-N citing papers
      for each entry (sorted by citingPaper citation count, descending).
    - Writes a CSV edge list (source_s2_id, target_s2_id, citing_title, year).

Pipeline per entry:
    1. Resolve the bib entry to an S2 paperId:
         - DOI   → GET /paper/DOI:<doi>
         - ArXiv → GET /paper/ARXIV:<id>
         - else  → GET /paper/search?query=<title>   (top hit)
    2. Paginate GET /paper/{s2_id}/citations (1000/page).
    3. Sort citing papers by citationCount desc, take top --limit.
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
import time
from pathlib import Path

import httpx

# ── optional .env loading ─────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

# ── bibtexparser ──────────────────────────────────────────────────────────────
try:
    import bibtexparser
    from bibtexparser.bparser import BibTexParser
    from bibtexparser.customization import convert_to_unicode
except ImportError:
    sys.exit("Install bibtexparser:  pip install bibtexparser")

# ── S2 config ─────────────────────────────────────────────────────────────────
S2_BASE   = "https://api.semanticscholar.org/graph/v1/paper"
S2_SEARCH = f"{S2_BASE}/search"
RESOLVE_FIELDS = "paperId,externalIds,title,year"
CITING_FIELDS  = (
    "citingPaper.paperId,citingPaper.title,citingPaper.year,"
    "citingPaper.authors,citingPaper.venue,citingPaper.citationCount,"
    "citingPaper.externalIds"
)

_API_KEY = os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "")
HEADERS: dict[str, str] = {"User-Agent": "forward-cites/1.0"}
if _API_KEY:
    HEADERS["x-api-key"] = _API_KEY

_MIN_INTERVAL = 1.1 if _API_KEY else 3.0
_last_call: float = 0.0


def _wait() -> None:
    global _last_call
    now = time.monotonic()
    gap = _MIN_INTERVAL - (now - _last_call)
    if gap > 0:
        time.sleep(gap)
    _last_call = time.monotonic()


# ── bib parsing ───────────────────────────────────────────────────────────────

def _extract_doi(entry: dict) -> str | None:
    raw = (entry.get("doi") or entry.get("DOI") or "").strip().rstrip(".,")
    for prefix in ("https://doi.org/", "http://dx.doi.org/"):
        if raw.startswith(prefix):
            raw = raw[len(prefix):]
    return raw or None


def _extract_arxiv(entry: dict) -> str | None:
    raw = (entry.get("arxivid") or entry.get("eprint") or "").strip()
    return raw or None


def parse_bib(path: Path) -> list[dict]:
    parser = BibTexParser(common_strings=True)
    parser.customization = convert_to_unicode
    with path.open(encoding="utf-8", errors="replace") as f:
        db = bibtexparser.load(f, parser=parser)
    return db.entries


# ── S2 calls ──────────────────────────────────────────────────────────────────

def _get_json(url: str, params: dict) -> dict | None:
    _wait()
    try:
        with httpx.Client(timeout=30, headers=HEADERS) as c:
            r = c.get(url, params=params)
            if r.status_code == 429:
                print("[rate-limit] sleeping 30s …")
                time.sleep(30)
                _wait()
                r = c.get(url, params=params)
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r.json()
    except Exception as e:
        print(f"[s2] error {url}: {e}")
        return None


def resolve_paper_id(entry: dict) -> dict | None:
    """Return {'s2_id','title','year'} or None."""
    doi = _extract_doi(entry)
    arxiv = _extract_arxiv(entry)
    title = entry.get("title", "").strip()

    if doi:
        data = _get_json(f"{S2_BASE}/DOI:{doi}", {"fields": RESOLVE_FIELDS})
        if data and data.get("paperId"):
            return {"s2_id": data["paperId"], "title": data.get("title", ""),
                    "year": data.get("year"), "method": "DOI"}
    if arxiv:
        data = _get_json(f"{S2_BASE}/ARXIV:{arxiv}", {"fields": RESOLVE_FIELDS})
        if data and data.get("paperId"):
            return {"s2_id": data["paperId"], "title": data.get("title", ""),
                    "year": data.get("year"), "method": "ArXiv"}
    if title:
        data = _get_json(S2_SEARCH,
                         {"query": title, "fields": RESOLVE_FIELDS, "limit": 1})
        hits = (data or {}).get("data") or []
        if hits and hits[0].get("paperId"):
            h = hits[0]
            return {"s2_id": h["paperId"], "title": h.get("title", ""),
                    "year": h.get("year"), "method": "title"}
    return None


def fetch_forward_citations(s2_id: str) -> list[dict]:
    """Paginate GET /paper/{id}/citations. Returns list of citingPaper dicts."""
    results: list[dict] = []
    offset = 0
    page_size = 1000
    while True:
        data = _get_json(f"{S2_BASE}/{s2_id}/citations",
                         {"fields": CITING_FIELDS,
                          "limit": page_size, "offset": offset})
        if not data:
            break
        items = data.get("data") or []
        for item in items:
            cp = item.get("citingPaper") or {}
            if cp.get("paperId"):
                results.append(cp)
        if len(items) < page_size:
            break
        offset += len(items)
    return results


# ── reporting ─────────────────────────────────────────────────────────────────

def _truncate(s: str, n: int) -> str:
    return s if len(s) <= n else s[: n - 1] + "…"


def _fmt_authors(authors: list[dict] | None) -> str:
    names = [a.get("name", "") for a in (authors or []) if a.get("name")]
    if not names:
        return ""
    if len(names) > 3:
        return ", ".join(names[:3]) + " et al."
    return ", ".join(names)


def build_report(per_entry: list[dict], limit: int, min_year: int | None) -> str:
    lines = [
        "# Forward Citation Report\n",
        f"Checked {len(per_entry)} entries against Semantic Scholar.  ",
        f"Top {limit} citing papers per entry (sorted by citationCount desc).",
    ]
    if min_year:
        lines.append(f"Only citing papers from year ≥ {min_year}.")
    lines.append("")

    for rec in per_entry:
        lines.append(f"## `{rec['key']}` — {_truncate(rec['bib_title'], 120)}")
        if rec["status"] != "OK":
            lines.append(f"_Status: **{rec['status']}**_\n")
            continue
        lines.append(f"- S2 id: `{rec['s2_id']}`  ")
        lines.append(f"- Total forward citations: **{rec['total']}**  ")
        lines.append(f"- Shown: {len(rec['top'])} (after filters)\n")
        if not rec["top"]:
            lines.append("_No citing papers after filters._\n")
            continue
        lines.append("| # | Year | Cites | Title | Authors | Venue |")
        lines.append("|---|------|-------|-------|---------|-------|")
        for i, cp in enumerate(rec["top"], 1):
            lines.append(
                f"| {i} "
                f"| {cp.get('year') or ''} "
                f"| {cp.get('citationCount') or 0} "
                f"| {_truncate(cp.get('title') or '', 90)} "
                f"| {_truncate(_fmt_authors(cp.get('authors')), 50)} "
                f"| {_truncate(cp.get('venue') or '', 40)} |"
            )
        lines.append("")
    return "\n".join(lines)


def write_edges_csv(per_entry: list[dict], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["source_bib_key", "source_s2_id",
                    "citing_s2_id", "citing_year",
                    "citing_citation_count", "citing_title"])
        for rec in per_entry:
            if rec["status"] != "OK":
                continue
            for cp in rec["top"]:
                w.writerow([rec["key"], rec["s2_id"],
                            cp.get("paperId"), cp.get("year") or "",
                            cp.get("citationCount") or 0,
                            cp.get("title") or ""])


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("bib", type=Path, help="Path to .bib file")
    ap.add_argument("--limit", type=int, default=25,
                    help="Top-N citing papers per entry in the report (default 25)")
    ap.add_argument("--min-year", type=int, default=None,
                    help="Filter out citing papers older than this year")
    ap.add_argument("--out", type=Path, default=None,
                    help="Markdown report output path "
                         "(default: forward_cites_report.md next to the .bib)")
    ap.add_argument("--csv", type=Path, default=None,
                    help="CSV edge list output path "
                         "(default: forward_cites_edges.csv next to the .bib)")
    args = ap.parse_args()

    bib_path = args.bib.expanduser().resolve()
    if not bib_path.exists():
        sys.exit(f"File not found: {bib_path}")

    if not _API_KEY:
        print("WARNING: SEMANTIC_SCHOLAR_API_KEY not set. "
              "Unauthenticated rate limit is strict — expect slowdowns.")

    report_path = args.out or (bib_path.parent / "forward_cites_report.md")
    csv_path    = args.csv or (bib_path.parent / "forward_cites_edges.csv")

    print(f"Parsing {bib_path.name} …")
    entries = parse_bib(bib_path)
    print(f"Found {len(entries)} entries.\n")

    per_entry: list[dict] = []
    for i, e in enumerate(entries, 1):
        key = e.get("ID", "?")
        bib_title = e.get("title", "")
        print(f"[{i}/{len(entries)}] {key} — {_truncate(bib_title, 70)}")

        resolved = resolve_paper_id(e)
        if not resolved:
            per_entry.append({"key": key, "bib_title": bib_title,
                              "status": "NOT_RESOLVED",
                              "s2_id": None, "total": 0, "top": []})
            print("  → NOT_RESOLVED")
            continue

        s2_id = resolved["s2_id"]
        citing = fetch_forward_citations(s2_id)
        total = len(citing)

        if args.min_year:
            citing = [cp for cp in citing
                      if (cp.get("year") or 0) >= args.min_year]

        citing.sort(key=lambda cp: cp.get("citationCount") or 0, reverse=True)
        top = citing[: args.limit]

        per_entry.append({
            "key": key, "bib_title": bib_title,
            "status": "OK", "s2_id": s2_id,
            "total": total, "top": top,
        })
        print(f"  → {total} forward citations (showing top {len(top)}) "
              f"[resolved via {resolved['method']}]")

    # ── outputs ───────────────────────────────────────────────────────────────
    print()
    print("=" * 70)
    ok = sum(1 for r in per_entry if r["status"] == "OK")
    nf = sum(1 for r in per_entry if r["status"] == "NOT_RESOLVED")
    total_cites = sum(r["total"] for r in per_entry if r["status"] == "OK")
    print(f"  Resolved:     {ok}/{len(per_entry)}")
    print(f"  Not resolved: {nf}")
    print(f"  Total forward citations fetched: {total_cites}")
    print("=" * 70)

    report = build_report(per_entry, args.limit, args.min_year)
    report_path.write_text(report, encoding="utf-8")
    print(f"\nReport written to {report_path}")

    write_edges_csv(per_entry, csv_path)
    print(f"Edge list written to {csv_path}")


if __name__ == "__main__":
    main()
