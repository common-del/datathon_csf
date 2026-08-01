# Hypothesis verdicts (auto-generated; rules in src/day1_verdicts.py)

## SUPPORTED (3)

**H5. Kalyana Karnataka (371J) gap, and whether inputs explain it**
- Effect: raw gap -13.3 pp; after controlling ptr_govt+literacy_rate_7plus+u5_stunted_pct the gap is -4.8 pp (mostly explained by measured inputs)
- Evidence: controls: ptr_govt, literacy_rate_7plus, u5_stunted_pct
- Caveat: a decade of 371J funds; KKRDB education-year 2023-24 pushes the other way from 2023-24
- What to do: Present the pair of numbers: the gap, and the gap after controls. That is the policy slide.

**H7. Averages move without the weakest children moving**
- Effect: 12 of 25 districts show mean up while the 10th percentile lagged (divergence < 0)
- Evidence: floor = 10th percentile of student % correct
- Caveat: items changed yearly: frame as ranking/shape shifts, not point gains
- What to do: Lead the equity slide with the count; name 2 districts each way.

**H11. The learning map follows pre-1956 administrative borders**
- Effect: legacy-group means: Bombay 60.5; Coorg 54.4; Hyderabad 45.9; Madras 58.2; Mysore 54.9 (ANOVA p=0.036)
- Evidence: coded by us from States Reorganisation Act literature; verify before quoting
- Caveat: explains, never excuses; do not present without the 371J-inputs slide next to it
- What to do: Innovation slide if SUPPORTED. Framing: a 70-year inheritance, not a verdict on anyone today.

## WEAK (2)

**H12. Akshara district ranking replicates in PARAKH RS 2024 grade-6 maths (govt schools)**
- Effect: Spearman rho=0.51 (p=0.00431, n=29 districts)
- Evidence: compared against the state-government subgroup column, the same management universe
- Caveat: PARAKH publishes integers and samples ~1,300 schools statewide; ties within 1 point
- What to do: Moderate agreement; cite as partial corroboration only.

**H13. District gender gaps replicate in PARAKH RS 2024**
- Effect: r=-0.15 (p=0.431); sign agreement 76% of 29 districts
- Evidence: PARAKH statewide shows girls +2 at grades 3 and 6, 0 by grade 9
- Caveat: both instruments are cross-sectional; agreement supports the pattern, not a cause
- What to do: If SUPPORTED: one line that the gender pattern is not an artefact of our instrument.

## DISCARD (7)

**H4. NFHS-5 stunting districts still lag (the tested cohort IS that under-5 cohort)**
- Effect: r=-0.04 (p=0.837, n=28 districts)
- Evidence: direction holds across years; 
- Caveat: NFHS-5 is 2019-21 and urban+rural; tested cohort born 2012-16 so exposure timing fits
- What to do: Do not present. If asked, say it was tested and found near-zero.

**H2. Non-Kannada-medium belts score differently on a Kannada-language test**
- Effect: r=-0.01 (p=0.947, n=116 blocks)
- Evidence: direction holds across years; 
- Caveat: medium share is a school-stock measure, not the tested child's home language; upgrade: item-level word-problem vs computation split in the afternoon
- What to do: Do not present. If asked, say it was tested and found near-zero.

**H1. Higher pupil-teacher ratio, lower scores**
- Effect: r=-0.18 (p=0.0711, n=99 blocks)
- Evidence: direction holds across years; controlled for Census block literacy. 
- Caveat: PTR proxies remoteness too; partial control applied for block literacy
- What to do: Do not present. If asked, say it was tested and found near-zero.

**H9. Who-got-tested bias**
- Effect: join too thin
- Evidence: GP name match with UDISE below usable threshold
- Caveat: expected fuzziness materialised
- What to do: Fall back to district-level coverage in the afternoon if time allows.

**H8. Cohorts in teacher-starved blocks progress slower**
- Effect: cohort progression -1.96 pp in top-PTR quartile vs -2.00 in bottom (diff 0.04, p=0.965)
- Evidence: same cohort, same place, different children; composition can shift
- Caveat: cross-year comparison carries the instrument caveat
- What to do: Do not present; progression is not differential by PTR here.

**H6. Gender gap changes as maths gets harder**
- Effect: girls-minus-boys: +2.3 pp on easiest tier vs +2.6 pp on hardest (rank r=-0.01, p=0.979)
- Evidence: tiers = top/bottom third of competencies by overall mastery
- Caveat: if the competency map was inferred rather than official, say so on the slide
- What to do: Do not present a flip; report the flat overall gap with effect size instead.

**H10. High private-school presence, lower government-school scores (selection)**
- Effect: r=-0.14 (p=0.133, n=116 blocks)
- Evidence: direction holds across years; 
- Caveat: composition/selection story, not school quality; CMS-E shows exit is income-graded
- What to do: Do not present. If asked, say it was tested and found near-zero.

