# Hypothesis menu (all tested on full data, n=1,379,087 students)


## SUPPORTED

**EH1. G6 multiplicative decline survives inside a constant-GP panel (same GPs all 3 years)**
- effect: panel (k=2182 GPs): mult 50.5->30.8 (-19.7pp vs raw -15.8pp, 125% persists); div 54.5->32.5 (-22.0pp vs raw -17.4pp, 127% persists)
- evidence: GPs with >=10 G6 students in every year; student-weighted
- caveat: items change each year; competency-level comparison assumes similar within-competency difficulty; panel GPs are earlier joiners, not a random subset
- policy: If it survives, the G6 collapse is real deterioration, not new-GP composition; remediation, not measurement, is the response.

**EH3. G6 decline present even in districts whose coverage changed least**
- effect: bottom-tercile |d_cov| (9 districts, mean |d_cov|=4.2pp): mult -18.7pp, div -21.5pp (all-district: -20.1/-22.6)
- evidence: unweighted district means
- caveat: coverage change is district-level; within-district reach can still shift
- policy: Decline without a coverage story in these districts undercuts the pure-selection explanation.

**EH5. A G6 multiplication decline remains after controlling district coverage change**
- effect: regression d(mult) = -19.32 -0.03*d_cov (n=25); predicted decline at zero coverage change: -19.3pp (raw mean -20.1pp, sd 4.1)
- evidence: district-level OLS
- caveat: linear control only; unmeasured within-district selection can remain
- policy: The coverage-free decline estimate is the honest headline number for the G6 collapse.

**EH6. G6 decline appears even in districts already deeply covered in 2022-23 (>=40%)**
- effect: 11 districts with 2022-23 coverage >=40%: mult -19.8pp, div -21.7pp
- evidence: these districts had least room for compositional dilution
- caveat: small n; deep-start districts may differ in other ways
- policy: Same conclusion as EH1 by a different route; two independent designs agreeing is strong evidence.

**EH7. The district league table changes once you adjust for who was assessed (coverage)**
- effect: cov-score r=0.55 (p=0.00373, n=26); 17 districts move >=3 ranks after adjustment; biggest: Raichur 19->12; Hassan 4->11; Gadag 15->20; Kodagu 13->8
- evidence: 2024-25, linear adjustment
- caveat: adjustment is descriptive, not a causal correction
- policy: Never publish a raw league table from a voluntary contest; always publish coverage next to rank.

**EH9. Girls still lead in districts where boys and girls are assessed at near-equal rates (|coverage gap|<=2pp)**
- effect: balanced district-years (n=25): girls-boys score gap +3.57pp (all: +2.79pp)
- evidence: balance defined on the verified UDISE rural State-Govt denominator
- caveat: n shrinks under the balance filter
- policy: A gap that survives balance is a real learning lead; report it with Cohen's d, not p-values.

**EH10. The girls' lead is stable across the three contest years despite coverage doubling**
- effect: girls-boys gap by year: 2022-23 +3.17pp, 2023-24 +2.55pp, 2024-25 +2.62pp
- evidence: unweighted mean of district gaps
- caveat: items change each year; competency-level comparison assumes similar within-competency difficulty
- policy: Stability across a doubling of reach argues the lead is not a participation artefact.

**EH11. Contest district ranking agrees with ASER 2024 rural arithmetic (like-for-like: rural, same age band)**
- effect: Spearman rho=0.56 (p=0.00362) vs ASER Std6-8 division; rho=0.30 (p=0.141) vs the other scale (n=25 districts)
- evidence: our 2024-25 district mean vs ASER 2024 district estimates
- caveat: ASER district samples are small (~600 kids)
- policy: External agreement validates the contest as a measurement instrument; that is a policy asset in itself.

**EH13. One competency is the best single proxy for overall performance**
- effect: mean corr with rest-of-test across 9 grade-years: division 0.67, measurement 0.67, multiplication 0.66, subtraction 0.65, number_sense 0.62, addition 0.62, shapes 0.58
- evidence: part-whole overlap removed (competency correlated with the OTHER competencies only)
- caveat: correlation, not sequencing
- policy: A short division screener could stand in for the whole test between contest rounds.

**EH14. Mastery is a ladder: conditional mastery gaps are large (prerequisite structure)**
- effect: largest lift: addition -> subtraction (+48pp: 72% vs 24%); multiplication -> division lift +45pp
- evidence: pooled across files
- caveat: conditional probability, not causal ordering
- policy: Remediation should sequence: secure the prerequisite before drilling the dependent skill.

**EH15. Low-performing GPs are also the most internally unequal**
- effect: corr(GP mean, GP sd) r=-0.62 (p=0, n=5599 GPs with >=15 students)
- evidence: GP-level, all years pooled
- caveat: sd is bounded near the score ceiling, which inflates the negative corr
- policy: The worst GPs need whole-class remediation, not just tail-targeting.

**EH16. Where coverage grew most, the measured floor (p10) fell most (the tail is who arrived)**
- effect: corr(d_coverage, floor change) r=-0.54 (p=0.00507, n=25 districts)
- evidence: p10 change 2022-23 -> 2024-25
- caveat: floor and coverage both move with district effort
- policy: Falling floors in expanding districts are a triage signal, not necessarily deterioration.

**EH18. Bright-spot blocks cluster in a few districts (shared practice, not luck)**
- effect: chi-sq p=0.0219; 22 bright blocks, top districts: Belagavi 6, Tumakuru 3, Vijayapura 3
- evidence: expected counts proportional to district block counts
- caveat: residual-based flags; model cv_R2=0.26
- policy: If clustered, send the CRP cadre to study those districts' shared practices.

**EH19. The Kalyana Karnataka gap is widening across the three contest years**
- effect: 371J-minus-rest gap by year: 2022-23 -10.0pp, 2023-24 -11.9pp, 2024-25 -15.8pp
- evidence: student-weighted
- caveat: coverage grew fastest in some KK districts; part of the widening may be reach
- policy: A widening gap strengthens the case for KKRDB money to follow measured learning, not only infrastructure.

**EH23. The coastal top-of-table is measured on thin, likely selected samples**
- effect: Udupi pooled rank 1 of 29 on 5.7% coverage; Dakshina Kannada pooled rank 2 of 29 on 2.0% coverage; Uttara Kannada pooled rank 3 of 29 on 0.8% coverage; and Udupi, Uttara Kannada, Dakshina Kannada absent from the 2024-25 round entirely
- evidence: pooled across all three years, rural State-Govt coverage basis
- caveat: thin samples are noisy in both directions; this is a warning about reading the table, not a claim they are secretly weak
- policy: Do not hold coastal districts up as models until their coverage passes ~50%.

**EH24. Mean-vs-floor divergence concentrates where coverage grew fastest**
- effect: floor-minus-mean divergence by coverage-growth tercile: low +3.3, mid +1.6, high -7.5 pp
- evidence: district-level
- caveat: same selection caveat as EH16
- policy: Equity metrics from a voluntary contest must be read jointly with coverage.

**H5. Kalyana Karnataka (371J) gap, and whether inputs explain it**
- effect: raw gap -13.3 pp; after controlling ptr_govt+literacy_rate_7plus+u5_stunted_pct the gap is -4.8 pp (mostly explained by measured inputs)
- evidence: controls: ptr_govt, literacy_rate_7plus, u5_stunted_pct
- caveat: a decade of 371J funds; KKRDB education-year 2023-24 pushes the other way from 2023-24
- policy: Present the pair of numbers: the gap, and the gap after controls. That is the policy slide.

**H7. Averages move without the weakest children moving**
- effect: 12 of 25 districts show mean up while the 10th percentile lagged (divergence < 0)
- evidence: floor = 10th percentile of student % correct
- caveat: items changed yearly: frame as ranking/shape shifts, not point gains
- policy: Lead the equity slide with the count; name 2 districts each way.

**H11. The learning map follows pre-1956 administrative borders**
- effect: legacy-group means: Bombay 60.5; Coorg 54.4; Hyderabad 45.9; Madras 58.2; Mysore 54.9 (ANOVA p=0.036)
- evidence: coded by us from States Reorganisation Act literature; verify before quoting
- caveat: explains, never excuses; do not present without the 371J-inputs slide next to it
- policy: Innovation slide if SUPPORTED. Framing: a 70-year inheritance, not a verdict on anyone today.


## WEAK

**EH21. A handful of items behave differently by gender (DIF screen)**
- effect: 5 of 180 item-year-grades with |girls-boys| >= 5pp (mostly girls-favoured)
- evidence: raw gap screen, not ability-matched DIF
- caveat: crude screen; proper DIF needs matching on total score
- policy: Flag for item review; do not over-read single items.

**H12. Akshara district ranking replicates in PARAKH RS 2024 grade-6 maths (govt schools)**
- effect: Spearman rho=0.51 (p=0.00431, n=29 districts)
- evidence: compared against the state-government subgroup column, the same management universe
- caveat: PARAKH publishes integers and samples ~1,300 schools statewide; ties within 1 point
- policy: Moderate agreement; cite as partial corroboration only.

**H13. District gender gaps replicate in PARAKH RS 2024**
- effect: r=-0.15 (p=0.431); sign agreement 76% of 29 districts
- evidence: PARAKH statewide shows girls +2 at grades 3 and 6, 0 by grade 9
- caveat: both instruments are cross-sectional; agreement supports the pattern, not a cause
- policy: If SUPPORTED: one line that the gender pattern is not an artefact of our instrument.


## DISCARD

**EH2. G4 division improvement survives inside the constant-GP panel**
- effect: panel (k=2278 GPs): G4 div 39.0->38.4 (-0.6pp vs raw +5.6pp)
- evidence: same panel construction as EH1
- caveat: items change each year; competency-level comparison assumes similar within-competency difficulty
- policy: A real G4 gain alongside a real G6 loss points at the upper-primary transition, not at a cohort-wide shock.

**EH4. Districts that widened coverage most saw scores fall most (selection story)**
- effect: r=-0.18 (p=0.396, n=25 districts); slope -0.33pp score per +10pp coverage
- evidence: change 2022-23 -> 2024-25, rural State-Government basis both sides
- caveat: ecological correlation; district coverage growth also tracks admin effort
- policy: If supported, part of the reported decline is the contest reaching weaker children, which is a participation success, not only a learning failure.

**EH8. Differential participation by gender inflates the measured girls' lead**
- effect: r=-0.47 (p=1.25e-05, n=80 district-years) between (girls-boys coverage) and (girls-boys score); the sign is negative: where girls are over-assessed the measured lead is SMALLER
- evidence: all three years pooled, authoritative UDISE rural State-Govt denominator
- caveat: district-level; within-school selection unobserved
- policy: A negative sign means differential participation DEFLATES the measured lead, so the true gap is if anything larger than reported. That is the opposite of the usual worry, and it agrees with EH9, where balanced districts show a bigger lead.

**EH12. Agreement with ASER is better in well-covered districts (disagreement = coverage artefact)**
- effect: corr(coverage, |rank disagreement|) r=-0.01 (p=0.95, n=25)
- evidence: rank disagreement vs ASER Std3-5 subtraction
- caveat: two noisy rankings compared
- policy: If supported: fix coverage first, then trust the map.

**EH17. Districts named in the 2023 drought declaration declined more in the following year**
- effect: drought list resolves to 0 districts - no usable contrast
- evidence: event geography too broad or too narrow to test
- caveat: the 2023 drought covered most of the state
- policy: Cannot test with district contrast; say so in limitations.

**EH20. Some items barely discriminate and dilute the measure**
- effect: 0 of 180 item-year-grades with discrimination r<0.15; worst: 
- evidence: point-biserial vs total
- caveat: low discrimination can also mean everyone-right or everyone-wrong items
- policy: Hand the item list to Akshara's assessment team for the 2025-26 paper.

**EH22. GPs newly reached in 2024-25 score below veteran GPs (direct composition evidence)**
- effect: new GPs (k=655, 16% of G6 students): mean 53.1 vs veteran GPs 48.6 (gap +4.6pp)
- evidence: G6 2024-25, GPs with >=5 students
- caveat: new GPs may differ in remoteness and size, not only preparedness
- policy: Quantifies exactly how much of the 'decline' is the contest finding weaker children. Pair with EH1 for the full story.

**H1. Higher pupil-teacher ratio, lower scores**
- effect: r=-0.18 (p=0.0711, n=99 blocks)
- evidence: direction holds across years; controlled for Census block literacy. 
- caveat: PTR proxies remoteness too; partial control applied for block literacy
- policy: Do not present. If asked, say it was tested and found near-zero.

**H2. Non-Kannada-medium belts score differently on a Kannada-language test**
- effect: r=-0.01 (p=0.947, n=116 blocks)
- evidence: direction holds across years; 
- caveat: medium share is a school-stock measure, not the tested child's home language; upgrade: item-level word-problem vs computation split in the afternoon
- policy: Do not present. If asked, say it was tested and found near-zero.

**H4. NFHS-5 stunting districts still lag (the tested cohort IS that under-5 cohort)**
- effect: r=-0.04 (p=0.837, n=28 districts)
- evidence: direction holds across years; 
- caveat: NFHS-5 is 2019-21 and urban+rural; tested cohort born 2012-16 so exposure timing fits
- policy: Do not present. If asked, say it was tested and found near-zero.

**H6. Gender gap changes as maths gets harder**
- effect: girls-minus-boys: +2.3 pp on easiest tier vs +2.6 pp on hardest (rank r=-0.01, p=0.979)
- evidence: tiers = top/bottom third of competencies by overall mastery
- caveat: if the competency map was inferred rather than official, say so on the slide
- policy: Do not present a flip; report the flat overall gap with effect size instead.

**H8. Cohorts in teacher-starved blocks progress slower**
- effect: cohort progression -1.96 pp in top-PTR quartile vs -2.00 in bottom (diff 0.04, p=0.965)
- evidence: same cohort, same place, different children; composition can shift
- caveat: cross-year comparison carries the instrument caveat
- policy: Do not present; progression is not differential by PTR here.

**H9. Who-got-tested bias**
- effect: join too thin
- evidence: GP name match with UDISE below usable threshold
- caveat: expected fuzziness materialised
- policy: Fall back to district-level coverage in the afternoon if time allows.

**H10. High private-school presence, lower government-school scores (selection)**
- effect: r=-0.14 (p=0.133, n=116 blocks)
- evidence: direction holds across years; 
- caveat: composition/selection story, not school quality; CMS-E shows exit is income-graded
- policy: Do not present. If asked, say it was tested and found near-zero.

