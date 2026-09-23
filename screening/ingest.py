"""Stage 1 — INGEST.

Reads every export file in the inputs directory and converts them into a single
list of unified Record objects. Format is detected by file extension; the source
database is taken from the filename stem (e.g. scopus.csv -> "scopus").
"""
from __future__ import annotations

import os
import glob
import re

import rispy
import bibtexparser
import pandas as pd

from .common import (
    Record, normalize_doi, clean_text, clean_year, first_author_surname,
)


def _source_from_filename(path: str) -> str:
    return os.path.splitext(os.path.basename(path))[0].lower()


def _mk_record(source: str, idx: int, *, doi, title, authors, year, abstract, raw_id):
    title = clean_text(title)
    authors = clean_text(authors)
    return Record(
        record_id=f"{source}-{idx:05d}",
        source_db=source,
        doi=normalize_doi(doi),
        title=title,
        authors=authors,
        first_author=first_author_surname(authors),
        year=clean_year(year),
        abstract=clean_text(abstract) or None,
        abstract_source="export" if clean_text(abstract) else "",
        raw_id=clean_text(raw_id),
    )


# --------------------------------------------------------------------------- #
# RIS
# --------------------------------------------------------------------------- #
_RIS_TAG_RE = re.compile(r"^\s*([A-Z0-9]{2})\s*-\s?(.*)$")


def _load_ris_entries(text: str) -> list[dict]:
    entries = rispy.loads(text)
    if entries:
        return entries

    parsed, entry, tag = [], {}, None
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        m = _RIS_TAG_RE.match(line)
        if m:
            tag, value = m.group(1), m.group(2).strip()
            value = re.sub(rf"^{re.escape(tag)}\s*-\s?", "", value).strip()
            if tag == "ER":
                if entry:
                    parsed.append(entry)
                entry, tag = {}, None
                continue
            entry.setdefault(tag, []).append(value)
        elif tag is not None and entry.get(tag):
            value = line.strip()
            if value and value != entry[tag][-1]:
                entry[tag][-1] += " " + value
    if entry:
        parsed.append(entry)
    return parsed


def _first(e: dict, *keys):
    for key in keys:
        value = e.get(key)
        if isinstance(value, (list, tuple)):
            value = next((v for v in value if str(v).strip()), None)
        if value is not None and str(value).strip():
            return value
    return None


def parse_ris(path: str) -> list[Record]:
    source = _source_from_filename(path)
    with open(path, "r", encoding="utf-8-sig", errors="replace") as fh:
        entries = _load_ris_entries(fh.read())
    out = []
    for i, e in enumerate(entries):
        out.append(_mk_record(
            source, i,
            doi=_first(e, "doi", "DO"),
            title=_first(e, "title", "primary_title", "T1"),
            authors=e.get("authors") or e.get("first_authors") or e.get("AU"),
            year=_first(e, "year", "publication_year", "PY"),
            abstract=_first(e, "abstract", "notes_abstract", "N2"),
            raw_id=_first(e, "id", "accession_number") or "",
        ))
    return out


# --------------------------------------------------------------------------- #
# MEDLINE / PubMed (.nbib and PubMed-format .txt)
# --------------------------------------------------------------------------- #
def _looks_like_medline(path: str) -> bool:
    """PubMed MEDLINE files lead with a PMID- tag (and have no RIS TY tag)."""
    with open(path, "r", encoding="utf-8-sig", errors="replace") as fh:
        for _ in range(60):
            line = fh.readline()
            if not line:
                break
            if line.startswith("PMID-"):
                return True
            if line.startswith("TY  -"):
                return False
    return False


def _medline_entries(path: str):
    """Yield each record as a dict[tag] -> list[str], one entry per blank-line block."""
    with open(path, "r", encoding="utf-8-sig", errors="replace") as fh:
        entry, tag = {}, None
        for raw in fh:
            line = raw.rstrip("\n")
            if not line.strip():                    # blank line ends a record
                if entry:
                    yield entry
                entry, tag = {}, None
                continue
            if len(line) > 4 and line[4] == "-" and line[:4].strip().isalnum() \
                    and not line[0].isspace():
                tag = line[:4].strip()
                entry.setdefault(tag, []).append(line[5:].strip())
            elif tag is not None:                   # 6-space-indented continuation
                entry[tag][-1] += " " + line.strip()
        if entry:
            yield entry


def _medline_doi(entry: dict) -> str | None:
    """DOI lives in LID or AID as '<doi> [doi]'."""
    for tag in ("LID", "AID"):
        for val in entry.get(tag, []):
            if "[doi]" in val.lower():
                return val.split()[0]
    return None


def parse_medline(path: str) -> list[Record]:
    source = _source_from_filename(path)
    out = []
    for i, e in enumerate(_medline_entries(path)):
        out.append(_mk_record(
            source, i,
            doi=_medline_doi(e),
            title=" ".join(e.get("TI", [])),
            authors="; ".join(e.get("FAU") or e.get("AU") or []),
            year=(e.get("DP") or [""])[0],          # e.g. "2023 Sep 9" -> clean_year -> 2023
            abstract=" ".join(e.get("AB", [])),
            raw_id=(e.get("PMID") or [""])[0],
        ))
    return out


# --------------------------------------------------------------------------- #
# BibTeX
# --------------------------------------------------------------------------- #
_BIB_ENTRY_RE = re.compile(r"(?m)^\s*@\w+\s*{")
_MALFORMED_BIB_FIELD_RE = re.compile(r"(?m)^\s*[A-Za-z][A-Za-z0-9_-]*\s*:[^\n]*,?\s*$")


def _load_bibtex_entries(text: str) -> list[dict]:
    """Load BibTeX, retrying after removing SAGE-style invalid `field:value` rows."""
    db = bibtexparser.loads(text)
    expected_entries = len(_BIB_ENTRY_RE.findall(text))
    if expected_entries == 0 or len(db.entries) >= expected_entries:
        return db.entries

    cleaned = _MALFORMED_BIB_FIELD_RE.sub("", text)
    retry = bibtexparser.loads(cleaned)
    return retry.entries if len(retry.entries) > len(db.entries) else db.entries


def parse_bibtex(path: str) -> list[Record]:
    source = _source_from_filename(path)
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        entries = _load_bibtex_entries(fh.read())
    out = []
    for i, e in enumerate(entries):
        out.append(_mk_record(
            source, i,
            doi=e.get("doi"),
            title=e.get("title"),
            authors=e.get("author"),
            year=e.get("year"),
            abstract=e.get("abstract"),     # ACM frequently omits this -> backfilled later
            raw_id=e.get("ID") or "",
        ))
    return out


# --------------------------------------------------------------------------- #
# CSV
# --------------------------------------------------------------------------- #
def _pick(row: dict, candidates: list[str]):
    """Case-insensitive lookup of the first matching column."""
    lower = {str(k).strip().lower(): v for k, v in row.items()}
    for cand in candidates:
        v = lower.get(cand.strip().lower())
        if v is not None and str(v).strip() != "":
            return v
    return None


def parse_csv(path: str, csv_field_candidates: dict) -> list[Record]:
    source = _source_from_filename(path)
    try:
        df = pd.read_csv(
            path, dtype=str, keep_default_na=False, encoding="utf-8-sig"
        )
    except UnicodeDecodeError:
        df = pd.read_csv(
            path, dtype=str, keep_default_na=False, encoding="mac_roman"
        )
        print(f"  ! read CSV (Macintosh) encoding: {path}")
    out = []
    for i, row in enumerate(df.to_dict("records")):
        out.append(_mk_record(
            source, i,
            doi=_pick(row, csv_field_candidates["doi"]),
            title=_pick(row, csv_field_candidates["title"]),
            authors=_pick(row, csv_field_candidates["authors"]),
            year=_pick(row, csv_field_candidates["year"]),
            abstract=_pick(row, csv_field_candidates["abstract"]),
            raw_id="",
        ))
    return out


# --------------------------------------------------------------------------- #
# Driver
# --------------------------------------------------------------------------- #
def ingest_all(cfg: dict) -> tuple[list[Record], dict]:
    inputs_dir = cfg["paths"]["inputs_dir"]
    candidates = cfg["ingest"]["csv_field_candidates"]
    records: list[Record] = []
    per_source: dict[str, int] = {}

    files = sorted(glob.glob(os.path.join(inputs_dir, "*")))
    if not files:
        raise FileNotFoundError(
            f"No export files found in {inputs_dir!r}. "
            "Add files like wos.ris, scopus.csv, ieee.ris, psycinfo.ris, acm.bib"
        )

    for path in files:
        ext = os.path.splitext(path)[1].lower()
        if ext == ".nbib" or (ext == ".txt" and _looks_like_medline(path)):
            recs = parse_medline(path)
        elif ext in (".ris", ".txt"):
            recs = parse_ris(path)
        elif ext == ".bib":
            recs = parse_bibtex(path)
        elif ext in (".csv", ".tsv"):
            recs = parse_csv(path, candidates)
        else:
            print(f"  ! skipping unsupported file: {os.path.basename(path)}")
            continue
        per_source[_source_from_filename(path)] = len(recs)
        records.extend(recs)
        print(f"  + {os.path.basename(path):<24} {len(recs):>6} records")

    return records, per_source
