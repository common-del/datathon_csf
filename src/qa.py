"""Data integrity and anomaly checks. Run BEFORE believing any finding."""
import numpy as np, pandas as pd, config

def run(df, meta):
    items, n_items = meta["items"], meta["n_items"]
    L, flags = [], []
    def add(k, v, note=""): L.append({"check": k, "value": v, "note": note})
    def flag(sev, msg): flags.append({"severity": sev, "issue": msg})

    add("rows", len(df))
    add("question_items_found", n_items,
        "handbook says 20" + ("" if n_items == 20 else "  <-- MISMATCH, verify"))
    if n_items != 20:
        flag("HIGH", "Found %d item columns, expected 20. Check config.MANUAL_ITEM_COLUMNS." % n_items)

    key = [c for c in ["year","grade","district","block","cluster","gp","gender"]
           if df[c].notna().any()] + items
    dup = int(df.duplicated(subset=key).sum())
    add("exact_duplicate_rows", dup, "identical on geography + all item responses")
    if dup > 0:
        add("duplicate_rows_note", "EXPECTED, not an error: no persistent student or school "
            "identifier exists, so two children with identical geography, gender and all 20 "
            "responses are indistinguishable by design. Rows are KEPT; deduplicating would "
            "delete real children.")

    for c in ["year","grade","district","block","cluster","gp","gender"]:
        miss = 100.0*df[c].isna().mean()
        add("missing_pct__" + c, round(miss, 2))
        if miss > 5:
            flag("MEDIUM" if miss < 30 else "HIGH", "%s missing in %.1f%% of rows." % (c, miss))

    inc = 100.0*(df["n_attempted"] < n_items).mean()
    add("rows_with_missing_responses_pct", round(inc, 2))
    if inc > 2:
        flag("MEDIUM", "%.1f%% of students have at least one blank response. "
                       "Scores computed on attempted items only." % inc)

    if df["score_given"].notna().any():
        cmp_ = df.dropna(subset=["score_given","score_items"])
        d = (cmp_["score_given"] - cmp_["score_items"]).abs()
        bad = int((d > 0.001).sum())
        add("score_column_vs_item_sum_mismatches", bad,
            "provided Score vs recomputed sum of items")
        if bad > 0:
            flag("HIGH", "%d rows where the provided Score does not equal the sum of Q1..Qn "
                         "(%.2f%%). Report which one you used." % (bad, 100.0*bad/max(len(cmp_),1)))

    diff = df[items].mean().sort_values()
    add("easiest_item", "%s (%.1f%% correct)" % (diff.index[-1], 100*diff.iloc[-1]))
    add("hardest_item", "%s (%.1f%% correct)" % (diff.index[0], 100*diff.iloc[0]))
    dead = [c for c in items if df[c].nunique(dropna=True) < 2]
    add("items_with_no_variation", len(dead), ", ".join(map(str, dead)))
    if dead:
        flag("HIGH", "Items with no variation (everyone same answer): %s" % ", ".join(map(str, dead)))
    for c in items:
        m = df[c].mean()
        if pd.notna(m) and (m < 0.02 or m > 0.98):
            flag("LOW", "Item %s is near-degenerate (%.1f%% correct) - weak for analysis." % (c, 100*m))

    s = df["score"].dropna()
    add("score_mean", round(float(s.mean()), 3))
    add("score_sd", round(float(s.std()), 3))
    add("pct_scoring_zero", round(100.0*float((s == 0).mean()), 2))
    add("pct_scoring_full", round(100.0*float((s == n_items).mean()), 2))
    if len(s):
        counts = s.value_counts().reindex(range(0, n_items+1), fill_value=0)
        exp = len(s)/(n_items+1)
        spike = counts[counts > 4*exp]
        add("score_values_over_4x_uniform", ", ".join("%d" % v for v in spike.index),
            "possible heaping / data-entry artefact")
        if (s == n_items).mean() > 0.10:
            flag("MEDIUM", "%.1f%% of students score full marks - possible ceiling effect."
                 % (100*(s == n_items).mean()))

    # Geography keys are stable IDs (GP ID canonical; block/cluster IDs derived from GP-ID
    # overlap in prep/06_build_geo_ids.py), so name-collision and nesting checks are moot.
    # GP and Cluster are independent hierarchies and are never assumed to nest.
    add("geography_key_basis", "GP ID canonical; block_id/cluster_id derived from GP-ID overlap")

    if df["year"].notna().any() and df["district"].notna().any():
        sets = df.dropna(subset=["district"]).groupby("year")["district"].agg(set)
        if len(sets) > 1:
            common = set.intersection(*sets)
            add("districts_present_every_year", len(common))
            for y, s_ in sets.items():
                extra = s_ - common
                if extra:
                    add("districts_only_in_some_years__%s" % y, ", ".join(sorted(extra))[:120])
            if any(len(s_ - common) for s_ in sets):
                flag("HIGH", "Contest COVERAGE changes across years (not a naming problem: the "
                             "organiser crosswalk resolves names). Districts appear or drop out "
                             "between years, so state-level year trends mix real change with "
                             "coverage change. Restrict cross-year claims to the %d districts "
                             "present in all three years, and say so." % len(common))

    if df["year"].notna().any() and df["grade"].notna().any():
        cov = df.pivot_table(index="year", columns="grade", values="score", aggfunc="size")
        add("year_x_grade_cells", int(cov.notna().sum().sum()))
        thin = int((cov.fillna(0) < 100).sum().sum())
        if thin:
            flag("LOW", "%d year x grade cells have under 100 students." % thin)
    for lvl, mn in [("gp", config.MIN_STUDENTS_PER_GP), ("block", config.MIN_STUDENTS_PER_BLOCK)]:
        if df[lvl].notna().any():
            n = df.groupby(lvl).size()
            add("%s_units_total" % lvl, int(len(n)))
            add("%s_units_below_min_n" % lvl, int((n < mn).sum()),
                "excluded from rankings (min n = %d)" % mn)

    if df["gender"].notna().any():
        vc = df["gender"].value_counts(normalize=True)
        add("gender_share_F", round(100*float(vc.get("F", 0)), 2))
        if abs(float(vc.get("F", 0)) - 0.5) > 0.08:
            flag("LOW", "Gender split is %.1f%% F - note it, do not assume balance."
                 % (100*float(vc.get("F", 0))))

    qa = pd.DataFrame(L)
    fl = pd.DataFrame(flags) if flags else pd.DataFrame(columns=["severity","issue"])
    order = {"HIGH":0,"MEDIUM":1,"LOW":2}
    if len(fl):
        fl = fl.sort_values("severity", key=lambda s: s.map(order)).reset_index(drop=True)
    return qa, fl
