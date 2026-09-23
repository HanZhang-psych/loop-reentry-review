# Consolidated cognitive-search PRISMA 2020 flow diagram

Files in this folder:

- `PRISMA_flow_cognitive_R.pdf` / `.png` / `.svg` — the flow diagram (PRISMA2020 package output).
- `PRISMA_cognitive_data.csv` — the filled PRISMA2020 template (the data behind the figure).
- `make_prisma_flowchart.R` — regenerates the figure from the CSV using the CRAN `PRISMA2020` package.
- `consolidated_prisma_summary.txt` — the full consolidated flow in text, with the three full-text-excluded model-eligible papers listed.

## Regenerate

```r
install.packages("PRISMA2020")   # once
# from this folder:
# Rscript make_prisma_flowchart.R
```

## How the numbers map (fully-merged flow across the four cognitive runs)

Runs merged as one search, all duplicates removed once:
ai-cognitive-0706, ai_cognitive_hfes, level3_cognitive_0706, level3_cognitive_hfes.

- Databases identified: 10,566 — Web of Science 843; Scopus 1,064; IEEE Xplore 756; PsycINFO 240; PubMed 207; ACM Digital Library 7,087; SAGE/HFES proceedings 369 (aggregated across the four runs).
- Removed before screening: 1,500, shown as a single "Duplicate records" total (1,233 within-run + 62 cross-run duplicates + 205 previously-screened overlap).
- Records screened: 9,066. Excluded by automated screening: 9,013 (a 198-record audit subset was human-checked). Reasons listed in the box: no out-of-the-loop automation 4,957; no human participants 2,859; no standalone cognitive task 776; no objective performance measure 350; experimental manipulation study 45; no loop re-entry 26.
- Reports sought / assessed at full text: 53 = 11 model-eligible + 42 held for human review (insufficient information / no abstract / inconsistent samples — not counted as excluded at abstract screening).
- Excluded at full text: 42 ("Did not meet inclusion criteria on full-text review").
- Other methods (Google Scholar Labs): 2 identified, 2 assessed, 0 excluded.
- Studies included: 13 (11 from the searches + 2 from Google Scholar Labs). Chen & Barnes (2012) is included for its Experiment 2 (separate sample); its Experiment 1 is the same dataset as the included Chen, Barnes & Qu (2010) paper, which is kept as the Experiment 1 record.

Note: the full-text exclusion reason is a single generic label; substantive per-paper
reasons were not recorded in the source sheet. No registers were searched, so that line is omitted.
