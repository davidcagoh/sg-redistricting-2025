"""
verify_refs.py — check every entry in a .bib file against Semantic Scholar.

Usage:
    python verify_refs.py references.bib

Reads SEMANTIC_SCHOLAR_API_KEY from a .env file in the same directory (or
from the environment).  No other dependencies beyond the packages listed below.

Install deps once:
    pip install bibtexparser httpx python-dotenv

Output:
    Prints a summary table to stdout.
    Writes verification_report.md alongside the .bib file.

Statuses:
    VERIFIED        — found via DOI/ArXiv; title matches closely
    LIKELY          — found via title search with high confidence (≥ 0.85)
    UNCERTAIN       — found something but title similarity is low; check manually
    NOT_FOUND       — S2 returned nothing for this entry
"""

from __future__ import annotations

import difflib
import os
import re
import sys
import time
import unicodedata
from pathlib import Path

import httpx

# ── optional .env loading ─────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass  # dotenv optional; key can come from environment directly

# ── bibtexparser ──────────────────────────────────────────────────────────────
try:
    import bibtexparser
    from bibtexparser.bparser import BibTexParser
    from bibtexparser.customization import convert_to_unicode
except ImportError:
    sys.exit("Install bibtexparser:  pip install bibtexparser")

# ── S2 config ─────────────────────────────────────────────────────────────────
S2_BASE = "https://api.semanticscholar.org/graph/v1/paper"
S2_SEARCH = "https://api.semanticscholar.org/graph/v1/paper/search"
S2_FIELDS = "paperId,externalIds,title,authors,year,venue"

_API_KEY = os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "")
HEADERS: dict[str, str] = {"User-Agent": "verify-refs/1.0"}
if _API_KEY:
    HEADERS["x-api-key"] = _API_KEY

# 1 req / sec when authenticated, be a bit more conservative unauthenticated
_MIN_INTERVAL = 1.1 if _API_KEY else 3.0
_last_call: float = 0.0


def _wait() -> None:
    global _last_call
    now = time.monotonic()
    gap = _MIN_INTERVAL - (now - _last_call)
    if gap > 0:
        time.sleep(gap)
    _last_call = time.monotonic()


# ── text normalisation for fuzzy title matching ───────────────────────────────

def _normalise(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = text.lower()
    text = re.sub(r"[^a-z0-9 ]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, _normalise(a), _normalise(b)).ratio()


# ── S2 calls ──────────────────────────────────────────────────────────────────

def _batch_lookup(ids: list[str]) -> list[dict | None]:
    """POST /paper/batch — returns one result per input id (None if not found)."""
    if not ids:
        return []
    results: list[dict | None] = []
    chunk = 500
    for i in range(0, len(ids), chunk):
        batch = ids[i : i + chunk]
        _wait()
        try:
            with httpx.Client(timeout=30, headers=HEADERS) as c:
                r = c.post(
                    f"{S2_BASE}/batch",
                    params={"fields": S2_FIELDS},
                    json={"ids": batch},
                )
                if r.status_code == 429:
                    print("[rate-limit] sleeping 30s …")
                    time.sleep(30)
                    _wait()
                    r = c.post(
                        f"{S2_BASE}/batch",
                        params={"fields": S2_FIELDS},
                        json={"ids": batch},
                    )
                r.raise_for_status()
                results.extend(r.json())
        except Exception as e:
            print(f"[batch] error: {e}")
            results.extend([None] * len(batch))
    return results


def _title_search(title: str) -> dict | None:
    """GET /paper/search — returns best hit or None."""
    _wait()
    try:
        with httpx.Client(timeout=30, headers=HEADERS) as c:
            r = c.get(
                S2_SEARCH,
                params={"query": title, "fields": S2_FIELDS, "limit": 1},
            )
            if r.status_code == 429:
                print("[rate-limit] sleeping 30s …")
                time.sleep(30)
                _wait()
                r = c.get(
                    S2_SEARCH,
                    params={"query": title, "fields": S2_FIELDS, "limit": 1},
                )
            r.raise_for_status()
            data = r.json().get("data") or []
            return data[0] if data else None
    except Exception as e:
        print(f"[search] error for '{title[:60]}': {e}")
        return None


# ── bib parsing ───────────────────────────────────────────────────────────────

def _extract_doi(entry: dict) -> str | None:
    raw = entry.get("doi") or entry.get("DOI") or ""
    raw = raw.strip().rstrip(".,")
    if raw.startswith("https://doi.org/"):
        raw = raw[len("https://doi.org/"):]
    elif raw.startswith("http://dx.doi.org/"):
        raw = raw[len("http://dx.doi.org/"):]
    return raw or None


_ARXIV_RE = re.compile(r"arXiv:?\s*(\d{4}\.\d{4,5}(?:v\d+)?)", re.IGNORECASE)


def _extract_arxiv(entry: dict) -> str | None:
    raw = (entry.get("arxivid") or entry.get("eprint") or "").strip()
    if raw:
        return raw
    for field in ("note", "journal", "howpublished"):
        m = _ARXIV_RE.search(entry.get(field, ""))
        if m:
            return m.group(1)
    return None


def parse_bib(path: Path) -> list[dict]:
    parser = BibTexParser(common_strings=True)
    parser.customization = convert_to_unicode
    with path.open(encoding="utf-8", errors="replace") as f:
        db = bibtexparser.load(f, parser=parser)
    return db.entries


# ── verification ──────────────────────────────────────────────────────────────

VERIFIED_THRESHOLD = 0.85
UNCERTAIN_THRESHOLD = 0.60


def verify(entries: list[dict]) -> list[dict]:
    results: list[dict] = []

    # Split entries into those with an identifier vs. title-only
    with_doi: list[tuple[int, str]] = []
    with_arxiv: list[tuple[int, str]] = []
    title_only: list[int] = []

    for idx, e in enumerate(entries):
        doi = _extract_doi(e)
        arxiv = _extract_arxiv(e)
        if doi:
            with_doi.append((idx, f"DOI:{doi}"))
        elif arxiv:
            with_arxiv.append((idx, f"ARXIV:{arxiv}"))
        else:
            title_only.append(idx)

    # ── batch: DOI ────────────────────────────────────────────────────────────
    if with_doi:
        print(f"Looking up {len(with_doi)} entries by DOI …")
        ids = [s2id for _, s2id in with_doi]
        hits = _batch_lookup(ids)
        for (idx, _), hit in zip(with_doi, hits):
            e = entries[idx]
            bib_title = e.get("title", "")
            if hit and hit.get("paperId"):
                sim = _similarity(bib_title, hit.get("title") or "")
                status = "VERIFIED" if sim >= VERIFIED_THRESHOLD else "UNCERTAIN"
                results.append({
                    "key": e.get("ID", "?"),
                    "bib_title": bib_title,
                    "s2_title": hit.get("title", ""),
                    "s2_year": hit.get("year"),
                    "similarity": round(sim, 2),
                    "status": status,
                    "method": "DOI",
                })
            else:
                results.append({
                    "key": e.get("ID", "?"),
                    "bib_title": bib_title,
                    "s2_title": "",
                    "s2_year": None,
                    "similarity": 0.0,
                    "status": "NOT_FOUND",
                    "method": "DOI",
                })

    # ── batch: ArXiv ──────────────────────────────────────────────────────────
    if with_arxiv:
        print(f"Looking up {len(with_arxiv)} entries by ArXiv ID …")
        ids = [s2id for _, s2id in with_arxiv]
        hits = _batch_lookup(ids)
        for (idx, _), hit in zip(with_arxiv, hits):
            e = entries[idx]
            bib_title = e.get("title", "")
            if hit and hit.get("paperId"):
                sim = _similarity(bib_title, hit.get("title") or "")
                status = "VERIFIED" if sim >= VERIFIED_THRESHOLD else "UNCERTAIN"
                results.append({
                    "key": e.get("ID", "?"),
                    "bib_title": bib_title,
                    "s2_title": hit.get("title", ""),
                    "s2_year": hit.get("year"),
                    "similarity": round(sim, 2),
                    "status": status,
                    "method": "ArXiv",
                })
            else:
                results.append({
                    "key": e.get("ID", "?"),
                    "bib_title": bib_title,
                    "s2_title": "",
                    "s2_year": None,
                    "similarity": 0.0,
                    "status": "NOT_FOUND",
                    "method": "ArXiv",
                })

    # ── title search: one by one ───────────────────────────────────────────────
    if title_only:
        print(f"Searching {len(title_only)} entries by title (slower) …")
        for i, idx in enumerate(title_only):
            e = entries[idx]
            bib_title = e.get("title", "")
            if not bib_title:
                results.append({
                    "key": e.get("ID", "?"),
                    "bib_title": "",
                    "s2_title": "",
                    "s2_year": None,
                    "similarity": 0.0,
                    "status": "UNCERTAIN",
                    "method": "no_title",
                })
                continue
            if i > 0 and i % 10 == 0:
                print(f"  … {i}/{len(title_only)}")
            hit = _title_search(bib_title)
            if hit and hit.get("paperId"):
                sim = _similarity(bib_title, hit.get("title") or "")
                if sim >= VERIFIED_THRESHOLD:
                    status = "LIKELY"
                elif sim >= UNCERTAIN_THRESHOLD:
                    status = "UNCERTAIN"
                else:
                    status = "NOT_FOUND"
                results.append({
                    "key": e.get("ID", "?"),
                    "bib_title": bib_title,
                    "s2_title": hit.get("title", ""),
                    "s2_year": hit.get("year"),
                    "similarity": round(sim, 2),
                    "status": status,
                    "method": "title_search",
                })
            else:
                results.append({
                    "key": e.get("ID", "?"),
                    "bib_title": bib_title,
                    "s2_title": "",
                    "s2_year": None,
                    "similarity": 0.0,
                    "status": "NOT_FOUND",
                    "method": "title_search",
                })

    # sort: NOT_FOUND first, then UNCERTAIN, then rest
    order = {"NOT_FOUND": 0, "UNCERTAIN": 1, "LIKELY": 2, "VERIFIED": 3}
    results.sort(key=lambda r: order.get(r["status"], 9))
    return results


# ── reporting ─────────────────────────────────────────────────────────────────

def _truncate(s: str, n: int) -> str:
    return s if len(s) <= n else s[: n - 1] + "…"


def print_summary(results: list[dict]) -> None:
    counts = {}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1

    print()
    print("=" * 70)
    print(f"  Total: {len(results)}")
    for status in ("VERIFIED", "LIKELY", "UNCERTAIN", "NOT_FOUND"):
        n = counts.get(status, 0)
        flag = " ← check" if status in ("UNCERTAIN", "NOT_FOUND") and n else ""
        print(f"  {status:<12} {n}{flag}")
    print("=" * 70)

    needs_check = [r for r in results if r["status"] in ("UNCERTAIN", "NOT_FOUND")]
    if needs_check:
        print(f"\n{'KEY':<30} {'STATUS':<12} {'SIM':>5}  BIB TITLE")
        print("-" * 90)
        for r in needs_check:
            print(
                f"{_truncate(r['key'], 30):<30} {r['status']:<12} "
                f"{r['similarity']:>5.2f}  {_truncate(r['bib_title'], 50)}"
            )


def write_report(results: list[dict], out_path: Path) -> None:
    lines = [
        "# Citation Verification Report\n",
        f"Checked {len(results)} entries against Semantic Scholar.\n",
        "",
        "| Status | Key | Bib Title | S2 Title | Year | Sim | Method |",
        "|--------|-----|-----------|----------|------|-----|--------|",
    ]
    for r in results:
        lines.append(
            f"| {r['status']} | `{r['key']}` "
            f"| {r['bib_title'][:80]} "
            f"| {r['s2_title'][:80]} "
            f"| {r['s2_year'] or ''} "
            f"| {r['similarity']:.2f} "
            f"| {r['method']} |"
        )
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nReport written to {out_path}")


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("Usage: python verify_refs.py references.bib")

    bib_path = Path(sys.argv[1]).expanduser().resolve()
    if not bib_path.exists():
        sys.exit(f"File not found: {bib_path}")

    if not _API_KEY:
        print(
            "WARNING: SEMANTIC_SCHOLAR_API_KEY not set. "
            "Unauthenticated rate limit is strict — expect slowdowns."
        )

    print(f"Parsing {bib_path.name} …")
    entries = parse_bib(bib_path)
    print(f"Found {len(entries)} entries.\n")

    results = verify(entries)
    print_summary(results)

    report_path = bib_path.parent / "verification_report.md"
    write_report(results, report_path)


if __name__ == "__main__":
    main()
