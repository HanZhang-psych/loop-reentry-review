# Search Strings — "Re-entering the Loop" Scoping Review

_Generated 2026-06-30. Companion to `criteria-loop-reentry.md`._

Broadened human–AI search (separate from the completed Level-3 driving search).
§7 adds a SAGE Journals pass over the HFES Annual Meeting Proceedings, which
Scopus/WoS index only patchily.
Three concept blocks combined with **AND**:

- **Block 1 — out-of-the-loop automation** (criterion 1)
- **Block 2 — re-entering-the-loop event + performance** (criteria 2–3)
- **Block 3 — standalone cognitive ability** (criterion 4)

Enforceable "basics" are applied as filters per engine: **years 2010–2026**,
**English**, **peer-reviewed journal / conference paper**. Two things are **not**
filterable and are left to screening: **human participants** (no metadata field
in these databases) and the conceptual substance of criteria 1–4 (the keyword
blocks only approximate them).

---

## Master blocks (Scopus / WoS / EBSCO form; in-quote & embedded wildcards OK)

**Block 1**
```
"human-AI interaction" OR "human-AI teaming" OR "human-AI collaboration" OR "human-agent interaction" OR "human-autonomy teaming" OR "human-automation interaction" OR "human-machine interaction" OR "AI assistant*" OR "intelligent agent*" OR automation OR "automated system*" OR "autonomous system*" OR "task offloading" OR "cognitive offloading" OR "supervisory control" OR "human supervision" OR "large language model*" OR LLM OR "generative AI"
```

**Block 2**
```
"out of the loop" OR "out-of-the-loop" OR takeover OR "take-over" OR "task resumption" OR "resume control" OR "re-engag*" OR reengag* OR "re-enter*" OR "transfer of control" OR handover OR handoff OR interven* OR overrid* OR malfunction* OR "failure detect*" OR "error detect*" OR "hazard detect*" OR evaluat* OR vetting OR oversight OR reliance OR "situation awareness"
```

**Block 3**
```
"attentional control" OR "working memory" OR "sustained attention" OR "task switching" OR "executive function" OR "processing speed" OR "individual differences" OR "mental capacity" OR "cognitive control" OR attentional*
```

---

## 1. Scopus (Advanced search)

```
TITLE-ABS-KEY(
 ( "human-AI interaction" OR "human-AI teaming" OR "human-AI collaboration" OR "human-agent interaction" OR "human-autonomy teaming" OR "human-automation interaction" OR "human-machine interaction" OR "AI assistant*" OR "intelligent agent*" OR automation OR "automated system*" OR "autonomous system*" OR "task offloading" OR "cognitive offloading" OR "supervisory control" OR "human supervision" OR "large language model*" OR LLM OR "generative AI" )
 AND
 ( "out of the loop" OR "out-of-the-loop" OR takeover OR "take-over" OR "task resumption" OR "resume control" OR "re-engag*" OR reengag* OR "re-enter*" OR "transfer of control" OR handover OR handoff OR interven* OR overrid* OR malfunction* OR "failure detect*" OR "error detect*" OR "hazard detect*" OR evaluat* OR vetting OR oversight OR reliance OR "situation awareness" )
 AND
 ( "attentional control" OR "working memory" OR "sustained attention" OR "task switching" OR "executive function" OR "processing speed" OR "individual differences" OR "mental capacity" OR "cognitive control" OR attentional* )
)
AND PUBYEAR > 2009 AND PUBYEAR < 2027
AND LANGUAGE ( english )
AND ( DOCTYPE ( ar ) OR DOCTYPE ( cp ) )
```
Reapply filters Language = English, Source Type = Journal and Conference proceeding,
and publication year 2010–2026 for the returned results.

---

## 2. Web of Science (Core Collection, Advanced search)

```
TS=(
 ( "human-AI interaction" OR "human-AI teaming" OR "human-AI collaboration" OR "human-agent interaction" OR "human-autonomy teaming" OR "human-automation interaction" OR "human-machine interaction" OR "AI assistant*" OR "intelligent agent*" OR automation OR "automated system*" OR "autonomous system*" OR "task offloading" OR "cognitive offloading" OR "supervisory control" OR "human supervision" OR "large language model*" OR LLM OR "generative AI" )
 AND
 ( "out of the loop" OR "out-of-the-loop" OR takeover OR "take-over" OR "task resumption" OR "resume control" OR "re-engag*" OR reengag* OR "re-enter*" OR "transfer of control" OR handover OR handoff OR interven* OR overrid* OR malfunction* OR "failure detect*" OR "error detect*" OR "hazard detect*" OR evaluat* OR vetting OR oversight OR reliance OR "situation awareness" )
 AND
 ( "attentional control" OR "working memory" OR "sustained attention" OR "task switching" OR "executive function" OR "processing speed" OR "individual differences" OR "mental capacity" OR "cognitive control" OR attentional* )
)
AND PY=(2010-2026)
AND LA=(English)
AND DT=(Article OR Proceedings Paper)
```
Reapply filters Language = English, Document Type = Article and Proceedings Paper,
and publication year 2010–2026 for the returned results.

---

## 3. PsycINFO via EBSCOhost (Advanced search, default keyword field)

```
( "human-AI interaction" OR "human-AI teaming" OR "human-AI collaboration" OR "human-agent interaction" OR "human-autonomy teaming" OR "human-automation interaction" OR "human-machine interaction" OR "AI assistant*" OR "intelligent agent*" OR automation OR "automated system*" OR "autonomous system*" OR "task offloading" OR "cognitive offloading" OR "supervisory control" OR "human supervision" OR "large language model*" OR LLM OR "generative AI" )
AND
( "out of the loop" OR "out-of-the-loop" OR takeover OR "take-over" OR "task resumption" OR "resume control" OR "re-engag*" OR reengag* OR "re-enter*" OR "transfer of control" OR handover OR handoff OR interven* OR overrid* OR malfunction* OR "failure detect*" OR "error detect*" OR "hazard detect*" OR evaluat* OR vetting OR oversight OR reliance OR "situation awareness" )
AND
( "attentional control" OR "working memory" OR "sustained attention" OR "task switching" OR "executive function" OR "processing speed" OR "individual differences" OR "mental capacity" OR "cognitive control" OR attentional* )
```
Then apply limiters: **Peer Reviewed** ✔ · **Publication Date** 2010–2026 ·
**Language** English.

---

## 4. IEEE Xplore (Advanced search — 3 rows, field = "All Metadata", combined AND)

Capped to IEEE limits (≤40 terms, ≤15/clause, ≤5 wildcards); in-quote and
embedded-phrase wildcards removed. Totals: 15 / 14 / 10 terms, 5 wildcards
(`attentional*` in Row 3 is the 5th — exactly at IEEE's ≤5 wildcard cap).

**Row 1 (All Metadata)**
```
"human-AI interaction" OR "human-autonomy teaming" OR "human-automation interaction" OR "human-machine interaction" OR "AI assistant" OR "intelligent agent" OR automation OR "automated system" OR "autonomous system" OR "supervisory control" OR "human supervision" OR "large language model" OR LLM OR "generative AI" OR "cognitive offloading"
```
**Row 2 (All Metadata)**
```
"out of the loop" OR "out-of-the-loop" OR takeover OR "take-over" OR handover OR reengag* OR interven* OR overrid* OR "failure detection" OR evaluat* OR vetting OR oversight OR reliance OR "situation awareness"
```
**Row 3 (All Metadata)**
```
"attentional control" OR "working memory" OR "sustained attention" OR "task switching" OR "executive function" OR "processing speed" OR "individual differences" OR "mental capacity" OR "cognitive control" OR attentional*
```
Then apply facets: **Year** 2010–2026. (IEEE content is English; no language filter.). Apply filter: Conferences and Journals

---

## 5. ACM Digital Library (search box, "Search within: Full text")

Wildcards removed from all quoted phrases (ACM does not expand `*` inside quotes);
plurals restored explicitly; Boolean operators must stay capitalized.

```
( "human-AI interaction" OR "human-AI teaming" OR "human-AI collaboration" OR "human-agent interaction" OR "human-autonomy teaming" OR "human-automation interaction" OR "human-machine interaction" OR "AI assistant" OR "AI assistants" OR "intelligent agent" OR "intelligent agents" OR automation OR "automated system" OR "automated systems" OR "autonomous system" OR "autonomous systems" OR "task offloading" OR "cognitive offloading" OR "supervisory control" OR "human supervision" OR "large language model" OR "large language models" OR LLM OR "generative AI" )
AND
( "out of the loop" OR "out-of-the-loop" OR takeover OR "take-over" OR "task resumption" OR "resume control" OR reengag* OR "re-engagement" OR "re-engaging" OR "re-engage" OR reenter* OR "re-enter" OR "re-entry" OR "transfer of control" OR handover OR handoff OR interven* OR overrid* OR malfunction* OR "failure detection" OR "error detection" OR "hazard detection" OR evaluat* OR vetting OR oversight OR reliance OR "situation awareness" )
AND
( "attentional control" OR "working memory" OR "sustained attention" OR "task switching" OR "executive function" OR "processing speed" OR "individual differences" OR "mental capacity" OR "cognitive control" OR attentional* )
```
Then filter: **Publication Date** Jan 2010–July 2026 · restrict to **Research Articles**.

To circumvent max download of 1000 records: Separate searches for 2010-2016, 2016-2020, 

---

## 6. PubMed (Advanced search / search box)

PubMed applies a field tag only to the **single term immediately before it**, so
every term carries its own `[tiab]` (title/abstract — the closest analog to
Scopus's `TITLE-ABS-KEY`). PubMed truncation (`*`) is **trailing-only and illegal
inside a quoted phrase**, so phrase-with-wildcard terms are expanded to explicit
variants (as in the ACM form); single-word truncations are kept. Hyphens are
ignored (`"human-AI"` = `"human AI"`), so the hyphen/space pairs collapse to one
match — harmless duplicates left in for readability.

**Full query** — paste this whole string into the PubMed search box (filters
included; or delete the last three lines and set them in the sidebar instead):
```
(
"human-AI interaction"[tiab] OR "human-AI teaming"[tiab] OR "human-AI collaboration"[tiab] OR "human-agent interaction"[tiab] OR "human-autonomy teaming"[tiab] OR "human-automation interaction"[tiab] OR "human-machine interaction"[tiab] OR "AI assistant"[tiab] OR "AI assistants"[tiab] OR "intelligent agent"[tiab] OR "intelligent agents"[tiab] OR automation[tiab] OR "automated system"[tiab] OR "automated systems"[tiab] OR "autonomous system"[tiab] OR "autonomous systems"[tiab] OR "task offloading"[tiab] OR "cognitive offloading"[tiab] OR "supervisory control"[tiab] OR "human supervision"[tiab] OR "large language model"[tiab] OR "large language models"[tiab] OR LLM[tiab] OR "generative AI"[tiab]
)
AND
(
"out of the loop"[tiab] OR "out-of-the-loop"[tiab] OR takeover[tiab] OR "take-over"[tiab] OR "task resumption"[tiab] OR "resume control"[tiab] OR reengag*[tiab] OR "re-engagement"[tiab] OR "re-engaging"[tiab] OR "re-engage"[tiab] OR reenter*[tiab] OR "re-enter"[tiab] OR "re-entry"[tiab] OR "transfer of control"[tiab] OR handover[tiab] OR handoff[tiab] OR interven*[tiab] OR overrid*[tiab] OR malfunction*[tiab] OR "failure detection"[tiab] OR "error detection"[tiab] OR "hazard detection"[tiab] OR evaluat*[tiab] OR vetting[tiab] OR oversight[tiab] OR reliance[tiab] OR "situation awareness"[tiab]
)
AND
(
"attentional control"[tiab] OR "working memory"[tiab] OR "sustained attention"[tiab] OR "task switching"[tiab] OR "executive function"[tiab] OR "executive functions"[tiab] OR "processing speed"[tiab] OR "individual differences"[tiab] OR "mental capacity"[tiab] OR "cognitive control"[tiab] OR attentional*[tiab]
)
AND ("2010/01/01"[dp] : "2026/12/31"[dp])
AND English[lang]
AND "journal article"[pt]
```
`[dp]` = date of publication; `[pt]` = publication type. Drop `"journal
article"[pt]` (or add `OR review[pt]`) to keep reviews; PubMed indexes almost no
standalone conference papers, so there is no `cp`-equivalent to add.

---

## 7. SAGE Journals — HFES Annual Meeting Proceedings (`journals.sagepub.com/home/pro`)

Closes a coverage gap: the **Proceedings of the Human Factors and Ergonomics Society
Annual Meeting** 

**Advanced Search — 3 rows, field = _Abstract_, combined with AND**

Row 1 (Abstract)
```
"human-AI interaction" OR "human-AI teaming" OR "human-AI collaboration" OR "human-agent interaction" OR "human-autonomy teaming" OR "human-automation interaction" OR "human-machine interaction" OR "AI assistant" OR "AI assistants" OR "intelligent agent" OR "intelligent agents" OR automation OR "automated system" OR "automated systems" OR "autonomous system" OR "autonomous systems" OR "task offloading" OR "cognitive offloading" OR "supervisory control" OR "human supervision" OR "large language model" OR "large language models" OR LLM OR "generative AI"
```
Row 2 (Abstract)
```
"out of the loop" OR "out-of-the-loop" OR takeover OR "take-over" OR "task resumption" OR "resume control" OR reengag* OR "re-engagement" OR "re-engaging" OR "re-engage" OR reenter* OR "re-enter" OR "re-entry" OR "transfer of control" OR handover OR handoff OR interven* OR overrid* OR malfunction* OR "failure detection" OR "error detection" OR "hazard detection" OR evaluat* OR vetting OR oversight OR reliance OR "situation awareness"
```
Row 3 (Abstract)
```
"attentional control" OR "working memory" OR "sustained attention" OR "task switching" OR "executive function" OR "processing speed" OR "individual differences" OR "mental capacity" OR "cognitive control" OR attentional*
```

---

