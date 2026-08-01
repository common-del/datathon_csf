# Datathon 2026 — Karnataka mathematics learning analytics

Team **datathon_csf** · Akshara Foundation + ACSEL
Tracks: Data Insights & Visualization, Predictive Analytics, Policy & Intervention Design

Primary evidence: `report.pdf` and `docs/policy_note.pdf`. Supporting: `slides.pptx`.
Every numeric claim is listed in `claims.json` with the file and row that proves it.

## Start here

**1. Get the data.** It is not in this repo, by competition rule and because the merged file is
181 MB, over GitHub's per-file limit. Read **`DATA_ACCESS.md`**. Quickest route: download the zip
from https://drive.google.com/file/d/1YFrqXsiXpJg2GnsgN5drQcNXezS4k204/view?usp=sharing and unzip
it to `external_data/datathon_master_appended_new.csv`.

**2. Run the one notebook.**

```
pip install -r requirements.txt
jupyter notebook jupyter_notebook.ipynb     # then Run All
```

`jupyter_notebook.ipynb` is the single entry point. Run All rebuilds every figure, table and
number behind `report.pdf`, `slides.pptx` and `docs/policy_note.pdf`. Its final section re-checks
all 48 published numbers against the report and prints PASS or FAIL for each, then prints a map
tracing every figure to the exact place it appears in each document.

Headless, without Jupyter:

```
python src/run_all.py            # the organisers' single entry point
python src/fix_coverage.py
python src/day1_verdicts.py
python src/extra_hypotheses.py
```

Offline, fixed seed 20260801, roughly three minutes.

## What's in the repo

```
jupyter_notebook.ipynb     the single entry point: Run All reproduces everything
DATA_ACCESS.md             how to get the data before running
report.pdf                 main findings
slides.pptx                12-slide deck
docs/policy_note.pdf       one-page note for the Commissioner
claims.json                46 numeric claims, each with how to verify it
manifest.yml               inventory, tracks, external datasets
requirements.txt           pinned dependencies

src/run_all.py             pipeline entry point: QA, analyses, model, figures, dashboard
src/fix_coverage.py        corrected coverage denominator, asserted against UDISE
src/day1_verdicts.py       hypotheses H1-H13
src/extra_hypotheses.py    hypotheses EH1-EH24
src/variance_gp_level.py   variance decomposition on GP means
src/figure_*.py            the five standalone figure builders
src/build_hypothesis_xlsx.py   the 36-hypothesis register
src/build_deliverables.py  rebuilds slides.pptx, manifest.yml, claims.json
src/{loader,schema,qa,metrics,analyses,external,model,figures,dashboard,
     coverage,choropleth,config}.py    pipeline internals

prep/                      how external_data was built, kept for provenance
external_data/             11 verified public datasets, plus the competency map
outputs/figures/           21 charts
outputs/tables/            61 tables
outputs/predictions/       Track 2: predicted mean per GP on the 0-20 scale
outputs/HYPOTHESIS_REGISTER.xlsx   all 36 hypotheses with method and assumptions
data/                      git-ignored. Never committed. See DATA_ACCESS.md
```

## External data

| Dataset | Vintage | Finest level used |
|---|---|---|
| UDISE+ school and enrolment records, Karnataka | 2022-23 to 2024-25 | District, block |
| Census 2011 Primary Census Abstract | 2011 | CD block |
| NFHS-5 district fact sheets | 2019-21 | District |
| NFHS-6 fact sheet | 2023-24 | State |
| ASER rural Karnataka | 2024 | District |
| PGI-D | 2025-26 | Educational district |
| PARAKH Rashtriya Sarvekshan | 2024 | District |
| Karnataka district crosswalk and geography hierarchy | 2024-25 | GP |
| Dated timeline of 26 school-system events | 2022-25 | Taluk to state |

Full citations in `external_data/SOURCES.md`, verification log in `docs/VERIFICATION_LOG.md`.

External covariates are joined only at levels that pass an automatic reliability gate.
District passes at 100%, block at 68%. Gram Panchayat is refused at 37%, and cluster is refused
outright because UDISE+ carries no cluster field.

## Rules compliance

Python only. Single entry point. Relative paths throughout. Fixed seed 20260801. No network
access at runtime. The dashboard is code-generated Plotly in one self-contained HTML file, no
Power BI or Tableau. The primary dataset is excluded by `.gitignore` and never committed. All
external data is public and cited.
