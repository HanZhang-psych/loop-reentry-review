# Search Strings — Level-3 Driving Takeover × Cognition

_Generated 2026-07-01. Companion to `criteria-old-level3.md`. Built on the same
three-block template as `search-strings-loop-reentry-cognitive.md`, but scoped to
**Level-3 (conditionally automated) driving** specifically. §7 adds a SAGE Journals
pass over the HFES Annual Meeting Proceedings, which Scopus/WoS index only patchily._

Three concept blocks combined with **AND**:

- **Block 1 — Level-3 / conditionally automated driving** (the automation context)
- **Block 2 — takeover event + driver performance** (the re-entry event)
- **Block 3 — standalone cognitive ability** (unchanged from the master template)

Enforceable "basics" are applied as filters per engine: **years 2010–2026**,
**English**, **peer-reviewed journal / conference paper**. Two things are **not**
filterable and are left to screening: **human participants** (no metadata field
in these databases) and the conceptual substance of the criteria (the keyword
blocks only approximate them).

---

## Master blocks (Scopus / WoS / EBSCO form; in-quote & embedded wildcards OK)

**Block 1**
```
"Level 3" OR "SAE Level 3" OR "conditional automation" OR "conditionally automated driving" OR "Level 3 automated driving" OR "automated driving" OR "autonomous vehicle"
```

**Block 2**
```
takeover OR "take-over" OR "takeover request" OR TOR OR "driver intervention" OR "takeover performance" OR "driver response" OR "transfer of control"
```

**Block 3**
```
"attentional control" OR "working memory" OR "sustained attention" OR "task switching" OR "executive function" OR "processing speed" OR "individual differences" OR "mental capacity" OR "cognitive control" OR attention*
```

---

## 1. Scopus (Advanced search)

```
TITLE-ABS-KEY(
 ( "Level 3" OR "SAE Level 3" OR "conditional automation" OR "conditionally automated driving" OR "Level 3 automated driving" OR "automated driving" OR "autonomous vehicle" )
 AND
 ( takeover OR "take-over" OR "takeover request" OR TOR OR "driver intervention" OR "takeover performance" OR "driver response" OR "transfer of control" )
 AND
 ( "attentional control" OR "working memory" OR "sustained attention" OR "task switching" OR "executive function" OR "processing speed" OR "individual differences" OR "mental capacity" OR "cognitive control" OR attention* )
)
AND PUBYEAR > 2009 AND PUBYEAR < 2027
AND LANGUAGE ( english )
AND ( DOCTYPE ( ar ) OR DOCTYPE ( cp ) )
```
Reapply filters Language == English, Source Type = Journal and Conference proceeding, and publication year 2010-2026 for returned results.

---

## 2. Web of Science (Core Collection, Advanced search)

```
TS=(
 ( "Level 3" OR "SAE Level 3" OR "conditional automation" OR "conditionally automated driving" OR "Level 3 automated driving" OR "automated driving" OR "autonomous vehicle" )
 AND
 ( takeover OR "take-over" OR "takeover request" OR TOR OR "driver intervention" OR "takeover performance" OR "driver response" OR "transfer of control" )
 AND
 ( "attentional control" OR "working memory" OR "sustained attention" OR "task switching" OR "executive function" OR "processing speed" OR "individual differences" OR "mental capacity" OR "cognitive control" OR attention* )
)
AND PY=(2010-2026)
AND LA=(English)
AND DT=(Article OR Proceedings Paper)
```
---

## 3. PsycINFO via EBSCOhost (Advanced search, default keyword field)

```
( "Level 3" OR "SAE Level 3" OR "conditional automation" OR "conditionally automated driving" OR "Level 3 automated driving" OR "automated driving" OR "autonomous vehicle" )
AND
( takeover OR "take-over" OR "takeover request" OR TOR OR "driver intervention" OR "takeover performance" OR "driver response" OR "transfer of control" )
AND
( "attentional control" OR "working memory" OR "sustained attention" OR "task switching" OR "executive function" OR "processing speed" OR "individual differences" OR "mental capacity" OR "cognitive control" OR attention* )
```
Then apply limiters: **Peer Reviewed** ✔ · **Publication Date** 2010–2026 ·
**Language** English.

---

## 4. IEEE Xplore (Advanced search — 3 rows, field = "All Metadata", combined AND)

Well within IEEE limits (≤40 terms, ≤15/clause, ≤5 wildcards): 7 / 8 / 10 terms,
**1 wildcard** (`attention*`), so the full term set is kept verbatim — no trimming needed.

**Row 1 (All Metadata)**
```
"Level 3" OR "SAE Level 3" OR "conditional automation" OR "conditionally automated driving" OR "Level 3 automated driving" OR "automated driving" OR "autonomous vehicle"
```
**Row 2 (All Metadata)**
```
takeover OR "take-over" OR "takeover request" OR TOR OR "driver intervention" OR "takeover performance" OR "driver response" OR "transfer of control"
```
**Row 3 (All Metadata)**
```
"attentional control" OR "working memory" OR "sustained attention" OR "task switching" OR "executive function" OR "processing speed" OR "individual differences" OR "mental capacity" OR "cognitive control" OR attention*
```
Then apply facets: **Year** 2010–2026. (IEEE content is English; no language filter.) Apply filter: Conferences and Journals

---

## 5. ACM Digital Library (search box, "Search within: Full text")

```
( "Level 3" OR "SAE Level 3" OR "conditional automation" OR "conditionally automated driving" OR "Level 3 automated driving" OR "automated driving" OR "autonomous vehicle" )
AND
( takeover OR "take-over" OR "takeover request" OR TOR OR "driver intervention" OR "takeover performance" OR "driver response" OR "transfer of control" )
AND
( "attentional control" OR "working memory" OR "sustained attention" OR "task switching" OR "executive function" OR "processing speed" OR "individual differences" OR "mental capacity" OR "cognitive control" OR attention* )
```
Then filter: **Publication Date** Jan 2010–July 2026 · restrict to **Research Articles** 

---

## 6. PubMed (Advanced search / search box)


**Full query** — paste this whole string into the PubMed search box (filters
included; or delete the last three lines and set them in the sidebar instead):
```
(
"Level 3"[tiab] OR "SAE Level 3"[tiab] OR "conditional automation"[tiab] OR "conditionally automated driving"[tiab] OR "Level 3 automated driving"[tiab] OR "automated driving"[tiab] OR "autonomous vehicle"[tiab]
)
AND
(
takeover[tiab] OR "take-over"[tiab] OR "takeover request"[tiab] OR TOR[tiab] OR "driver intervention"[tiab] OR "takeover performance"[tiab] OR "driver response"[tiab] OR "transfer of control"[tiab]
)
AND
(
"attentional control"[tiab] OR "working memory"[tiab] OR "sustained attention"[tiab] OR "task switching"[tiab] OR "executive function"[tiab] OR "executive functions"[tiab] OR "processing speed"[tiab] OR "individual differences"[tiab] OR "mental capacity"[tiab] OR "cognitive control"[tiab] OR attention*[tiab]
)
AND ("2010/01/01"[dp] : "2026/12/31"[dp])
AND English[lang]
AND "journal article"[pt]
```
`[dp]` = date of publication; `[pt]` = publication type. Drop `"journal
article"[pt]` (or add `OR review[pt]`) to keep reviews; PubMed indexes almost no
standalone conference papers, so there is no `cp`-equivalent to add. In PubMed
especially, `TOR[tiab]` collides with the biology gene/pathway "TOR/mTOR" — the
`AND` with Blocks 1 and 3 removes almost all of it, but watch for stragglers.

---

## 7. SAGE Journals — HFES Annual Meeting Proceedings (`journals.sagepub.com/home/pro`)

Closes a coverage gap: the **Proceedings of the Human Factors and Ergonomics Society
Annual Meeting** 

**Advanced Search — 3 rows, field = _Abstract_, combined with AND**

Row 1 (Abstract)
```
"Level 3" OR "SAE Level 3" OR "conditional automation" OR "conditionally automated driving" OR "Level 3 automated driving" OR "automated driving" OR "autonomous vehicle"
```
Row 2 (Abstract)
```
takeover OR "take-over" OR "takeover request" OR TOR OR "driver intervention" OR "takeover performance" OR "driver response" OR "transfer of control"
```
Row 3 (Abstract)
```
"attentional control" OR "working memory" OR "sustained attention" OR "task switching" OR "executive function" OR "processing speed" OR "individual differences" OR "mental capacity" OR "cognitive control" OR attention*
```


---
