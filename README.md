# loop-reentry-review

Materials for the scoping review *Who can re-enter the loop? A scoping review on
cognitive abilities and loop re-entry in human–AI interaction.*

This repository documents how the review's literature search and screening were
run, and it reproduces the PRISMA 2020 flow diagram. 

## What the review did

We searched seven databases plus a supplementary Google Scholar Labs pass for
studies that relate a standalone measure of a cognitive ability to an objective
measure of how well a person re-enters the loop after offloading a task to an
automated or AI agent. Titles and abstracts were screened by a large language
model (Claude Sonnet 4.6) prompted with the eligibility criteria; each record was
screened five times at different sampling temperatures, and a record was excluded
only when all five screenings agreed. Records that passed were screened at full
text by two research assistants. The search identified 10,566 records (9,066
after de-duplication) and yielded 13 included studies.

## Repository layout

    prompts/            The screening criteria sent to the model as its
                        instructions (prompts/criteria-loop-reentry-cognitive.md).
    search_strings/     The database query strings, by search strand.
    search_results/     Per-strand PRISMA count summaries (record counts only).
    prisma/             Reproducible PRISMA 2020 flow diagram: the R script,
                        the data behind it, the rendered figure, and a
                        text summary of the consolidated flow.
    run.py, screening/  The screening pipeline (code only).
    config.template.yaml, requirements.txt

## Reproducing the PRISMA flow diagram

The figure is generated from `prisma/PRISMA_cognitive_data.csv` with the CRAN
`PRISMA2020` package:

    cd prisma
    Rscript make_prisma_flowchart.R

See `prisma/README_prisma.md` for how each number in the diagram maps to the
screening stages.

## Re-running the screening pipeline

The pipeline is included so the screening procedure is inspectable and
repeatable. To run screening on your own exported records:

    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=...        # required for a live screen
    python run.py prepare --search my_search
    python run.py screen  --search my_search

The screening logic lives in `prompts/criteria-loop-reentry-cognitive.md`; the
pipeline adds the structured-output format automatically.

## Citation

If you use these materials, please cite the paper. [Citation to be added.]

## License

Code is released under the MIT License (see `LICENSE`). The prompt, search
strings, and PRISMA data files may be reused with attribution.
