# Getting the data before you run anything

The assessment data is **not in this repository**, on purpose. It holds individual student
records, this repo is public, and committing it would expose real children's data and
disqualify the entry. The merged file is also 181 MB, which is over GitHub's 100 MB per-file
limit.

Two ways to get set up. Either works, and both produce an identical analysis frame of
13,79,087 records and identical numbers throughout.

## Option A: download the merged file (simplest)

1. Download the zip:
   **https://drive.google.com/file/d/1YFrqXsiXpJg2GnsgN5drQcNXezS4k204/view?usp=sharing**
2. Unzip it.
3. Put the CSV here, with exactly this name:

```
external_data/datathon_master_appended_new.csv
```

That single file is the three years of the Akshara GP Maths Contest merged into one table,
with the 11 competency scores already computed from the official per-file question map.

## Option B: use the original organiser files

1. Put the organiser workbooks in `data/`.
2. Run `python prep/05_standardise_primary.py`, which writes nine standardised CSVs to:

```
data/primary/std_grade4_2022-23.csv
data/primary/std_grade4_2023-24.csv
data/primary/std_grade4_2024-25.csv
data/primary/std_grade5_2022-23.csv
data/primary/std_grade5_2023-24.csv
data/primary/std_grade5_2024-25.csv
data/primary/std_grade6_2022-23.csv
data/primary/std_grade6_2023-24.csv
data/primary/std_grade6_2024-25.csv
```

The notebook detects whichever route you used and rebuilds the same frame from it.

## You also need the UDISE+ files

Coverage, the Kalyana Karnataka comparison and every enrolment denominator read from:

```
data/udise_csv/udise_ka_enrolment_by_grade_2022-23.csv
data/udise_csv/udise_ka_enrolment_by_grade_2023-24.csv
data/udise_csv/udise_ka_enrolment_by_grade_2024-25.csv
data/udise_csv/udise_ka_school_2022-23.csv
data/udise_csv/udise_ka_school_2023-24.csv
data/udise_csv/udise_ka_school_2024-25.csv
```

These are public UDISE+ extracts. Sources and the verification log are in
`external_data/SOURCES.md` and `docs/VERIFICATION_LOG.md`.

## Then run it

```
pip install -r requirements.txt
jupyter notebook jupyter_notebook.ipynb    # then Run All
```

Or headless, without Jupyter:

```
python src/run_all.py
python src/fix_coverage.py
python src/day1_verdicts.py
python src/extra_hypotheses.py
```

Fixed seed 20260801. Offline, no licences, roughly three minutes for the pipeline.

Section 14 of the notebook re-checks all 48 published numbers against the report and prints
PASS or FAIL for each. If your run disagrees with `report.pdf` anywhere, that section will say
so instead of hiding it.
