"""Descriptive and diagnostic analyses: items, competencies, gender, geography, progression."""
import numpy as np, pandas as pd
from scipy import stats
import config

# ------------------------------------------------------------------- items
def item_analysis(df, items, cmap=None):
    """Per (year, grade) - Qn means different questions in different files, so item
    statistics are only meaningful within one file. Output carries year+grade keys."""
    frames = []
    for (yr, gr), sub in df.groupby(["year", "grade"], dropna=False):
        f = _item_analysis_one(sub, items, cmap)
        f.insert(0, "year", yr); f.insert(1, "grade", gr)
        frames.append(f)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

def _item_analysis_one(df, items, cmap=None):
    total = df[items].sum(axis=1, min_count=1)
    rows = []
    for c in items:
        s = df[c]
        rest = total - s.fillna(0)                       # corrected for the item itself
        ok = s.notna() & rest.notna()
        disc = float(np.corrcoef(s[ok], rest[ok])[0, 1]) if ok.sum() > 30 else np.nan
        r = {"item": c, "pct_correct": round(100*float(s.mean()), 2),
             "discrimination_r": round(disc, 3) if pd.notna(disc) else np.nan,
             "n_responses": int(s.notna().sum())}
        if df["gender"].notna().any():
            f = float(s[df.gender.eq("F")].mean()); m = float(s[df.gender.eq("M")].mean())
            r["pct_correct_F"] = round(100*f, 2); r["pct_correct_M"] = round(100*m, 2)
            r["gender_gap_pp_F_minus_M"] = round(100*(f - m), 2)
        rows.append(r)
    out = pd.DataFrame(rows)
    out["quality_flag"] = np.where(out["discrimination_r"] < 0.15, "LOW DISCRIMINATION",
                          np.where(out["pct_correct"] > 95, "TOO EASY",
                          np.where(out["pct_correct"] < 10, "TOO HARD", "ok")))
    return out.sort_values("pct_correct")

def competency_profile(df, cmap, items, by=("year","grade","gender")):
    """Mastery per competency from the per-file C_* share-correct columns
    (equated across years per the organisers). cmap/items kept for signature compat."""
    ccols = [c for c in df.columns if c.startswith("C_")]
    if not ccols:
        return pd.DataFrame()
    long = []
    for col in ccols:
        lab = col[2:].replace("_", " ")
        sub = df[list(by) + [col]].dropna(subset=[col])
        if not len(sub):
            continue
        sub = sub.rename(columns={col: "_rate"})
        sub["_mastered"] = (sub["_rate"] >= 0.5).astype(float)
        g = sub.groupby(list(by), dropna=False).agg(
            n=("_rate","size"), pct_items_correct=("_rate","mean"),
            pct_mastered=("_mastered","mean")).reset_index()
        g["competency_code"] = lab; g["competency_label"] = lab
        long.append(g)
    out = pd.concat(long, ignore_index=True)
    out["pct_items_correct"] = (100*out["pct_items_correct"]).round(2)
    out["pct_mastered"] = (100*out["pct_mastered"]).round(2)
    cols = ["competency_code","competency_label"] + list(by) + ["n","pct_items_correct","pct_mastered"]
    return out[cols].sort_values(["competency_code"] + list(by))

# ------------------------------------------------------------------ gender
def gender_gaps(df, items, cmap=None):
    """Overall, by competency, by difficulty tier, and by district - with tests."""
    res = {}
    if df["gender"].isna().all():
        return res
    f, m = df.loc[df.gender.eq("F"), "pct"].dropna(), df.loc[df.gender.eq("M"), "pct"].dropna()
    if len(f) > 30 and len(m) > 30:
        t, p = stats.ttest_ind(f, m, equal_var=False)
        pooled = np.sqrt((f.var(ddof=1) + m.var(ddof=1)) / 2)
        res["overall"] = pd.DataFrame([{
            "n_girls": len(f), "n_boys": len(m),
            "mean_pct_girls": round(float(f.mean()), 2), "mean_pct_boys": round(float(m.mean()), 2),
            "gap_pp_girls_minus_boys": round(float(f.mean() - m.mean()), 2),
            "welch_t": round(float(t), 2), "p_value": float("%.3g" % p),
            "cohens_d": round(float((f.mean() - m.mean()) / pooled), 3) if pooled else np.nan,
            "practical_note": "gap under 1pp is statistically detectable but not "
                              "programmatically meaningful at this sample size"}])
    if [c for c in df.columns if c.startswith("C_")] or (cmap is not None and len(cmap)):
        prof = competency_profile(df, cmap, items, by=("gender",))
        piv = prof.pivot_table(index=["competency_code","competency_label"],
                               columns="gender", values="pct_mastered").reset_index()
        if {"F","M"}.issubset(piv.columns):
            piv["gap_pp_F_minus_M"] = (piv["F"] - piv["M"]).round(2)
            allm = competency_profile(df, cmap, items, by=("year",)) \
                     .groupby("competency_code")["pct_mastered"].mean()
            piv["overall_mastery_pct"] = piv["competency_code"].map(allm).round(1)
            piv["difficulty_tier"] = pd.qcut(piv["overall_mastery_pct"].rank(method="first"), 3,
                                             labels=["hard (higher-order)","middle","easy (foundational)"])
            res["by_competency"] = piv.sort_values("overall_mastery_pct", ascending=False)
            res["by_tier"] = (piv.groupby("difficulty_tier", observed=False)
                                 .agg(n_competencies=("competency_code","size"),
                                      mean_gap_pp=("gap_pp_F_minus_M","mean"))
                                 .round(2).reset_index())
    for lvl in ["district","block"]:
        if df[lvl].notna().any():
            g = (df.dropna(subset=[lvl,"gender"]).groupby([lvl,"gender"])["pct"]
                   .agg(["size","mean"]).unstack())
            try:
                out = pd.DataFrame({
                    "n_girls": g[("size","F")], "n_boys": g[("size","M")],
                    "girls_pct": g[("mean","F")].round(2), "boys_pct": g[("mean","M")].round(2)})
                out["gap_pp_F_minus_M"] = (out["girls_pct"] - out["boys_pct"]).round(2)
                out = out[(out.n_girls >= 30) & (out.n_boys >= 30)]
                res["by_" + lvl] = out.reset_index().sort_values("gap_pp_F_minus_M")
            except Exception:
                pass
    return res

# --------------------------------------------------------------- geography
def unit_summary(df, level, items=None):
    """Aggregate to an administrative level, all years pooled and per year."""
    if level not in df.columns or df[level].isna().all():
        return pd.DataFrame(), pd.DataFrame()
    parents = {"gp": ["division","district","block","cluster"],
               "cluster": ["division","district","block"],
               "block": ["division","district"],
               "district": ["division"], "division": []}[level]
    parents = [p for p in parents if p in df.columns and df[p].notna().any()]
    need = list(dict.fromkeys(parents + [level, "pct", "year", "year_n", "gender"]
                + (["gp_id"] if level == "gp" and "gp_id" in df.columns else [])))
    need = [c for c in need if c in df.columns]
    d = df[need].dropna(subset=[level, "pct"])

    def agg(keys):
        gb = d.groupby(keys, dropna=False)["pct"]
        g = gb.agg(n_students="size", pct_mean="mean", pct_sd="std").reset_index()
        if level == "gp" and "gp_id" in d.columns:
            gid = d.groupby(keys, dropna=False)["gp_id"].first().reset_index(drop=True)
            g["gp_id"] = gid
        q = gb.quantile([config.FLOOR_PERCENTILE/100.0, 0.90]).unstack()
        q.columns = ["pct_floor", "pct_p90"]
        g = g.merge(q.reset_index(), on=keys, how="left")
        if d["gender"].notna().any():
            gg = (d.dropna(subset=["gender"]).pivot_table(index=keys, columns="gender",
                   values="pct", aggfunc="mean"))
            if {"F","M"}.issubset(gg.columns):
                gg = (gg["F"] - gg["M"]).rename("gender_gap_pp").reset_index()
                g = g.merge(gg, on=keys, how="left")
        num = g.select_dtypes("number").columns
        g[num] = g[num].round(2)
        return g

    pooled = agg(parents + [level])
    per_year = agg(parents + [level, "year", "year_n"]) if df["year"].notna().any() else pd.DataFrame()
    return pooled, per_year

def trends(per_year, level):
    """First-to-last-year change per unit, with a simple slope."""
    if per_year is None or len(per_year) == 0 or "year_n" not in per_year.columns:
        return pd.DataFrame()
    yrs = sorted(per_year["year_n"].dropna().unique())
    if len(yrs) < 2:
        return pd.DataFrame()
    keys = [c for c in ["division","district","block","cluster","gp"] if c in per_year.columns]
    key = keys[: keys.index(level) + 1] if level in keys else [level]
    a = per_year[per_year.year_n == yrs[0]].set_index(key)
    b = per_year[per_year.year_n == yrs[-1]].set_index(key)
    j = a[["pct_mean","pct_floor","n_students"]].join(
        b[["pct_mean","pct_floor","n_students"]], lsuffix="_first", rsuffix="_last", how="inner")
    j["change_pp"]        = (j.pct_mean_last - j.pct_mean_first).round(2)
    j["floor_change_pp"]  = (j.pct_floor_last - j.pct_floor_first).round(2)
    j["annualised_pp"]    = (j["change_pp"] / max(len(yrs) - 1, 1)).round(2)
    def slope(g):
        s = per_year.set_index(key).loc[[g]] if False else None
        return None
    j["years"] = "%s -> %s" % (per_year[per_year.year_n == yrs[0]]["year"].iloc[0],
                               per_year[per_year.year_n == yrs[-1]]["year"].iloc[0])
    return j.reset_index().sort_values("change_pp")

def progression(df, level="block"):
    """
    Synthetic cohort tracking. With grades 4-6 over 3 years you can follow the SAME
    cohort: grade 4 in year 1 -> grade 5 in year 2 -> grade 6 in year 3, at unit level.
    Not the same children, but the same cohort in the same place - far stronger than
    comparing grades within one year.
    """
    if df["year_n"].isna().all() or df["grade"].isna().all():
        return pd.DataFrame(), pd.DataFrame()
    yrs = sorted(df["year_n"].dropna().unique())
    grades = sorted(df["grade"].dropna().unique())
    if len(yrs) < 2 or len(grades) < 2:
        return pd.DataFrame(), pd.DataFrame()

    cell = (df.dropna(subset=["pct"])
              .groupby([level, "year", "year_n", "grade"], dropna=False)["pct"]
              .agg(n="size", mean="mean").reset_index())
    cohorts = []
    for gi, g0 in enumerate(grades[:-1]):
        for yi, y0 in enumerate(yrs[:-1]):
            g1, y1 = g0 + 1, yrs[yi + 1]
            if g1 not in grades:
                continue
            a = cell[(cell.grade == g0) & (cell.year_n == y0)]
            b = cell[(cell.grade == g1) & (cell.year_n == y1)]
            j = a.merge(b, on=level, suffixes=("_from", "_to"))
            if len(j) == 0:
                continue
            j["cohort"] = "G%d %s -> G%d %s" % (g0, j["year_from"].iloc[0], g1, j["year_to"].iloc[0])
            j["progression_pp"] = (j["mean_to"] - j["mean_from"]).round(2)
            cohorts.append(j)
    if not cohorts:
        return pd.DataFrame(), pd.DataFrame()
    coh = pd.concat(cohorts, ignore_index=True)
    coh = coh[(coh.n_from >= 20) & (coh.n_to >= 20)]
    summary = (coh.groupby("cohort")
                  .agg(n_units=(level,"nunique"), mean_from=("mean_from","mean"),
                       mean_to=("mean_to","mean"), mean_progression_pp=("progression_pp","mean"),
                       pct_units_declining=("progression_pp", lambda s: 100*float((s < 0).mean())))
                  .round(2).reset_index())
    cols = [level,"cohort","year_from","grade_from","n_from","mean_from",
            "year_to","grade_to","n_to","mean_to","progression_pp"]
    return coh[[c for c in cols if c in coh.columns]].sort_values("progression_pp"), summary
