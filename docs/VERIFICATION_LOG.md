# Verification log, 30 July 2026

Every number in the kit rechecked against its original source before the event. Method and coverage per file. Re-run this discipline on anything added later.

| File / claim | Method | Coverage | Result |
|---|---|---|---|
| nfhs5_karnataka_districts.csv | Cell diff vs pratapvardhan GitHub mirror of official fact sheets, in-browser full-file diff | 330/330 cells | CLEAN, zero mismatches |
| aser2024_karnataka_districts.csv | Cell diff vs ASER 2024 Karnataka District Estimates PDF | 180/180 cells | CLEAN |
| aser_karnataka_trend.csv | Cell diff vs ASER 2024 Karnataka state pages + India trend tables | 40/40 cells | CLEAN |
| pgid_2025_26_karnataka.csv | Cell diff vs PGI-D 2025-26 report PDF (official endpoint) + row-sum arithmetic | 245/245 cells, 35/35 sums | CLEAN |
| nfhs6_karnataka_state.csv, nfhs6_india_state.csv | Independent re-extraction from the local PDF, contiguous value-sequence match | 202/202 rows | CLEAN |
| udise_karnataka_*_covariates.csv (PTR etc.) | Independent recompute from raw parquet, fresh code path | all 35 districts | CLEAN, max abs diff 0.0 |
| Grade 4-6 enrolment universe | Recompute from by-grade CSVs, fresh path | 3 years x 3 definitions | CLEAN (matches to the child) |
| census2011_karnataka_district.csv (minimal fallback) | State-total consistency: population sums to official 61,095,297 exactly; weighted literacy 75.25 vs official 75.36 (weight basis differs) | 30 districts, 3 indicators | CONSISTENT; source is aggregator sites, upgrade via prep/01 on Friday |
| karnataka_district_crosswalk.csv | Structural: 31 districts, codes 555-584 contiguous and unique, divisions 9/8/7/7, 371J=7 | full | CLEAN |
| Context findings C1-C8 | Independent recompute of each quoted number | all | CLEAN after 2 fixes (see below) |

## Fixes made during verification
1. C7 lowest-5 list printed "Belagavi" twice because educational district Belagavi Chikkodi was collapsed to its revenue parent. Now prints educational district names.
2. DATA_UNIVERSE attributed the lowest PTRs to "Mysuru division"; the lowest four span Mysuru and Bengaluru divisions. Reworded.

## Known caveats that stay (do not present these numbers without the caveat)
- NFHS-5 mirror is a mirror. The repo itself says "recheck with source". Cell-fidelity to the mirror is proven; fidelity of mirror to rchiips.org PDFs is not independently proven here (rchiips blocks headless fetch). Bangalore pre-primary (23.4) is flagged in the source as based on 25-49 unweighted cases.
- The NFHS-5 columns hh_electricity_pct and hh_improved_sanitation_pct are population-living-in-households shares, not household shares. Values correct, names slightly loose.
- ASER's own report has internal 0.1pp inconsistencies between its trend tables and Table 15. Our CSV matches the trend tables (the govt+pvt weighted series). If a judge cross-checks against Table 15, the 0.1 differences are ASER's, not ours.
- PGI-D maps_to_district and the crosswalk's princely_legacy / is_371J columns are our editorial additions, not source data.
- context_pack script hard-codes two verified literals (35.6 vs 22.2 PTR contrast; 16.2% non-Kannada enrolment share). Verified 30 Jul 2026 against parquet recompute; recheck if UDISE inputs change.
- KSNDMC drought-taluk counts (223/196) and all Tier-1/2 external URLs in DATA_UNIVERSE are agent-verified as existing but their contents are not yet cell-verified. Verify any number you quote from them on Friday.

## Addendum, census upgrade (30 July, evening)
Census 2011 PCA pulled through the participant's browser (sandbox egress to data.gov.in was
throttled). 176 CD-block records, all 30 districts. Validation: block-universe population sums to
38,931,799, consistent with rural + census-town coverage (state total 61,095,297 includes statutory
towns, which this catalog stores as separate TOWN rows, not fetched); block-universe SC 19.65% / ST
8.95% vs full-state 17.15% / 6.95%, direction consistent with rural skew; Bagalkot block-universe
literacy 64.49 vs verified full-district 68.82, rural skew as expected. District file keeps verified
full-universe population/literacy/sex-ratio and adds SC/ST/worker columns computed over the block
universe, labelled as such in a note column. Educational-block fuzzy match: 85.1% of blocks matched
(exact norm + within-district difflib at 0.72); unmatched blocks carry NaN, never a guessed value.

## Addendum, 31 July: PARAKH RS 2024 district extract
Scraped from the PARAKH dashboard (charts publish integers). Verification status PARTLY: extraction
method documented in PRS2024/README_source_and_method.md, 6 areas double-scraped identically, 3 cells
hand-verified against the live dashboard. Not yet cell-verified against a PARAKH technical report
(none exposes district tables). Rules for use: quote integers, treat 1-point gaps as ties, always name
the state-government subgroup when comparing to our data. Engine hypotheses H12/H13 consume it.

## Addendum, 31 July evening: PRS 2024 verified against the official NCERT state report
Report_Karnataka_IND29.pdf (NCERT 2025, ISBN 978-93-5729-683-0) checked against the dashboard extract.
STATE level: every decodable mathematics value matches across all three grades and all four subgroup
families (gender, location, management incl. state-govt 59/40/29, social group). Status upgraded
PARTLY -> VERIFIED at state level. DISTRICT level: the report carries percentile-band maps, not numeric
tables, so district numbers remain dashboard-only and keep PARTLY status with the documented caveats.
NEW extract: prs2024_karnataka_competencies_math.csv (34 rows, grades 3/6/9 maths by NCF competency,
spot-asserted 6 cells). Grade-6 floor: fractions C-1.2 at 26% (national 29%).
