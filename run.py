#!/usr/bin/env python3
"""
Literature-screening pipeline — command-line entry point.

The workflow — PREPARE, CLEAN, review, APPLY, then SCREEN:

  Step 1 — prepare (scaffold the search):
    python run.py prepare     # seed this search's config.yaml + empty inputs/ folder
  --- human drops the database exports into the search's inputs/ folder and
      edits its config.yaml (mailto, model, criteria) ---

  Step 2 — clean (ingest -> dedup -> prior -> enrich, then STOP for review):
    python run.py clean       # the whole cleaning pass
      # individual steps if you prefer:
      python run.py ingest    # parse exports          -> work/01_ingested.csv
      python run.py dedup     # de-duplicate           -> work/02_deduplicated.csv
                              #   (+ outputs/dedup_removed.csv, dedup_possible_duplicates.csv)
      python run.py prior     # drop already-screened  -> updates work/02_deduplicated.csv
                              #   (opt-in; + outputs/prior_screened_removed.csv)
      python run.py enrich    # backfill abstracts     -> work/03_enriched.csv

  --- human reviews the checkpoint files in outputs/ here:
        dedup_removed.csv             mark `restore` to add a wrongly-removed paper back
        dedup_possible_duplicates.csv set `decision` = merge (redundant) / keep (distinct)
        prior_screened_removed.csv    mark `restore` to add a wrongly-removed paper back
        missing_abstracts.csv         paste an `abstract` for any you can fill by hand ---

  Step 3 — apply (confirm the final data for screening):
    python run.py apply       # apply those decisions + re-enrich  (alias: restore)

  Step 4 — screen:
    python run.py screen      # Claude Batch API screen -> work/04_* + outputs/*
    python run.py screen --dry-run    # estimate cost only, no API call

    python run.py archive     # snapshot inputs+work+outputs into the search's archives/

`all` is intentionally disabled: screening before the duplicate-review checkpoint
is unsafe. A completed `screen` run is archived automatically (disable with
--no-archive). The work/ files are the human checkpoints — inspect them.

Multiple searches: each search is a self-contained run under
data/searches/<name>/ with its OWN complete config.yaml (seeded from
config.template.yaml), plus inputs/work/outputs/prior_screened/archives. The
ROOT config.yaml only selects the active search (paths.active_search), which
`--search <name>` overrides; `python run.py searches` lists them. Drop an
earlier search's results into a later search's prior_screened/ folder to skip
re-screening overlap.
"""
from __future__ import annotations

import os
import csv
import sys
import json
import random
import argparse

from screening.common import (
    Record, load_config, write_records_csv, read_records_csv, record_fieldnames,
    update_counts, read_counts, archive_run, clean_text, read_csv_dicts,
    apply_search_layout, list_searches, load_search_config, set_active_search,
)
from screening import ingest, dedup, enrich, screen, prior


def _p(cfg, *parts):
    return os.path.join(*parts)


def _write_dicts(rows, path, fieldnames):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


# --------------------------------------------------------------------------- #
def stage_ingest(cfg):
    print("[1/4] INGEST")
    records, per_source = ingest.ingest_all(cfg)
    out = _p(cfg, cfg["paths"]["work_dir"], "01_ingested.csv")
    write_records_csv(records, out)
    update_counts(cfg, identified_total=len(records), identified_per_source=per_source)
    print(f"  -> {len(records)} records written to {out}")
    return records, per_source


def stage_dedup(cfg, records=None):
    print("[2/4] DEDUP")
    if records is None:
        records = read_records_csv(_p(cfg, cfg["paths"]["work_dir"], "01_ingested.csv"))
    unique, removed_records, possible_dupes = dedup.deduplicate(records, cfg)
    write_records_csv(unique, _p(cfg, cfg["paths"]["work_dir"], "02_deduplicated.csv"))
    update_counts(cfg, duplicates_removed=len(removed_records),
                  unique_after_dedup=len(unique),
                  dedup_possible_duplicates=len(possible_dupes))

    out_dir = cfg["paths"]["outputs_dir"]
    # every auto-removed duplicate, with a `restore` column the human can mark
    if removed_records:
        rm = _p(cfg, out_dir, "dedup_removed.csv")
        removed_cols = ["restore", "match_type", "duplicate_of", "kept_title",
                        "similarity"] + record_fieldnames()
        _write_dicts(removed_records, rm, removed_cols)
        print(f"  i {len(removed_records)} removed as duplicates -> {rm}  "
              f"(mark `restore` to add any back)")
    # pairs KEPT (not removed) that might still be duplicates -> human decides
    if possible_dupes:
        pd = _p(cfg, out_dir, "dedup_possible_duplicates.csv")
        _write_dicts(possible_dupes, pd, list(possible_dupes[0].keys()))
        print(f"  ! {len(possible_dupes)} possible duplicates KEPT -> {pd}  "
              f"(set `decision` = merge/keep)")
    print(f"  -> {len(records)} in, {len(removed_records)} duplicates removed, {len(unique)} unique")
    return unique, len(removed_records)


def stage_prior(cfg, records=None):
    """Remove records already screened in a prior, overlapping run.

    Runs after DEDUP (which only collapses copies within THIS run) so anything
    dropped here is a genuine cross-run repeat. No-op unless `prior_screened`
    is enabled in config with at least one matching file. Rewrites
    02_deduplicated.csv in place and logs removals (restorable) to
    outputs/prior_screened_removed.csv.
    """
    print("[prior] REMOVE PREVIOUSLY-SCREENED")
    dedup_path = _p(cfg, cfg["paths"]["work_dir"], "02_deduplicated.csv")
    if records is None:
        records = read_records_csv(dedup_path)
    remaining, removed, n_prior = prior.remove_prior_screened(records, cfg)
    if not (cfg.get("prior_screened") or {}).get("enabled", False):
        print("  (disabled — set prior_screened.enabled: true in config to use)")
        return records
    if not n_prior:
        print("  no prior-screened list found (check prior_screened.files) — skipping")
        return records

    write_records_csv(remaining, dedup_path)
    update_counts(cfg, prior_screened_list=n_prior,
                  prior_screened_removed=len(removed),
                  unique_after_dedup=len(remaining))
    if removed:
        rm = _p(cfg, cfg["paths"]["outputs_dir"], "prior_screened_removed.csv")
        _write_dicts(removed, rm, prior.removed_row_fieldnames())
        print(f"  i {len(removed)} already-screened records removed -> {rm}  "
              f"(mark `restore` to add any back)")
    print(f"  -> matched against {n_prior} prior records; "
          f"{len(removed)} removed, {len(remaining)} remain")
    return remaining


def stage_enrich(cfg, records=None):
    print("[3/4] ENRICH")
    if records is None:
        records = read_records_csv(_p(cfg, cfg["paths"]["work_dir"], "02_deduplicated.csv"))
    filled, missing = enrich.enrich_abstracts(records, cfg)
    write_records_csv(records, _p(cfg, cfg["paths"]["work_dir"], "03_enriched.csv"))
    update_counts(cfg, abstracts_backfilled=filled, missing_abstract=len(missing))
    if missing:
        rev = _p(cfg, cfg["paths"]["outputs_dir"], "missing_abstracts.csv")
        _write_dicts([r.to_row() for r in missing], rev, record_fieldnames())
        print(f"  ! {len(missing)} records still lack an abstract -> {rev}  "
              f"(paste an `abstract` to include them)")
    print(f"  -> {filled} abstracts backfilled; {len(missing)} still missing")
    return records, missing


def stage_prepare(cfg):
    """Scaffold a search: its config.yaml + an empty inputs/ folder, then STOP.

    The search's config (seeded from config.template.yaml) and folders are created
    by the loader before this runs; here we just confirm and tell the human what to
    do next — drop the database exports into inputs/, tweak config.yaml, then
    `clean`. Idempotent: re-running never clobbers an existing config."""
    paths = cfg["paths"]
    name = paths.get("search", "?")
    cfg_path = _p(cfg, paths["search_root"], "config.yaml")
    inputs = paths["inputs_dir"]
    os.makedirs(inputs, exist_ok=True)
    existing = sorted(f for f in os.listdir(inputs)) if os.path.isdir(inputs) else []
    bar = "=" * 72
    print("\n" + bar)
    print(f"  SEARCH '{name}' PREPARED — ADD YOUR EXPORTS, THEN CLEAN")
    print(bar)
    print(f"  1. Edit this search's settings (mailto, model, criteria, etc.):")
    print(f"       {cfg_path}")
    print(f"  2. Drop your database exports into:")
    print(f"       {inputs}/")
    print(f"       (one file per database — wos.ris, scopus.csv, ieee.ris, ...)")
    if existing:
        print(f"       [already present: {', '.join(existing)}]")
    print(f"  3. Clean them (ingest -> dedup -> drop prior-screened -> enrich):")
    print(f"       python run.py clean          # '{name}' is now the active search")
    print(bar)
    return cfg


def stage_clean(cfg):
    """Cleaning only: ingest -> dedup -> prior -> enrich, then STOP for review.

    Screening is deliberately a separate command so that no paper is ever
    screened before the duplicate-review checkpoint."""
    recs, _ = stage_ingest(cfg)
    recs, _ = stage_dedup(cfg, recs)
    recs = stage_prior(cfg, recs)
    recs, _ = stage_enrich(cfg, recs)
    work, out = cfg["paths"]["work_dir"], cfg["paths"]["outputs_dir"]
    bar = "=" * 72
    print("\n" + bar)
    print("  CLEANING DONE — REVIEW DUPLICATES BEFORE YOU SCREEN")
    print(bar)
    print(f"  1. Skim   {work}/02_deduplicated.csv        (the survivors)")
    print(f"  2. Review {out}/dedup_removed.csv               (REMOVED as duplicates)")
    print(f"            -> add one back: put 'x' in its `restore` column")
    print(f"  3. Review {out}/dedup_possible_duplicates.csv   (KEPT, maybe duplicates)")
    print(f"            -> set `decision` to 'merge' (redundant) or 'keep' (distinct)")
    prior_removed = _p(cfg, out, "prior_screened_removed.csv")
    if os.path.exists(prior_removed):
        print(f"  3b.Review {out}/prior_screened_removed.csv     (REMOVED, already screened)")
        print(f"            -> add one back: put 'x' in its `restore` column")
    print(f"  4. Review {out}/missing_abstracts.csv           (no abstract found)")
    print(f"            -> paste an `abstract` for any you can fill in by hand")
    print(f"  5. Apply all of the above:    python run.py apply")
    print(f"  6. Then screen:               python run.py screen")
    print(bar)
    return recs


def _read_csv_rows(path):
    return read_csv_dicts(path)


def _record_from_row(row):
    """Reconstruct a Record from a CSV row (ignores any extra columns)."""
    rec = Record(**{k: row.get(k, "") for k in record_fieldnames()})
    rec.year = int(rec.year) if str(rec.year).strip().isdigit() else None
    rec.doi = rec.doi or None
    rec.abstract = rec.abstract or None
    return rec


# vocabularies accepted in the human-editable decision columns
_RESTORE_MARKS = {"x", "y", "yes", "true", "1", "restore"}
_MERGE_MARKS = {"merge", "redundant", "duplicate", "dup", "drop", "same", "yes", "y", "1"}
_KEEP_MARKS = {"keep", "separate", "distinct", "different", "no", "n", "0"}


def stage_apply(cfg):
    """Apply the human's review decisions, then re-enrich and refresh the set.

    Reconciles the three review files produced during cleaning — closing the
    human-in-the-loop before screening:
      * outputs/dedup_removed.csv             rows marked `restore` are added back
      * outputs/prior_screened_removed.csv    rows marked `restore` are added back
      * outputs/dedup_possible_duplicates.csv `decision`=merge drops the candidate;
                                              keep / blank leaves both (blank warns)
      * outputs/missing_abstracts.csv         any `abstract` you typed in is adopted
    Safe to re-run; every decision is idempotent.
    """
    print("[apply] applying your duplicate / abstract review decisions")
    work, out = cfg["paths"]["work_dir"], cfg["paths"]["outputs_dir"]
    dedup_path = _p(cfg, work, "02_deduplicated.csv")
    if not os.path.exists(dedup_path):
        sys.exit(f"  no {dedup_path} found — run `python run.py clean` first.")

    by_id = {r.record_id: r for r in read_records_csv(dedup_path)}
    n_merged = n_restored = n_abstracts = n_undecided = 0
    merged_audit = []          # human-merged candidates, appended to the removed file

    # ---- 1. possible duplicates: merge (drop candidate) or keep (no-op) ----- #
    pd_path = _p(cfg, out, "dedup_possible_duplicates.csv")
    if os.path.exists(pd_path):
        for row in _read_csv_rows(pd_path):
            decision = str(row.get("decision", "")).strip().lower()
            cand = row.get("drop_if_merged_id", "")
            if decision in _MERGE_MARKS:
                rec = by_id.pop(cand, None)
                if rec is not None:
                    n_merged += 1
                    merged_audit.append({
                        "restore": "", "match_type": "possible_duplicate_merged_by_human",
                        "duplicate_of": row.get("keep_id", ""),
                        "kept_title": row.get("keep_title", ""),
                        "similarity": row.get("similarity", ""), **rec.to_row()})
            elif decision in _KEEP_MARKS:
                pass                                   # already separate
            elif cand:
                n_undecided += 1

    # ---- 2. restore papers wrongly removed as duplicates ------------------- #
    rm_path = _p(cfg, out, "dedup_removed.csv")
    if os.path.exists(rm_path):
        for row in _read_csv_rows(rm_path):
            rid = row.get("record_id", "")
            if str(row.get("restore", "")).strip().lower() in _RESTORE_MARKS \
                    and rid and rid not in by_id:
                by_id[rid] = _record_from_row(row)
                n_restored += 1

    # ---- 2b. restore papers wrongly dropped as already-screened ------------ #
    prior_path = _p(cfg, out, "prior_screened_removed.csv")
    if os.path.exists(prior_path):
        for row in _read_csv_rows(prior_path):
            rid = row.get("record_id", "")
            if str(row.get("restore", "")).strip().lower() in _RESTORE_MARKS \
                    and rid and rid not in by_id:
                by_id[rid] = _record_from_row(row)
                n_restored += 1

    # ---- 3. abstracts the human added by hand ------------------------------ #
    miss_path = _p(cfg, out, "missing_abstracts.csv")
    if os.path.exists(miss_path):
        for row in _read_csv_rows(miss_path):
            rid, abstract = row.get("record_id", ""), clean_text(row.get("abstract", ""))
            if abstract and rid in by_id and not by_id[rid].abstract:
                by_id[rid].abstract = abstract
                by_id[rid].abstract_source = "manual"
                n_abstracts += 1

    if not (n_merged or n_restored or n_abstracts):
        print("  no decisions found to apply.")
        print("  mark `restore` in dedup_removed.csv, set `decision` in")
        print("  dedup_possible_duplicates.csv, or fill `abstract` in")
        print("  missing_abstracts.csv, then re-run.")
        if n_undecided:
            print(f"  ({n_undecided} possible-duplicate pair(s) still have no decision)")
        return

    survivors = list(by_id.values())
    write_records_csv(survivors, dedup_path)

    # keep human-merged candidates visible (and restorable) in the audit file
    if merged_audit:
        removed_cols = ["restore", "match_type", "duplicate_of", "kept_title",
                        "similarity"] + record_fieldnames()
        existing = _read_csv_rows(rm_path) if os.path.exists(rm_path) else []
        _write_dicts(existing + merged_audit, rm_path, removed_cols)

    # re-enrich (cache-accelerated); manual + existing abstracts are preserved
    _filled, missing = enrich.enrich_abstracts(survivors, cfg)
    write_records_csv(survivors, _p(cfg, work, "03_enriched.csv"))
    _write_dicts([r.to_row() for r in missing], miss_path, record_fieldnames())
    update_counts(cfg, unique_after_dedup=len(survivors), restored_from_dedup=n_restored,
                  possible_duplicates_merged=n_merged, manual_abstracts=n_abstracts,
                  missing_abstract=len(missing))

    print(f"  possible-duplicate merges applied: {n_merged}"
          + (f"   ({n_undecided} still undecided)" if n_undecided else ""))
    print(f"  papers restored:             {n_restored}")
    print(f"  manual abstracts adopted:    {n_abstracts}")
    print(f"  -> set now {len(survivors)} records; {len(missing)} still lack an abstract")
    print(f"  -> 02_deduplicated.csv and 03_enriched.csv updated. Next: python run.py screen")
    return survivors


def stage_screen(cfg, records=None, dry_run=False, verify_cache=False,
                 config_path="config.yaml", archive=True):
    print("[4/4] SCREEN")
    if records is None:
        records = read_records_csv(_p(cfg, cfg["paths"]["work_dir"], "03_enriched.csv"))
    instructions, reasons = screen.load_criteria(cfg["paths"]["criteria_file"])
    system_prompt = screen.build_system_prompt(instructions, reasons)

    s = cfg["screen"]
    model = s["model"]
    temps = screen.sample_temperatures(cfg)
    samples = len(temps)

    policy = s["missing_abstract_policy"]
    to_screen = [r for r in records if r.abstract]
    no_abstract = [r for r in records if not r.abstract]
    if policy == "screen":
        to_screen, no_abstract = records, []

    # ---- cost estimate ----------------------------------------------------- #
    est = screen.estimate_cost(to_screen, system_prompt, cfg, model, samples)
    print(f"  model: {model}  |  self-consistency: {samples} samples @ temps {temps}")
    print(f"  estimate: {est['records']} records x {samples} samples, "
          f"~{est['input_tokens']:,} in / ~{est['output_tokens']:,} out tokens (uncached)")
    src = "measured" if est["sys_source"] == "api" \
        else "approx char/4 — set ANTHROPIC_API_KEY for an exact count"
    if not cfg["screen"].get("use_prompt_caching"):
        cache_state = "OFF (use_prompt_caching: false)"
    elif est["caching"]:
        cache_state = (f"ON — criteria prompt {est['sys_tokens']} tok >= "
                       f"{est['min_cacheable']} floor; ~{est['cache_read_frac']:.0%} of "
                       f"prefix reads cached")
    else:
        cache_state = (f"OFF — criteria prompt {est['sys_tokens']} tok < "
                       f"{est['min_cacheable']} floor (below {model}'s min cacheable prefix)")
    print(f"  prompt caching: {cache_state}  [{src}]")
    print(f"  total estimate: ~${est['realistic_usd']} realistic  "
          f"(upper bound ~${est['est_usd']}; batch pricing)")
    if est["borderline"]:
        near = "just under" if est["sys_tokens"] < est["min_cacheable"] else "just over"
        print(f"  ! borderline: criteria prompt ({est['sys_tokens']} tok) sits {near} the "
              f"{est['min_cacheable']}-tok cache floor — real caching may differ.")
        print("    confirm it for real with:  python run.py screen --dry-run --verify-cache")

    # ---- optional live caching probe (ground truth, one cheap call pair) ---- #
    if verify_cache:
        if not cfg["screen"].get("use_prompt_caching"):
            print("  verify-cache: skipped — use_prompt_caching is false, so this "
                  "run sends no cache_control and will NOT cache regardless.")
        else:
            print("  verify-cache: probing the live API (2 requests, max_tokens=1)...")
            res = screen.probe_prompt_caching(system_prompt, model, cfg)
            if res.get("error"):
                print(f"  verify-cache: could not probe — {res['error']}")
            elif res["active"]:
                print(f"  verify-cache: CONFIRMED ON — prefix of "
                      f"{res['cached_prefix_tokens']} tok cached; 2nd request read "
                      f"{res['second']['read']} tok from cache "
                      f"(>= {res['min_cacheable']} floor).")
            else:
                print(f"  verify-cache: NOT CACHING — 2nd request read 0 cache tokens "
                      f"({res['second']['input']} tok billed as full input; prefix is "
                      f"below {model}'s {res['min_cacheable']}-tok floor).")

    if dry_run:
        print("  (dry run — no batch submitted)")
        return

    if "ANTHROPIC_API_KEY" not in os.environ:
        sys.exit("  ERROR: set ANTHROPIC_API_KEY before running a live screen.")

    raw_by_sample = screen.screen_records(to_screen, system_prompt, cfg, model, temps)

    # ---- assemble outputs -------------------------------------------------- #
    cols = ["record_id", "source_db", "doi", "authors", "year", "title",
            "abstract_source", "eligible", "reason_for_exclusion", "confidence",
            "agreement", "votes_include", "votes_exclude", "valid_samples",
            "total_samples", "rationale", "notes", "needs_human_review"]

    full_rows, review_rows, audit_log = [], [], []
    by_id = {r.record_id: r for r in records}

    for rid, texts in raw_by_sample.items():
        verdicts = [screen.parse_verdict(t or "{}", reasons) for t in texts]
        v = screen.aggregate_samples(verdicts, cfg)
        flag = screen.review_flag(v, cfg)
        r = by_id[rid]
        note = "insufficient info -> included for full text" \
            if v.get("forced_include_insufficient") else ""
        row = {
            "record_id": rid, "source_db": r.source_db, "doi": r.doi or "",
            "authors": r.authors, "year": r.year or "", "title": r.title,
            "abstract_source": r.abstract_source,
            "eligible": v.get("eligible", ""),
            "reason_for_exclusion": v.get("reason", ""),
            "confidence": v.get("confidence", ""),
            "agreement": v.get("agreement", ""),
            "votes_include": v.get("votes_include", ""),
            "votes_exclude": v.get("votes_exclude", ""),
            "valid_samples": v.get("valid_samples", ""),
            "total_samples": v.get("total_samples", ""),
            "rationale": v.get("rationale", ""),
            "notes": note,
            "needs_human_review": flag,
        }
        full_rows.append(row)
        if flag:
            review_rows.append(row)

        # full audit trail: every raw sample, kept for reproducibility
        audit_log.append({
            "record_id": rid, "model": model,
            "samples": [{"temperature": temps[i], "raw": texts[i],
                         "eligible": verdicts[i]["eligible"],
                         "reason": verdicts[i]["reason"],
                         "rationale": verdicts[i]["rationale"],
                         "parse_error": verdicts[i]["parse_error"]}
                        for i in range(len(texts))],
            "final": {"eligible": v.get("eligible", ""), "reason": v.get("reason", ""),
                      "confidence": v.get("confidence", ""),
                      "agreement": v.get("agreement", ""),
                      "consistent": v.get("consistent", False)},
            "needs_human_review": flag,
        })

    # records never sent to the model (missing abstract under "review" policy)
    for r in no_abstract:
        row = {c: "" for c in cols}
        row.update({
            "record_id": r.record_id, "source_db": r.source_db, "doi": r.doi or "",
            "authors": r.authors, "year": r.year or "", "title": r.title,
            "abstract_source": r.abstract_source,
            "notes": "no abstract available — not screened",
            "needs_human_review": "missing abstract (not screened)",
        })
        full_rows.append(row)
        review_rows.append(row)

    # ---- audit sample of the auto-EXCLUDED pile ---------------------------- #
    # Self-consistency cannot catch systematic errors (the model wrong the same
    # way every sample). Spot-check a seeded random sample of consistent excludes
    # so the real exclusion-error rate on THIS corpus is observable, not assumed.
    audit_cfg = s.get("audit_excludes", {}) or {}
    audit_n = int(audit_cfg.get("sample_size", 0) or 0)
    auto_excludes = [row for row in full_rows
                     if row["eligible"] == "F" and not row["needs_human_review"]]
    n_audit = 0
    if audit_n and auto_excludes:
        rng = random.Random(int(audit_cfg.get("seed", 0) or 0))
        n_audit = min(audit_n, len(auto_excludes))
        for row in rng.sample(auto_excludes, n_audit):
            row["needs_human_review"] = "audit sample (random exclude check)"
            review_rows.append(row)

    work_out = _p(cfg, cfg["paths"]["work_dir"], "04_screening_results.csv")
    _write_dicts(full_rows, work_out, cols)

    audit_path = _p(cfg, cfg["paths"]["work_dir"], "04_raw_samples.jsonl")
    os.makedirs(os.path.dirname(audit_path) or ".", exist_ok=True)
    with open(audit_path, "w", encoding="utf-8") as fh:
        for entry in audit_log:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")

    out_dir = cfg["paths"]["outputs_dir"]
    _write_dicts(full_rows, _p(cfg, out_dir, "screening_results_full.csv"), cols)

    # Only TRULY CONSISTENT includes go to the download list. A majority-but-not-
    # unanimous include is a tentative include: it is held in needs_human_review.csv
    # for confirmation, not auto-added to eligible_for_fulltext.csv.
    eligible = [r for r in full_rows if r["eligible"] == "T" and not r["needs_human_review"]]
    _write_dicts(eligible, _p(cfg, out_dir, "eligible_for_fulltext.csv"), cols)
    _write_dicts(review_rows, _p(cfg, out_dir, "needs_human_review.csv"), cols)

    # ---- PRISMA-style summary (full flow via the counts ledger) ------------ #
    counts = read_counts(cfg)
    update_counts(cfg, screened=len(to_screen), eligible=len(eligible),
                  flagged_for_review=len(review_rows))
    n_excl = sum(1 for r in full_rows if r["eligible"] == "F")
    n_inconsistent = sum(1 for r in full_rows
                         if str(r.get("needs_human_review", "")).startswith("samples not consistent"))
    # majority-include but not consistent: held back from the eligible file
    tentative_includes = sum(1 for r in full_rows
                             if r["eligible"] == "T" and r["needs_human_review"])
    inconsistent_exclude = n_inconsistent - tentative_includes
    reason_counts = {}
    for r in full_rows:
        if r["eligible"] == "F" and r["reason_for_exclusion"]:
            reason_counts[r["reason_for_exclusion"]] = reason_counts.get(r["reason_for_exclusion"], 0) + 1

    per_source = counts.get("identified_per_source", {})
    summary = ["PRISMA FLOW SUMMARY", "=" * 40, "Identification:"]
    if per_source:
        for src, n in sorted(per_source.items()):
            summary.append(f"  {src:<24} {n}")
    summary += [
        f"  Records identified:    {counts.get('identified_total', '?')}",
        f"  Duplicates removed:    {counts.get('duplicates_removed', '?')}",
    ]
    if counts.get("prior_screened_removed"):
        summary.append(
            f"  Previously screened removed: {counts.get('prior_screened_removed')}"
            f"  (matched against {counts.get('prior_screened_list', '?')} prior records)")
    summary += [
        f"  Unique records:        {counts.get('unique_after_dedup', '?')}",
        f"  Abstracts backfilled:  {counts.get('abstracts_backfilled', '?')}",
        "",
        "Screening:",
        f"  Model:                 {model}",
        f"  Self-consistency samples: {samples}",
        f"  Records screened:      {len(to_screen)}",
        f"  Not screened (no abstract): {len(no_abstract)}",
        f"  Eligible for full text (consistent includes): {len(eligible)}",
        f"  Excluded:              {n_excl}",
        f"  Flagged for human review:    {len(review_rows)}",
        f"    leaning include, not consistent (tentative, held back): {tentative_includes}",
        f"    leaning exclude, not consistent: {inconsistent_exclude}",
        f"    audit-sampled excludes: {n_audit}",
        "",
        "Exclusions by reason:",
    ]
    summary += [f"  {k:<40} {v}" for k, v in sorted(reason_counts.items(), key=lambda x: -x[1])]
    summary += [
        "",
        f"NOTE: the {n_audit} audit-sampled excludes are randomly drawn from the "
        "auto-excluded pile. Inspect them; the share you find wrongly excluded "
        "estimates this run's false-exclude rate.",
    ]
    with open(_p(cfg, out_dir, "prisma_summary.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(summary) + "\n")
    print("\n".join("  " + s for s in summary))
    print(f"\n  -> outputs written to {out_dir}/")
    print(f"  -> per-sample audit trail: {audit_path}")
    print(f"  ** review {len(review_rows)} flagged records in needs_human_review.csv **")

    # ---- per-run archive (record keeping) ---------------------------------- #
    if archive and (cfg.get("archive") or {}).get("enabled", True):
        run_dir = archive_run(cfg, config_path, meta={
            "stage": "screen", "model": model, "samples": samples,
            "temperatures": temps, "screened": len(to_screen),
            "eligible": len(eligible), "excluded": n_excl,
            "flagged_for_review": len(review_rows),
        })
        print(f"  -> run archived for record keeping: {run_dir}/")


def stage_archive(cfg, config_path="config.yaml"):
    """Snapshot the current inputs/work/outputs into a timestamped run folder."""
    print("[archive] snapshotting current run state")
    run_dir = archive_run(cfg, config_path, meta={"stage": "archive"})
    print(f"  -> archived to {run_dir}/")
    return run_dir


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser(description="Literature-screening pipeline")
    ap.add_argument("stage", choices=["prepare", "clean", "ingest", "dedup", "prior",
                                      "enrich", "apply", "restore", "screen", "archive",
                                      "searches", "all"])
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--search", default=None,
                    help="which search folder under paths.searches_dir to run "
                         "(overrides paths.active_search)")
    ap.add_argument("--dry-run", action="store_true", help="screen: estimate cost only")
    ap.add_argument("--verify-cache", action="store_true",
                    help="screen: live-probe whether the criteria prompt actually "
                         "caches on this model (one cheap API call pair); pairs with "
                         "--dry-run to check without screening")
    ap.add_argument("--no-archive", action="store_true",
                    help="screen: skip writing the per-run record-keeping archive")
    args = ap.parse_args()
    archive = not args.no_archive

    if args.stage == "searches":
        root = load_config(args.config)
        base = (root.get("paths") or {}).get("searches_dir")
        active = args.search or (root.get("paths") or {}).get("active_search")
        found = list_searches(root)
        print(f"searches_dir: {base or '(not set — legacy flat layout)'}")
        for name in found:
            print(f"  {'* ' if name == active else '  '}{name}")
        if not found:
            print("  (none yet)")
        return

    # load the ACTIVE search's own config (root config only selects the search);
    # `prepare` scaffolds a brand-new search (seeds its config + inputs folder).
    creating = args.stage == "prepare"
    if creating and not args.search:
        sys.exit("  prepare requires --search NAME (the search to scaffold), e.g.\n"
                 "      python run.py prepare --search 2025_update\n"
                 "  it becomes the active search, so later commands need no --search.")
    cfg, name = load_search_config(args.config, args.search, create=creating)
    # derive this search's inputs/work/outputs/prior_screened/archives paths
    apply_search_layout(cfg, name, create=creating)
    # scaffolding a search also makes it the active one in the root config, so
    # subsequent commands (clean/apply/screen/validate) need no --search.
    if creating and name:
        if set_active_search(args.config, name):
            print(f"[active] {name} is now the active search in {args.config}")
    if name:
        print(f"[search] {name}  ({cfg['paths']['search_root']}/)")
        # archive the search's OWN config, not the root selector
        config_path = os.path.join(cfg["paths"]["search_root"], "config.yaml")
    else:
        config_path = args.config

    try:
        _dispatch(args, cfg, archive, config_path)
    except FileNotFoundError as e:
        sys.exit(f"  {e}")


def _dispatch(args, cfg, archive, config_path):
    if args.stage == "prepare":
        stage_prepare(cfg)
    elif args.stage == "clean":
        stage_clean(cfg)
    elif args.stage == "ingest":
        stage_ingest(cfg)
    elif args.stage == "dedup":
        stage_dedup(cfg)
    elif args.stage == "prior":
        stage_prior(cfg)
    elif args.stage == "enrich":
        stage_enrich(cfg)
    elif args.stage in ("apply", "restore"):     # 'restore' kept as an alias
        stage_apply(cfg)
    elif args.stage == "screen":
        stage_screen(cfg, dry_run=args.dry_run, verify_cache=args.verify_cache,
                     config_path=config_path, archive=archive)
    elif args.stage == "archive":
        stage_archive(cfg, config_path=config_path)
    elif args.stage == "all":
        sys.exit(
            "  'all' is disabled on purpose: screening before the duplicate-review\n"
            "  checkpoint risks discarding wrongly-merged papers. Run the steps\n"
            "  separately:\n"
            "      python run.py prepare    # scaffold the search (config + inputs folder)\n"
            "      #   ... drop your database exports into the search's inputs/ ...\n"
            "      python run.py clean      # ingest -> dedup -> prior -> enrich, then stop\n"
            "      #   ... review removed / possible-duplicate / missing-abstract files ...\n"
            "      python run.py apply      # apply your review decisions\n"
            "      python run.py screen     # screen the reviewed set"
        )


if __name__ == "__main__":
    main()
