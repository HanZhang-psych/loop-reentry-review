"""Stage 2 — DEDUP.

Two passes:
  1. Exact match on normalized DOI.
  2. Fuzzy match (title similarity + year window + first-author check) on the
     remainder, to catch duplicates that lack a DOI in one or more databases.

Possible-duplicate pairs (similarity in [review_band, threshold)) are NOT merged
automatically; both records are KEPT in the set and written to a review file for
a human to adjudicate (merge or keep).
"""
from __future__ import annotations

from rapidfuzz import fuzz

from .common import Record, normalize_title


def _merge_sources(keep: Record, dup: Record) -> None:
    """Record that `keep` was also found in `dup`'s database, and fill gaps."""
    srcs = set(keep.source_db.split(",")) | set(dup.source_db.split(","))
    keep.source_db = ",".join(sorted(s for s in srcs if s))
    # opportunistically fill missing fields from the duplicate
    if not keep.abstract and dup.abstract:
        keep.abstract, keep.abstract_source = dup.abstract, dup.abstract_source
    if not keep.doi and dup.doi:
        keep.doi = dup.doi
    if not keep.year and dup.year:
        keep.year = dup.year


def _removed_row(dup: Record, keeper: Record, match_type: str, score) -> dict:
    """A human-editable record of one removed duplicate (for dedup_removed.csv).

    Carries the full removed record plus context, and a `restore` column the
    reviewer marks to add a falsely-flagged paper back before screening.
    """
    return {
        "restore": "",                      # put 'x' here to add this paper back
        "match_type": match_type,           # doi_exact | fuzzy_title
        "duplicate_of": keeper.record_id,   # the record it was merged into
        "kept_title": keeper.title,
        "similarity": score,                # 100 for DOI-exact, else fuzzy score
        **dup.to_row(),
    }


def deduplicate(records: list[Record], cfg: dict):
    """Returns (unique_records, removed_records, possible_duplicates).

    `removed_records` is a list of human-editable dicts (see _removed_row): one
    per auto-merged duplicate, so the reviewer can see exactly what was dropped
    and restore any false positive. `possible_duplicates` is one dict per pair
    that was just below the merge threshold and KEPT, for the human to decide.
    """
    d = cfg["dedup"]
    threshold = d["fuzzy_title_threshold"]
    review_band = d["fuzzy_review_band"]
    year_window = d["year_window"]

    # ---- Pass 1: exact DOI ------------------------------------------------- #
    by_doi: dict[str, Record] = {}
    no_doi: list[Record] = []
    unique: list[Record] = []
    removed_records: list[dict] = []

    for r in records:
        if r.doi:
            if r.doi in by_doi:
                keeper = by_doi[r.doi]
                _merge_sources(keeper, r)
                removed_records.append(_removed_row(r, keeper, "doi_exact", 100.0))
            else:
                by_doi[r.doi] = r
                unique.append(r)
        else:
            no_doi.append(r)

    # ---- Pass 2: fuzzy title for the DOI-less remainder -------------------- #
    # Compare each no-DOI record against everything kept so far (DOI-matched +
    # already-accepted no-DOI records). Blocking by year keeps this tractable.
    possible_dupes = []
    norm_cache = {id(u): normalize_title(u.title) for u in unique}

    for r in no_doi:
        nt = normalize_title(r.title)
        best_score, best_match = 0.0, None
        for u in unique:
            if r.year and u.year and abs(r.year - u.year) > year_window:
                continue
            score = fuzz.token_sort_ratio(nt, norm_cache.get(id(u), normalize_title(u.title)))
            if score > best_score:
                best_score, best_match = score, u

        if best_match is not None and best_score >= threshold:
            # author check guards against near-identical titles from different works
            if (not r.first_author or not best_match.first_author
                    or fuzz.ratio(r.first_author, best_match.first_author) >= 80):
                _merge_sources(best_match, r)
                removed_records.append(_removed_row(r, best_match, "fuzzy_title", round(best_score, 1)))
                continue

        if best_match is not None and review_band <= best_score < threshold:
            # both records are KEPT; the human decides merge vs keep. `keep_*` is
            # the record already in the set; `drop_if_merged_*` is this candidate,
            # which is removed only if the human sets decision = merge.
            possible_dupes.append({
                "decision": "",   # human: 'merge' if redundant, 'keep' if distinct
                "similarity": round(best_score, 1),
                "keep_id": best_match.record_id, "keep_title": best_match.title,
                "keep_year": best_match.year, "keep_source": best_match.source_db,
                "drop_if_merged_id": r.record_id, "drop_if_merged_title": r.title,
                "drop_if_merged_year": r.year, "drop_if_merged_source": r.source_db,
            })

        unique.append(r)
        norm_cache[id(r)] = nt

    return unique, removed_records, possible_dupes
