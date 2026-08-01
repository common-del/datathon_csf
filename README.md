# Datathon 2026 — Karnataka mathematics learning analytics

## Team

Team **datathon_csf** · Datathon 2026 (Akshara Foundation + ACSEL) · Tracks: Data Insights & Visualization, Predictive Analytics, Policy & Intervention Design

Primary evidence: `report.pdf` and `docs/policy_note.pdf`. Supporting: `slides.pptx`. Every numeric claim: `claims.json`.


Single entry point, offline, fixed seed, under 3 minutes.

```
python src/run_all.py          # or double-click RUN_ME.bat on Windows
```

**New here? Read `START_HERE.md`. Nothing else.**

## What's in the box

```
START_HERE.md              the only page you need on Day 1
RUN_ME.bat                 double-click to run everything
CHECK_SETUP.bat            double-click to diagnose your install

data/primary/              put the Akshara CSV here. Never committed.
external_data/             8 external datasets, already cleaned and joined
data/SOURCES.md            every citation, plus the joining hazards

prep/00_check_environment.py    what's installed, what's missing
prep/01_fetch_census.py         pulls Census 2011 Karnataka (needs internet, run once)
prep/02_build_udise_covariates.py  rebuilds the UDISE covariates (already done)
prep/03_make_synthetic.py       fake data shaped like the real thing, for rehearsal

src/run_all.py             the entry point
src/config.py              the ONLY file you might edit
src/schema.py              works out which column is which
src/loader.py              load, clean, harmonise
src/qa.py                  integrity and anomaly checks
src/metrics.py             the 5 original metrics
src/analyses.py            items, competencies, gender, geography, cohorts
src/external.py            joins, with match-rate reporting
src/model.py               early-warning model, 3 nested feature sets
src/figures.py             static charts
src/dashboard.py           self-contained interactive HTML

docs/report_TEMPLATE.md         report skeleton
docs/policy_note_TEMPLATE.md    2-page policy note skeleton
docs/slides_TEMPLATE.pptx       12-slide deck, pre-formatted, figure names printed on each slide
docs/build_slides.js            regenerates the deck if you want to change the layout

playbook/INSTALL_WINDOWS.md     Thursday night, 40 minutes
playbook/DAY1_BATTLE_PLAN.md    hour by hour against the 7pm deadline
playbook/INSIGHT_PLAYBOOK.md    what every output means, and the sentence to write
playbook/JUDGE_QA_PREP.md       the 14 questions, and how to answer them

outputs/                   everything the pipeline produces
manifest.yml               auto-generated list of outputs
claims.json                auto-generated list of every numeric claim
```

## The external data, at a glance

| Dataset | Vintage | Finest level available |
|---|---|---|
| Census 2011 Primary Census Abstract, Karnataka | 2011 | CD Block (and village) |
| NFHS-5 district fact sheets | 2019–21 | District |
| ASER (rural) Karnataka | 2024 | District (pooled grade bands) |
| PGI-D | 2025-26 | Educational district |
| UDISE+ school records, Karnataka | 2022-23 to 2024-25 | **Gram Panchayat** |
| Karnataka geography hierarchy | 2024-25 | Gram Panchayat |
| Karnataka district crosswalk | — | 31 revenue / 35 educational districts |

Gram Panchayat coverage in UDISE is 97.8% for rural schools, which is why block and GP joins work at all. Full caveats in `data/SOURCES.md`.

## The five original metrics

1. **Learning Variance Signature** — where the variation in learning actually lives across the administrative hierarchy, with a df-adjusted variance component so small units don't fake a signal.
2. **Targeting Efficiency Ceiling** — the most of the learning gap any scheme at a given tier could reach, executed perfectly.
3. **Competency Bottleneck Score** — gate lift × (1 − mastery), finding the competency that is both load-bearing and missing.
4. **Floor Index** — the 10th percentile tracked against the mean, so you can see whether the weakest children moved.
5. **Structural Advantage Residual** — actual minus what socio-economic and school-system conditions predict, which turns "correlation is not causation" into a method rather than a caveat.

Plus the **Intervention Triage Score** as the decision tool: gap × children affected × tractability.

## Design notes

- Every analysis step is wrapped. One failure never stops the run; it gets reported at the end of `outputs/RUN_LOG.txt`.
- Column names are detected against a synonym dictionary, with a manual override in `src/config.py` if detection fails.
- If no real item-to-competency mapping is supplied, one is inferred by clustering item correlations, and the output says so.
- Charts use a green-white-red diverging scale, green for the socially preferable direction, white at the benchmark.
- `external_data/SAMPLE_competency_map_DO_NOT_USE_FOR_REAL_DATA.csv` is a shape example only. On Day 1, save the real mapping as `external_data/competency_map.csv`.

## Rules compliance

Python only. Single entry point. Relative paths. Fixed seed 20260801. No network at runtime. Dashboard is code-generated Plotly in one self-contained HTML file, no Power BI or Tableau. Primary dataset excluded by `.gitignore`. All external data public and cited in `data/SOURCES.md`.
