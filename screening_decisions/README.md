# LLM screening decision log

The per-record decisions made by the large language model (Claude Sonnet 4.6)
during title-and-abstract screening, for every record it screened across the
four cognitive searches. This is the transparency record referenced in the
manuscript's Methods.

**Source abstracts are not included here.** These files carry only bibliographic
metadata (DOI, title, authors, year, source database) and the model's own
outputs (its per-sample verdict, chosen reason, and short rationale). The
copyrighted abstracts that were sent to the model are not redistributed.

## Files

- `decision_log.jsonl` — one JSON object per record, with the full detail:
  each of the five samples (`temperature`, `eligible`, `reason`, `rationale`)
  and the aggregated `final` decision.
- `decision_log.csv` — the same records in flat form, one row each: the five
  per-temperature verdicts (`elig_t00`…`elig_t10`), vote counts, agreement, and
  the final decision. Convenient for quick inspection; use the JSONL for the
  per-sample rationales.

## Fields

- `eligible`: `T` (include) or `F` (exclude); blank if a sample did not parse.
- Each record was screened five times at temperatures 0.0, 0.3, 0.5, 0.7, 1.0.
  A record was auto-excluded only when all five samples returned `F`; any other
  pattern was routed to human review (`needs_human_review`).
- `reason`: the exclusion reason a sample cited, from the fixed list in the
  screening prompt (`prompts/criteria-loop-reentry-cognitive.md`). The final
  reason is the one most frequently cited across the exclude samples.
- Records with no abstract were not sent to the model; they appear with an empty
  `samples` list and are marked for human review.

## Scope and counts

Each row is one record as screened within one search, tagged by `search`. Records
retrieved by more than one of the four searches therefore appear once per search;
the PRISMA flow counts in the manuscript are after cross-search de-duplication,
so totals here (9,128 rows: 9,098 screened + 30 not screened for a missing
abstract) are larger than the 9,066 unique records reported in the flow diagram.
