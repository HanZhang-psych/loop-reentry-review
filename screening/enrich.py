"""Stage 3 — ENRICH.

For records missing an abstract after ingest/dedup (ACM especially), fetch one
by DOI from OpenAlex (primary) then Crossref (fallback). Results are cached on
disk so reruns don't re-hit the APIs.

Records still missing an abstract afterwards are returned separately so they can
be routed to human review rather than silently dropped or auto-excluded.
"""
from __future__ import annotations

import os
import re
import json
import time

import requests

from .common import Record

_PREVIEW_ELLIPSIS_RE = re.compile(r"(?:\.{3}|…)\s*$")


def _load_cache(path: str) -> dict:
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_cache(cache: dict, path: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(cache, fh)


def _reconstruct_inverted_index(inv: dict) -> str:
    """OpenAlex returns abstracts as {word: [positions]}; rebuild the text."""
    if not inv:
        return ""
    positions = [(pos, word) for word, idxs in inv.items() for pos in idxs]
    positions.sort()
    return " ".join(word for _, word in positions)


def _strip_jats(text: str) -> str:
    """Crossref abstracts often contain JATS/XML tags."""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text)).strip()


def _fetch_openalex(doi: str, mailto: str, timeout: int) -> str | None:
    url = f"https://api.openalex.org/works/doi:{doi}"
    try:
        resp = requests.get(url, params={"mailto": mailto}, timeout=timeout)
        if resp.status_code != 200:
            return None
        inv = resp.json().get("abstract_inverted_index")
        text = _reconstruct_inverted_index(inv)
        return text or None
    except (requests.RequestException, ValueError):
        return None


def _fetch_crossref(doi: str, mailto: str, timeout: int) -> str | None:
    url = f"https://api.crossref.org/works/{doi}"
    try:
        resp = requests.get(url, params={"mailto": mailto}, timeout=timeout)
        if resp.status_code != 200:
            return None
        abstract = resp.json().get("message", {}).get("abstract")
        return _strip_jats(abstract) if abstract else None
    except (requests.RequestException, ValueError):
        return None


def _has_sage_source(record: Record) -> bool:
    return any(src.strip().lower().startswith("sage")
               for src in record.source_db.split(","))


def _is_sage_preview_abstract(record: Record) -> bool:
    """SAGE BibTeX exports often include only an abstract preview ending in ellipsis."""
    return (
        bool(record.abstract)
        and record.abstract_source == "export"
        and _has_sage_source(record)
        and bool(_PREVIEW_ELLIPSIS_RE.search(record.abstract.strip()))
    )


def enrich_abstracts(records: list[Record], cfg: dict):
    """Mutates records in place. Returns (n_filled, still_missing_records)."""
    e = cfg["enrich"]
    mailto, delay, timeout = e["mailto"], e["request_delay_sec"], e["timeout_sec"]
    cache = _load_cache(e["cache_file"])

    missing_targets = [r for r in records if not r.abstract]
    preview_targets = [r for r in records if _is_sage_preview_abstract(r)]
    targets = missing_targets + preview_targets
    print(
        f"  {len(missing_targets)} records missing an abstract; "
        f"{len(preview_targets)} SAGE preview abstracts need backfill; "
        "attempting backfill..."
    )

    filled = 0
    for i, r in enumerate(targets, 1):
        force_replace = _is_sage_preview_abstract(r)
        if not r.doi:
            if force_replace:
                r.abstract, r.abstract_source = None, ""
            continue  # no DOI -> cannot look up reliably; left for human review

        if r.doi in cache and (cache[r.doi].get("text") or not force_replace):
            text, src = cache[r.doi]["text"], cache[r.doi]["source"]
        else:
            text, src = _fetch_openalex(r.doi, mailto, timeout), "openalex"
            if not text:
                text, src = _fetch_crossref(r.doi, mailto, timeout), "crossref"
            cache[r.doi] = {"text": text, "source": src if text else ""}
            time.sleep(delay)
            if i % 50 == 0:
                _save_cache(cache, e["cache_file"])

        if text:
            r.abstract, r.abstract_source = text, cache[r.doi]["source"]
            filled += 1
        elif force_replace:
            r.abstract, r.abstract_source = None, ""

    _save_cache(cache, e["cache_file"])
    still_missing = [r for r in records if not r.abstract]
    return filled, still_missing
