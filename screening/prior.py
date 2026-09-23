"""Remove records already screened in a previous, overlapping search.

When an earlier search overlaps the current one, papers you already screened will
reappear in the new exports. Deduplication only collapses copies *within* the
current run; it cannot know about a paper you looked at months ago. This pass
closes that gap: given one or more CSVs from a prior run (the pipeline's own
output — e.g. ``data/outputs/screening_results_full.csv``), it drops any current
record that matches a prior one, so nothing already-screened is screened again.

Matching mirrors DEDUP exactly — DOI exact-match first, then fuzzy title within a
year window with a first-author guard — reusing the same thresholds from
``cfg["dedup"]`` so the two passes behave consistently. Every removed record is
written to ``outputs/prior_screened_removed.csv`` with a ``restore`` column, so a
false match can be added back at the same human checkpoint as dedup.
"""
from __future__ import annotations

import glob
import os

from rapidfuzz import fuzz

from .common import (
    Record, normalize_title, normalize_doi, first_author_surname, clean_year,
    read_csv_dicts,
)

# candidate column names in the prior CSV (the pipeline's own output uses the
# lowercase forms; the alternates let a hand-made list work too)
_COLS = {
    "record_id": ["record_id", "id"],
    "doi":       ["doi", "DOI"],
    "title":     ["title", "Title"],
    "year":      ["year", "Year"],
    "authors":   ["authors", "Authors", "author"],
    "decision":  ["eligible", "decision"],
}


def _get(row: dict, field: str) -> str:
    for name in _COLS[field]:
        if row.get(name):
            return row[name]
    return ""


def _load_prior_rows(patterns) -> list[dict]:
    rows = []
    for pattern in patterns:
        for path in sorted(glob.glob(pattern)):
            if not os.path.isfile(path):
                continue
            rows.extend(read_csv_dicts(path))
    return rows


def _removed_row(dup: Record, match_type: str, score, ref: dict) -> dict:
    """A human-editable record of one paper dropped as already-screened.

    Same shape as dedup's removed rows (a leading `restore` column + context),
    so the reviewer works the same way for both files.
    """
    return {
        "restore": "",                          # put 'x' here to add this paper back
        "match_type": match_type,               # doi_exact | fuzzy_title
        "prior_record_id": ref.get("id", ""),   # the matched record in the prior run
        "prior_title": ref.get("title", ""),
        "prior_decision": ref.get("decision", ""),  # its prior eligible/exclude call
        "similarity": score,                    # 100 for DOI-exact, else fuzzy score
        **dup.to_row(),
    }


def removed_row_fieldnames() -> list[str]:
    from .common import record_fieldnames
    return ["restore", "match_type", "prior_record_id", "prior_title",
            "prior_decision", "similarity"] + record_fieldnames()


def remove_prior_screened(records: list[Record], cfg: dict):
    """Drop current records that were screened in a prior run.

    Returns (remaining, removed_rows, n_prior). If the feature is disabled or no
    prior files are found, this is a no-op: (records, [], 0).
    """
    pc = cfg.get("prior_screened") or {}
    if not pc.get("enabled", False):
        return records, [], 0

    prior_rows = _load_prior_rows(pc.get("files") or [])
    if not prior_rows:
        return records, [], 0

    d = cfg["dedup"]
    threshold = d["fuzzy_title_threshold"]
    year_window = d["year_window"]

    # index the prior corpus: DOI -> ref, and a list of (norm_title, year, author, ref)
    prior_by_doi: dict[str, dict] = {}
    prior_titles: list[tuple] = []
    for row in prior_rows:
        ref = {"id": _get(row, "record_id"), "title": _get(row, "title"),
               "decision": _get(row, "decision")}
        doi = normalize_doi(_get(row, "doi"))
        if doi:
            prior_by_doi.setdefault(doi, ref)
        title = _get(row, "title")
        if title:
            prior_titles.append((normalize_title(title), clean_year(_get(row, "year")),
                                 first_author_surname(_get(row, "authors")), ref))

    remaining, removed = [], []
    for r in records:
        # ---- Pass 1: exact DOI --------------------------------------------- #
        if r.doi and r.doi in prior_by_doi:
            removed.append(_removed_row(r, "doi_exact", 100.0, prior_by_doi[r.doi]))
            continue

        # ---- Pass 2: fuzzy title within the year window -------------------- #
        nt = normalize_title(r.title)
        best_score, best_ref, best_author = 0.0, None, ""
        for pt, py, pfa, ref in prior_titles:
            if r.year and py and abs(r.year - py) > year_window:
                continue
            score = fuzz.token_sort_ratio(nt, pt)
            if score > best_score:
                best_score, best_ref, best_author = score, ref, pfa

        if best_ref is not None and best_score >= threshold and (
                not r.first_author or not best_author
                or fuzz.ratio(r.first_author, best_author) >= 80):
            removed.append(_removed_row(r, "fuzzy_title", round(best_score, 1), best_ref))
            continue

        remaining.append(r)

    return remaining, removed, len(prior_rows)
