# Data sources and citations

Copy the relevant lines into `report.pdf` and `manifest.yml`. All external data here is public.

## Primary

**Akshara Foundation competency-based mathematics assessment**, Karnataka government schools, grades 4 to 6, three assessment years, 20 items across 10 competencies, disaggregated to Gram Panchayat. Provided on the event intranet on Day 1. Not redistributed, not committed to the repository. https://akshara.org.in/

## External, pre-loaded in `external_data/`

**1. Census 2011 Primary Census Abstract, Karnataka** (village, CD-Block and district level).
Registrar General and Census Commissioner, Ministry of Home Affairs, via data.gov.in.
Catalog: https://www.data.gov.in/catalog/villagetown-wise-primary-census-abstract-2011-karnataka
Retrieved through the data.gov.in API by `prep/01_fetch_census.py`. 30,064 records.
Files: `census2011_karnataka_district.csv`, `census2011_karnataka_block.csv`

**2. NFHS-5 district fact sheets, Karnataka** (2019–21). 30 districts, 11 indicators covering women's schooling, child stunting, wasting, underweight, anaemia, sanitation, electricity and early marriage.
International Institute for Population Sciences. Accessed via the CSV mirror at
https://raw.githubusercontent.com/pratapvardhan/NFHS-5/master/district-level/NFHS-5-KA-Karnataka.csv
Original fact sheets: http://rchiips.org/nfhs/
File: `nfhs5_karnataka_districts.csv`
*Note: this is a mirror of the official fact sheets, not the primary PDF. Verify any headline figure against rchiips.org before quoting it in the report.*

**3. ASER 2024 (rural), Karnataka district estimates.** ASER Centre / Pratham.
District estimates: https://asercentre.org/wp-content/uploads/2022/12/Karnataka_District-Estimates.pdf
State pages: https://asercentre.org/wp-content/uploads/2022/12/Karnataka-1.pdf
Files: `aser2024_karnataka_districts.csv`, `aser_karnataka_trend.csv`
*Note: district estimates pool grades 3–5 and 6–8, so they are NOT the same metric as the state Std III / Std V figures. Roughly 30 villages per district, and ASER publishes no confidence intervals, so treat district figures as indicative.*

**4. Performance Grading Index for Districts (PGI-D) 2025-26.** Department of School Education and Literacy, Ministry of Education. Released 8 July 2026. 35 Karnataka educational districts, 600 points across 6 categories.
Report: https://dpgi.udiseplus.gov.in/apis/backend/downloadreport/DISTRICT-PGID-2025-26-ENGLISH
Portal: https://dpgi.udiseplus.gov.in/
File: `pgid_2025_26_karnataka.csv`
*Note: the learning-outcomes domain draws on PARAKH Rashtriya Sarvekshan 2024, which NCERT states is not comparable with earlier NAS rounds. Do not build a year-on-year PGI-D improvement narrative across that break.*

**5. UDISE+ school records, Karnataka, 2022-23 to 2024-25.** Department of School Education and Literacy, Ministry of Education. 74,859 Karnataka schools in 2024-25, aggregated by `prep/02_build_udise_covariates.py` to district, block and Gram Panchayat level, restricted to schools serving at least one of grades 4 to 6.
Portal: https://dashboard.udiseplus.gov.in/
Files: `udise_karnataka_district_covariates.csv`, `udise_karnataka_block_covariates.csv`, `udise_karnataka_gp_covariates.csv`, `karnataka_geography_hierarchy.csv`
*Note: UDISE stores teacher counts as 16-bit integers. Aggregating and then multiplying overflows and produces negative percentages. Our build script casts to float first. If you recompute anything from UDISE yourself, do the same.*

**6. Karnataka district crosswalk** (compiled for this submission).
Maps all 31 revenue districts and 35 educational districts across Census 2011 names, NFHS-5 names, ASER 2024 names, PGI-D names and current official spellings, with Census 2011 district codes 555–584 and revenue division.
File: `karnataka_district_crosswalk.csv`
*Note: Vijayanagara was created in 2021 from Ballari and has no Census 2011 denominator. Any per-capita figure for Vijayanagara or post-2021 Ballari needs either a merge back to a single Ballari unit or a taluk-level rebuild. Decide which before modelling.*

## Reference, not joined

Karnataka At A Glance 2024-25: https://kgis.ksrsac.in/KAGREPORT2026/2024-25/%23DAG%20Updated/KAG_Report_2024-25.pdf
SSLC 2025 exam statistics, KSEAB: https://kseab.karnataka.gov.in/new-page/SSLC%202025%20Exam-1%20Statistics/en
NITI Aayog SDG India Index: https://www.niti.gov.in/
Karnataka Open Data Portal: https://karnataka.data.gov.in/

## Known joining hazards

1. **District universes differ.** NFHS-5 has 30 pre-2021-named districts. ASER 2024 has 30 current-named. PGI-D and UDISE have 35 educational districts. The assessment data has whatever it has. Always state the level and the match rate.
2. **Vintage spread is 15 years.** Census 2011 to UDISE 2024-25. Treat Census and NFHS as structural conditions, not current controls.
3. **Universe mismatch.** NFHS-5 district figures combine urban and rural. ASER is rural only. Bengaluru Urban is the worst case; joining the two there produces something close to nonsense.
4. **Cluster has no external source.** UDISE carries no cluster field. Cluster mapping must be derived from the assessment file itself.
5. **GP names repeat across blocks.** Always key on district + block + GP.

## Added 30 July 2026

**7. NFHS-6 fact sheets (2023-24), state level.** IIPS/MoHFW compilation, May 2026, from the PDF in the Datathon folder. 101 indicators, NFHS-6 urban/rural/total plus NFHS-5 total.
Files: `nfhs6_karnataka_state.csv`, `nfhs6_india_state.csv`
*Notes: state level only, no district fact sheets published yet; the NFHS-6 sheet carries no anaemia indicators, so NFHS-5 anaemia has no update path. District joins stay on NFHS-5; use NFHS-6 as the current benchmark and for direction of travel.*

**8. UDISE+ Karnataka school-level CSVs.** Full extracts from the parquets: `data/udise_csv/udise_ka_school_<year>.csv` (163 columns, ~75k schools each) and `udise_ka_enrolment_by_grade_<year>.csv` (grade-wise boys/girls counts per school, Social Category totals) for 2022-23, 2023-24, 2024-25.

**9. Grade 4-6 enrolment denominators, GP level.** `udise_karnataka_gp_grade46_enrolment.csv`: total, government, and girls grade 4-6 enrolment per district x block x GP x year. Purpose: assessment coverage ratio (tested / enrolled), the who-got-tested check.

**10. Crosswalk additions.** `karnataka_district_crosswalk.csv` now carries `is_371J_kalyana_karnataka` (7 districts) and `princely_legacy` (Hyderabad / Bombay / Madras / Mysore / Coorg), coded by us from the States Reorganisation Act 1956 literature. Verify before quoting in the report.

**11. Census 2011 PCA, upgraded 30 July.** `census2011_karnataka_block.csv`: 176 CD blocks, full indicator set with derived rates and rural share. `census2011_karnataka_district.csv`: verified full-universe population/literacy/sex-ratio plus SC/ST/worker columns computed over the CD-block universe (rural + census towns, ~64% of state population; statutory towns excluded), flagged in a note column. Block joins to educational blocks are fuzzy-matched at 85%; unmatched blocks carry NaN. `prep/01_fetch_census.py` remains for reproducibility.

**12. Pre-baked context pack.** `context_pack/` holds findings, tables and figures computable without the student data (see `CONTEXT_FINDINGS.md`). The Day-1 engine stays reserved for score-dependent analysis.

**13. PARAKH Rashtriya Sarvekshan 2024, Karnataka districts (added 31 July).** `prs2024_karnataka_maths.csv`: 31 districts x grades 3/6/9 maths, with boys/girls, rural/urban, management (incl. state-government subgroup) and social-group splits; plus the all-subjects file and raw extracts in `..\PRS2024\`. Extracted from the PARAKH dashboard charts; values are integers as published; ~1,300 sampled schools per grade statewide, thin subgroup cells in some districts. Method and caveats in `PRS2024/README_source_and_method.md`.
*Status: PARTLY verified. Extraction method documented, double-scrape consistency on 6 areas, 3 cells hand-checked against the live dashboard (Hassan G3=73, Ballari G6=34, Kolar G9=28). Treat 1-point differences as ties; do not rank aggressively.*

**14. ASER 2024 Karnataka District Estimates PDF** now stored locally (`..\ASER-Karnataka_District-Estimates-2024.pdf`) as source-of-record for the already-verified `aser2024_karnataka_districts.csv` (180/180 cells matched).
