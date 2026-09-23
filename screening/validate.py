"""VALIDATION — an OPTIONAL preliminary check that your criteria work.

Run this ONLY if you already have a small, hand-picked set of papers whose
eligibility you know (some you're sure should be INCLUDED, some EXCLUDED). It
lets you sanity-check the criteria wording *before* screening a whole corpus.

Unlike a full run, this does not read a prior screening output. It SCREENS your
hand-labeled papers itself — same model, same criteria, same self-consistency
sampling as `run.py screen` — writes the full per-record results into the
search's `validate/` folder, and then compares the model's verdicts against your
labels: a confusion matrix, recall/specificity, and every disagreement (false
EXCLUDES first — those are the costly ones).

This is a preliminary gut-check on a set YOU chose, not an unbiased performance
estimate — so it deliberately reports point numbers, no confidence interval. If
you tune the criteria to fix a miss you see here, you've tuned to this set:
re-check on a FRESH hand-labeled set before trusting the wording.

The labels CSV is handcrafted. Required columns: record_id, human_label (T/F),
and enough text to screen (title and/or abstract). Optional: authors, year, doi.

    record_id,human_label,title,abstract
    known-01,T,"Effect of X on Y","We tested whether X ... (full abstract)"
    known-02,F,"A review of Z","This narrative review summarizes ..."

Usage:
    # with labels.csv in the search's validate/ folder, just name the search:
    python -m screening.validate --search pilot             # screen + compare
    python -m screening.validate --search pilot --dry-run   # cost estimate only
    # or point at a labels file anywhere:
    python -m screening.validate --labels path/to/labels.csv
    # optional: a second labeler's file for inter-rater reliability (Cohen's kappa)
    python -m screening.validate --labels labeler_a.csv --labels2 labeler_b.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import Counter

from screening import screen
from screening.common import (
    Record, apply_search_layout, load_search_config, clean_text, clean_year,
    read_csv_dicts,
)


RESULT_COLS = [
    "record_id", "human_label", "eligible", "outcome", "reason_for_exclusion",
    "confidence", "agreement", "votes_include", "votes_exclude",
    "valid_samples", "total_samples", "needs_human_review", "rationale", "title",
]


def _write_dicts(rows, path, fieldnames):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


# --------------------------------------------------------------------------- #
# Load the handcrafted labels file into screenable records
# --------------------------------------------------------------------------- #
def load_labeled_records(path: str):
    """Read the handcrafted labels CSV -> (records, labels).

    `records` are Record objects ready to screen; `labels` maps record_id -> T/F.
    Requires record_id and human_label columns; reads title/abstract/authors/
    year/doi when present.
    """
    rows = read_csv_dicts(path)
    header = set(rows[0].keys()) if rows else set()
    for need in ("record_id", "human_label"):
        if need not in header:
            sys.exit(f"  {path} must have a '{need}' column.\n"
                     "  Handcraft it with columns: record_id, human_label (T/F), "
                     "title, abstract  (authors, year, doi optional).")

    records, labels, seen, missing_abstract = [], {}, set(), []
    for row in rows:
        rid = (row.get("record_id") or "").strip()
        lab = (row.get("human_label") or "").strip().upper()
        if not rid:
            continue
        if lab not in ("T", "F"):
            print(f"  ! skipping {rid!r}: human_label must be T or F (got {lab!r})")
            continue
        if rid in seen:
            print(f"  ! duplicate record_id {rid!r} — keeping the first")
            continue
        seen.add(rid)
        abstract = clean_text(row.get("abstract", "")) or None
        records.append(Record(
            record_id=rid,
            source_db="validate",
            title=clean_text(row.get("title", "")),
            authors=clean_text(row.get("authors", "")),
            year=clean_year(row.get("year")),
            doi=(row.get("doi") or "").strip() or None,
            abstract=abstract,
            abstract_source="manual" if abstract else "",
        ))
        labels[rid] = lab
        if not abstract:
            missing_abstract.append(rid)

    if not records:
        sys.exit(f"  no usable labeled records in {path} (need record_id + T/F human_label).")
    if missing_abstract:
        shown = ", ".join(missing_abstract[:5]) + (" ..." if len(missing_abstract) > 5 else "")
        print(f"  ! {len(missing_abstract)} labeled record(s) have no abstract — "
              f"screening on title alone: {shown}")
    return records, labels


def load_labels(path: str) -> dict:
    """Just record_id -> T/F, for a second labeler's inter-rater comparison."""
    out = {}
    for row in read_csv_dicts(path):
        rid = (row.get("record_id") or "").strip()
        lab = (row.get("human_label") or "").strip().upper()
        if rid and lab in ("T", "F"):
            out[rid] = lab
    return out


# --------------------------------------------------------------------------- #
# Inter-rater reliability (two human labelers) — optional, unchanged concept
# --------------------------------------------------------------------------- #
def cohen_kappa(pairs: list[tuple[str, str]]) -> float:
    n = len(pairs)
    if n == 0:
        return float("nan")
    po = sum(1 for a, b in pairs if a == b) / n
    ca, cb = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    labels = set(ca) | set(cb)
    pe = sum((ca[k] / n) * (cb[k] / n) for k in labels)
    return (po - pe) / (1 - pe) if (1 - pe) else float("nan")


def report_irr(labels: dict, labels2: dict) -> None:
    shared = sorted(set(labels) & set(labels2))
    print("\n=== INTER-RATER RELIABILITY (your gold standard) ===")
    if not shared:
        print("  no overlapping record_ids between the two label files — skipped")
        return
    pairs = [(labels[r], labels2[r]) for r in shared]
    agree = sum(1 for a, b in pairs if a == b)
    kappa = cohen_kappa(pairs)
    print(f"  overlapping labeled records: {len(shared)}")
    print(f"  raw percent agreement:       {agree / len(shared):.3f}")
    print(f"  Cohen's kappa:               {kappa:.3f}")
    if kappa < 0.6:
        print("  ** kappa < 0.6: your own labels disagree a lot — clarify the "
              "criteria before judging the model against them. **")


# --------------------------------------------------------------------------- #
# Screen the labeled records (same path as run.py screen) and score them
# --------------------------------------------------------------------------- #
def _outcome(human: str, model: str) -> str:
    if model not in ("T", "F"):
        return "no verdict"
    return {("T", "T"): "true include", ("F", "F"): "true exclude",
            ("F", "T"): "FALSE INCLUDE", ("T", "F"): "FALSE EXCLUDE"}[(human, model)]


def screen_and_score(records, labels, cfg, validate_dir, dry_run):
    """Screen the labeled records with self-consistency, write full results to
    validate_dir, and return the per-record result rows (None on a dry run)."""
    instructions, reasons = screen.load_criteria(cfg["paths"]["criteria_file"])
    system_prompt = screen.build_system_prompt(instructions, reasons)
    model = cfg["screen"]["model"]
    temps = screen.sample_temperatures(cfg)
    samples = len(temps)

    est = screen.estimate_cost(records, system_prompt, cfg, model, samples)
    print(f"  model: {model}  |  self-consistency: {samples} samples @ temps {temps}")
    print(f"  estimate: {est['records']} records x {samples} samples, "
          f"~{est['input_tokens']:,} in / ~{est['output_tokens']:,} out tokens")
    print(f"  total estimate: ~${est['est_usd']} (batch pricing, upper bound)")
    if dry_run:
        print("  (dry run — no API call made)")
        return None

    if "ANTHROPIC_API_KEY" not in os.environ:
        sys.exit("  ERROR: set ANTHROPIC_API_KEY before validating (it screens for real).")

    # keep validation's batch checkpoint + outputs in the validate/ folder so it
    # never collides with the real screen run's work/ checkpoint.
    os.makedirs(validate_dir, exist_ok=True)
    cfg["paths"]["work_dir"] = validate_dir
    raw_by_sample = screen.screen_records(records, system_prompt, cfg, model, temps)

    by_id = {r.record_id: r for r in records}
    rows, audit_log = [], []
    for rid, texts in raw_by_sample.items():
        verdicts = [screen.parse_verdict(t or "{}", reasons) for t in texts]
        v = screen.aggregate_samples(verdicts, cfg)
        flag = screen.review_flag(v, cfg)
        r, human = by_id[rid], labels.get(rid, "")
        model_elig = v.get("eligible", "")
        rows.append({
            "record_id": rid, "human_label": human, "eligible": model_elig,
            "outcome": _outcome(human, model_elig),
            "reason_for_exclusion": v.get("reason", ""),
            "confidence": v.get("confidence", ""),
            "agreement": v.get("agreement", ""),
            "votes_include": v.get("votes_include", ""),
            "votes_exclude": v.get("votes_exclude", ""),
            "valid_samples": v.get("valid_samples", ""),
            "total_samples": v.get("total_samples", ""),
            "needs_human_review": flag,
            "rationale": v.get("rationale", ""),
            "title": r.title,
        })
        audit_log.append({
            "record_id": rid, "model": model, "human_label": human,
            "samples": [{"temperature": temps[i], "raw": texts[i],
                         "eligible": verdicts[i]["eligible"],
                         "reason": verdicts[i]["reason"],
                         "rationale": verdicts[i]["rationale"],
                         "parse_error": verdicts[i]["parse_error"]}
                        for i in range(len(texts))],
            "final": {"eligible": model_elig, "reason": v.get("reason", ""),
                      "confidence": v.get("confidence", ""),
                      "agreement": v.get("agreement", ""),
                      "consistent": v.get("consistent", False)},
        })

    results_path = os.path.join(validate_dir, "validate_results.csv")
    _write_dicts(rows, results_path, RESULT_COLS)
    audit_path = os.path.join(validate_dir, "validate_raw_samples.jsonl")
    with open(audit_path, "w", encoding="utf-8") as fh:
        for entry in audit_log:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"\n  -> full validation results: {results_path}")
    print(f"  -> per-sample audit trail:  {audit_path}")
    return rows


def evaluate(rows) -> None:
    tp = fp = tn = fn = no_verdict = 0
    false_excludes, false_includes = [], []
    for row in rows:
        human = row["human_label"]
        model = (row["eligible"] or "").strip().upper()
        if model not in ("T", "F"):
            no_verdict += 1
        elif human == "T" and model == "T":
            tp += 1
        elif human == "F" and model == "F":
            tn += 1
        elif human == "F" and model == "T":
            fp += 1
            false_includes.append(row)
        elif human == "T" and model == "F":
            fn += 1
            false_excludes.append(row)

    sens = tp / (tp + fn) if (tp + fn) else float("nan")
    spec = tn / (tn + fp) if (tn + fp) else float("nan")

    print("\n=== VALIDATION (preliminary criteria check) ===")
    print(f"  labeled records screened: {tp + fp + tn + fn + no_verdict}")
    print(f"  confusion: TP={tp}  FP={fp}  TN={tn}  FN={fn}"
          + (f"  (+{no_verdict} no verdict)" if no_verdict else ""))
    print(f"  recall / sensitivity (caught your known includes): {sens:.3f}  ({tp}/{tp + fn})")
    print(f"  specificity (dropped your known excludes):         {spec:.3f}  ({tn}/{tn + fp})")

    if false_excludes:
        print(f"\n  ** {len(false_excludes)} FALSE EXCLUDES — you marked include, model "
              "excluded (the costly error): **")
        for row in false_excludes:
            print(f"     - {row['record_id']}: {row.get('title', '')[:80]}  "
                  f"[reason={row.get('reason_for_exclusion', '')}, "
                  f"agreement={row.get('agreement', '')}]")
    if false_includes:
        print(f"\n  {len(false_includes)} false includes — you marked exclude, model included:")
        for row in false_includes:
            print(f"     - {row['record_id']}: {row.get('title', '')[:80]}  "
                  f"[agreement={row.get('agreement', '')}]")
    if no_verdict:
        print(f"\n  {no_verdict} record(s) got no parseable verdict — see "
              "needs_human_review in validate_results.csv.")

    print("\n  This is a preliminary check on a set you hand-picked, not an unbiased "
          "estimate. If you change the criteria to fix a miss here, re-check on a "
          "FRESH hand-labeled set before you trust the wording.")


def main():
    ap = argparse.ArgumentParser(
        description="Optional preliminary check: screen a hand-labeled set with the "
                    "same self-consistency settings as the full run and compare.")
    ap.add_argument("--labels", default=None,
                    help="handcrafted CSV: record_id, human_label (T/F), title, abstract "
                         "(default: labels.csv in the search's validate/ folder)")
    ap.add_argument("--labels2",
                    help="optional second labeler (record_id, human_label) for inter-rater reliability")
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--search", default=None,
                    help="which search's config/criteria to validate against "
                         "(overrides paths.active_search)")
    ap.add_argument("--dry-run", action="store_true",
                    help="estimate screening cost only — no API call")
    args = ap.parse_args()

    cfg, name = load_search_config(args.config, args.search)
    apply_search_layout(cfg, name)
    validate_dir = cfg["paths"].get("validate_dir") or \
        os.path.join(os.path.dirname(cfg["paths"]["work_dir"]) or ".", "validate")
    if name:
        print(f"[search] {name}  ({cfg['paths']['search_root']}/)")

    labels_path = args.labels or os.path.join(validate_dir, "labels.csv")
    if not os.path.isfile(labels_path):
        sys.exit(f"  no labels file at {labels_path}.\n"
                 "  Handcraft one (record_id, human_label, title, abstract) there, "
                 "or pass --labels PATH.")

    records, labels = load_labeled_records(labels_path)
    if args.labels2:
        report_irr(labels, load_labels(args.labels2))

    print(f"\n[validate] screening {len(records)} hand-labeled records "
          "(same self-consistency as the full run)")
    rows = screen_and_score(records, labels, cfg, validate_dir, args.dry_run)
    if rows is not None:
        evaluate(rows)


if __name__ == "__main__":
    main()
