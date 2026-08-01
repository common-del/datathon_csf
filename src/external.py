"""
Join the assessment data to external public datasets.
Every join reports its match rate. Unmatched names are written out so you can
state coverage honestly in the report instead of silently losing rows.
"""
import difflib, os, re
import numpy as np, pandas as pd
import config

def strip_id(s):
    """Our unit labels are '<ID> <name>' (e.g. 'B0007 BAILHONGAL', '1201 ADAGAL').
    External sources are name-keyed, so drop the leading ID token before matching."""
    t = str(s).strip()
    parts = t.split(" ", 1)
    if len(parts) == 2 and (parts[0].isdigit() or
                            (len(parts[0]) > 1 and parts[0][0] in "BC" and parts[0][1:].isdigit())):
        return parts[1]
    return t

def norm(s):
    s = strip_id(s)
    s = str(s).upper().strip()
    s = re.sub(r"\(.*?\)", " ", s)
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    for a, b in [(" DIST", ""), (" DISTRICT", ""), (" TALUK", ""), (" TALUKA", ""),
                 (" BLOCK", ""), (" GP", ""), (" GRAM PANCHAYAT", ""), (" URBAN", " U"),
                 (" RURAL", " R")]:
        if s.endswith(a):
            s = s[: -len(a)] + b
    return s.strip()

def _read(name):
    p = os.path.join(config.EXTERNAL, name)
    if not os.path.exists(p):
        print("      missing: %s" % name); return None
    try:
        return pd.read_csv(p)
    except Exception as e:
        print("      unreadable %s: %s" % (name, e)); return None

def build_alias_table():
    """Map every known spelling of a Karnataka district to one canonical key."""
    cw = _read("karnataka_district_crosswalk.csv")
    pg = _read("pgid_2025_26_karnataka.csv")
    rows = []
    if cw is not None:
        for _, r in cw.iterrows():
            can = r["current_name"]
            names = [r.get("current_name"), r.get("census2011_name"), r.get("nfhs5_name"),
                     r.get("aser2024_name")]
            for a in str(r.get("alt_spellings", "") or "").split(";"):
                names.append(a)
            for n in names:
                if isinstance(n, str) and n.strip():
                    rows.append({"alias_norm": norm(n), "canonical_district": can})
    if pg is not None:
        for _, r in pg.iterrows():
            rows.append({"alias_norm": norm(r["pgid_educational_district"]),
                         "canonical_district": r["maps_to_district"]})
    oc = _read("organiser_district_crosswalk.csv")
    if oc is not None and {"contest_district_value","standard_district"}.issubset(oc.columns):
        for _, r in oc.iterrows():
            for col in ["contest_district_value","standard_district","udise_join_name",
                        "nfhs_join_name","aser_join_name","kag_join_name"]:
                v = r.get(col)
                if isinstance(v, str) and v.strip():
                    rows.append({"alias_norm": norm(v), "canonical_district": None, "_std": r["standard_district"], "_v": v})
        # map organiser standard names onto our canonical current_name via norm equality/fuzzy
        std = {norm(x["_std"]): x["_std"] for x in rows if x.get("_std")}
        cur = {r["alias_norm"]: r["canonical_district"] for r in rows if r.get("canonical_district")}
        import difflib
        s2c = {}
        for n_, s_ in std.items():
            hit = cur.get(n_) or (cur.get(difflib.get_close_matches(n_, list(cur), 1, 0.85)[0])
                                  if difflib.get_close_matches(n_, list(cur), 1, 0.85) else None)
            s2c[s_] = hit or s_
        for x in rows:
            if x.get("canonical_district") is None and x.get("_std"):
                x["canonical_district"] = s2c.get(x["_std"], x["_std"])
    rows = [{"alias_norm": x["alias_norm"], "canonical_district": x["canonical_district"]}
            for x in rows if x.get("canonical_district")]
    t = pd.DataFrame(rows).drop_duplicates("alias_norm")
    return t

def match_districts(values, alias, label="district", cutoff=0.86):
    """Return a mapping frame with the method used for each name."""
    uniq = sorted({v for v in values if isinstance(v, str) and v.strip()})
    lut = dict(zip(alias["alias_norm"], alias["canonical_district"]))
    pool = list(lut.keys())
    out = []
    for v in uniq:
        n = norm(v)
        if n in lut:
            out.append({label: v, "canonical_district": lut[n], "match": "exact"}); continue
        hit = difflib.get_close_matches(n, pool, n=1, cutoff=cutoff)
        if hit:
            out.append({label: v, "canonical_district": lut[hit[0]],
                        "match": "fuzzy->%s" % hit[0]})
        else:
            out.append({label: v, "canonical_district": np.nan, "match": "UNMATCHED"})
    m = pd.DataFrame(out)
    ok = 100.0 * m["canonical_district"].notna().mean() if len(m) else 0.0
    print("      %s names: %d, matched %.1f%%" % (label, len(m), ok))
    bad = m[m["canonical_district"].isna()][label].tolist()
    if bad:
        print("      UNMATCHED: %s" % ", ".join(bad[:12]))
    return m

def district_covariates(alias):
    """One row per canonical district, every external source merged."""
    cw  = _read("karnataka_district_crosswalk.csv")
    if cw is None:
        return pd.DataFrame(), []
    base = cw[["current_name","revenue_division","census2011_name","nfhs5_name",
               "aser2024_name"]].rename(columns={"current_name":"canonical_district"})
    sources = []

    nf = _read("nfhs5_karnataka_districts.csv")
    if nf is not None:
        base = base.merge(nf, on="nfhs5_name", how="left")
        sources.append("NFHS-5 (2019-21) district fact sheets")

    ar = _read("aser2024_karnataka_districts.csv")
    if ar is not None:
        base = base.merge(ar, on="aser2024_name", how="left")
        sources.append("ASER 2024 Karnataka district estimates")

    pg = _read("pgid_2025_26_karnataka.csv")
    if pg is not None:
        p = (pg.groupby("maps_to_district")
               .agg(pgid_overall_600=("overall_600","mean"),
                    pgid_outcomes_290=("outcomes_290","mean"),
                    pgid_infra_51=("infra_entitlements_51","mean"),
                    pgid_digital_50=("digital_learning_50","mean"),
                    pgid_governance_84=("governance_84","mean"),
                    pgid_n_edu_districts=("pgid_educational_district","size")).reset_index()
               .rename(columns={"maps_to_district":"canonical_district"}))
        base = base.merge(p, on="canonical_district", how="left")
        sources.append("PGI-D 2025-26 (district performance grading)")

    pr = _read("prs2024_karnataka_maths.csv")
    if pr is not None:
        m = match_districts(pr["prs_district"].dropna().unique(), alias, "prs_district")
        pr = pr.merge(m[["prs_district","canonical_district"]], on="prs_district", how="left")
        keep = [c for c in pr.columns if c.startswith("prs24_")] + ["canonical_district"]
        base = base.merge(pr[keep], on="canonical_district", how="left")
        sources.append("PARAKH Rashtriya Sarvekshan 2024 district dashboard (achievement %, integers)")

    ud = _read("udise_karnataka_district_covariates.csv")
    if ud is not None:
        latest = sorted(ud["academic_year"].dropna().unique())[-1]
        u = ud[ud.academic_year == latest].copy()
        keep = ["revenue_district","ptr_govt","pct_female_teachers_govt",
                "pct_teachers_graduate_plus_govt","pct_sch_library_govt","pct_sch_playground_govt",
                "pct_sch_computer_lab_govt","pct_sch_internet_govt","pct_sch_tapwater_functional_govt",
                "pct_sch_preprimary_govt","girls_func_toilets_per_school_govt",
                "good_classrooms_per_school_govt","acad_inspections_per_school_govt",
                "mean_instruction_days_govt","avg_govt_school_size","pct_private_schools",
                "enrolment_govt","n_schools_govt"]
        u = (u[[c for c in keep if c in u.columns]]
               .groupby("revenue_district").mean(numeric_only=True).reset_index()
               .rename(columns={"revenue_district":"canonical_district"}))
        base = base.merge(u, on="canonical_district", how="left")
        sources.append("UDISE+ %s school records, aggregated (Karnataka)" % latest)

    cen = _read("census2011_karnataka_district.csv")
    if cen is not None and len(cen):
        cen = cen.copy()
        cen["census2011_name"] = cen["name"] if "name" in cen.columns else cen.get("district_name")
        keep = ["census2011_name","total_population_person","literacy_rate_7plus",
                "male_female_literacy_gap_pp","sex_ratio","sc_pct","st_pct",
                "work_participation_rate","agri_labour_share_of_workers","marginal_worker_share"]
        c = cen[[x for x in keep if x in cen.columns]].copy()
        c["census2011_name"] = c["census2011_name"].astype(str).str.strip()
        base = base.merge(c, on="census2011_name", how="left")
        sources.append("Census 2011 Primary Census Abstract, Karnataka (data.gov.in)")
    else:
        print("      NOTE: Census district file absent. Run prep/01_fetch_census.py with internet.")

    num = base.select_dtypes("number").columns
    base[num] = base[num].round(3)
    return base, sources

def attach(df, alias):
    """Add canonical_district to the student frame."""
    if "district" not in df.columns or df["district"].isna().all():
        df["canonical_district"] = np.nan
        return df, pd.DataFrame()
    m = match_districts(df["district"].dropna().unique(), alias, "district")
    df = df.merge(m[["district","canonical_district"]], on="district", how="left")
    return df, m

def unit_join(unit_df, level, alias):
    """
    Attach external covariates to a unit-level table.
    district -> full external stack.  block / gp -> UDISE + Census block where available.
    """
    if level == "district":
        cov, src = district_covariates(alias)
        if cov.empty:
            return unit_df, [], {}
        m = match_districts(unit_df[level].dropna().unique(), alias, level)
        out = unit_df.merge(m[[level,"canonical_district"]], on=level, how="left") \
                     .merge(cov, on="canonical_district", how="left")
        rate = 100.0*out["canonical_district"].notna().mean()
        return out, src, {"level":"district","match_rate_pct":round(rate,1),
                          "n_units":len(unit_df),"sources":src}

    ud = _read("udise_karnataka_%s_covariates.csv" % ("gp" if level == "gp" else "block"))
    if ud is None:
        return unit_df, [], {}
    latest = sorted(ud["academic_year"].dropna().unique())[-1]
    u = ud[ud.academic_year == latest].copy()
    drop = ["state","division","revenue_district","academic_year"]
    u = u.drop(columns=[c for c in drop if c in u.columns])
    if level == "gp":
        u["_k"] = u["district"].map(norm) + "|" + u["block"].map(norm) + "|" + u["gram_panchayat"].map(norm)
        unit_df = unit_df.copy()
        unit_df["_k"] = unit_df["district"].map(norm) + "|" + unit_df["block"].map(norm) + "|" + unit_df["gp"].map(norm)
        u = u.drop(columns=["district","block","gram_panchayat"])
    else:
        u["_k"] = u["district"].map(norm) + "|" + u["block"].map(norm)
        unit_df = unit_df.copy()
        unit_df["_k"] = unit_df["district"].map(norm) + "|" + unit_df["block"].map(norm)
        u = u.drop(columns=["district","block"])
    u = u.groupby("_k").mean(numeric_only=True).reset_index()
    out = unit_df.merge(u, on="_k", how="left").drop(columns=["_k"])
    probe = [c for c in out.columns if c.startswith("ptr_govt")]
    rate = 100.0*out[probe[0]].notna().mean() if probe else np.nan
    src = ["UDISE+ %s school records aggregated to %s level (Karnataka)" % (latest, level)]

    cen = _read("census2011_karnataka_block.csv")
    if cen is not None and len(cen) and level == "block":
        cen = cen.copy()
        keep = ["literacy_rate_7plus","male_female_literacy_gap_pp","sex_ratio","sc_pct",
                "st_pct","work_participation_rate","agri_labour_share_of_workers",
                "marginal_worker_share","total_population_person","rural_share_pct"]
        keep = [x for x in keep if x in cen.columns]
        cen["_d"] = cen["district_name"].map(norm)
        cen["_b"] = cen["name"].map(norm)
        # census district names are 2011 spellings; map to canonical then to norm
        m2011 = match_districts(cen["district_name"].dropna().unique(), alias, "census_district")
        cen = cen.merge(m2011.rename(columns={"census_district": "district_name"}),
                        on="district_name", how="left")
        cen["_dc"] = cen["canonical_district"].map(norm)
        out["_d"]  = out["district"].map(norm)
        m3 = match_districts(out["district"].dropna().unique(), alias, "district")
        out = out.merge(m3[["district","canonical_district"]].rename(
              columns={"canonical_district": "_cd2"}), on="district", how="left")
        out["_dc"] = out["_cd2"].map(norm)
        # exact block-name match within canonical district, then fuzzy within district
        import difflib
        lut = {}
        for dc, grp in cen.groupby("_dc"):
            lut[dc] = dict(zip(grp["_b"], grp.index))
        idx = []
        for _, r in out.iterrows():
            dc, b = r["_dc"], norm(str(r["block"]))
            pool = lut.get(dc, {})
            if b in pool:
                idx.append(pool[b]); continue
            hit = difflib.get_close_matches(b, list(pool.keys()), n=1, cutoff=0.72)
            idx.append(pool[hit[0]] if hit else -1)
        cenv = cen[keep].reindex(pd.Index(idx)).reset_index(drop=True)
        cenv.columns = ["census_" + c for c in cenv.columns]
        cenv[pd.Series(idx).values == -1] = np.nan
        out = pd.concat([out.reset_index(drop=True), cenv], axis=1)
        out = out.drop(columns=[c for c in ["_d","_dc","_cd2"] if c in out.columns])
        cr = 100.0 * out["census_literacy_rate_7plus"].notna().mean()
        src.append("Census 2011 PCA at CD-Block level, Karnataka (data.gov.in), fuzzy-matched to educational blocks")
        print("      census block match: %.1f%%" % cr)
    return out, src, {"level":level,"match_rate_pct":round(float(rate),1) if pd.notna(rate) else np.nan,
                      "n_units":len(unit_df),"sources":src}

MIN_MATCH_PCT   = 60.0   # below this a level is not administratively mappable, full stop
BIAS_ALPHA      = 0.05   # matched vs unmatched score difference must NOT be significant

def reliability_gate(unit_df, level, probe="ptr_govt", value="pct_mean"):
    """Decide whether external covariates may be ASSOCIATED with outcomes at this level.

    Two conditions, both reported:
      1. coverage: student-weighted match rate >= MIN_MATCH_PCT
      2. no selection bias: matched and unmatched units must not differ in outcome
    A level that fails is excluded from every external association (bright spots,
    structural model features, triage tractability). Internal analyses at that level
    are unaffected, because they need no external join.

    Karnataka reality check baked in: UDISE+ carries no Cluster field at all, so
    cluster can never pass and is refused before any test.
    """
    from scipy import stats as _st
    if level == "cluster":
        return False, {"level": level, "usable": False, "match_pct": 0.0,
                       "reason": "UDISE+ has no Cluster field; the education-cluster layer "
                                 "does not exist in any joinable external source"}
    if unit_df is None or probe not in unit_df.columns or value not in unit_df.columns:
        return False, {"level": level, "usable": False, "match_pct": np.nan,
                       "reason": "no external covariates joined at this level"}
    ok = unit_df[probe].notna()
    w = unit_df["n_students"] if "n_students" in unit_df.columns else pd.Series(1, index=unit_df.index)
    match_pct = 100.0 * w[ok].sum() / max(w.sum(), 1)
    p = np.nan
    if ok.sum() > 5 and (~ok).sum() > 5:
        p = float(_st.ttest_ind(unit_df.loc[ok, value].dropna(),
                                unit_df.loc[~ok, value].dropna(), equal_var=False)[1])
    unbiased = (not np.isfinite(p)) or p > BIAS_ALPHA
    usable = (match_pct >= MIN_MATCH_PCT) and unbiased
    reason = ("coverage %.1f%% and no detectable selection bias (p=%s)" % (match_pct, "%.3g" % p if np.isfinite(p) else "n/a")) if usable \
        else ("coverage %.1f%% below the %.0f%% floor" % (match_pct, MIN_MATCH_PCT) if match_pct < MIN_MATCH_PCT
              else "matched and unmatched units differ in outcome (p=%.3g): joining would bias results" % p)
    return usable, {"level": level, "usable": usable, "match_pct": round(match_pct, 1),
                    "bias_p": round(p, 4) if np.isfinite(p) else None, "reason": reason}

FEATURE_SETS = {
    "district": ["literacy_rate_7plus","male_female_literacy_gap_pp","sc_pct","st_pct",
                 "work_participation_rate","agri_labour_share_of_workers",
                 "women_10plus_schooling_pct","u5_stunted_pct","children_anaemic_pct",
                 "hh_improved_sanitation_pct","women_married_before18_pct",
                 "ptr_govt","pct_female_teachers_govt","pct_teachers_graduate_plus_govt",
                 "pct_sch_library_govt","pct_sch_computer_lab_govt","pct_private_schools",
                 "avg_govt_school_size","acad_inspections_per_school_govt",
                 "std3_5_atleast_subtraction_pct","pgid_outcomes_290","pgid_infra_51"],
    "block":    ["ptr_govt","pct_female_teachers_govt","pct_teachers_graduate_plus_govt",
                 "pct_sch_library_govt","pct_sch_playground_govt","pct_sch_computer_lab_govt",
                 "pct_sch_tapwater_functional_govt","pct_sch_preprimary_govt",
                 "girls_func_toilets_per_school_govt","good_classrooms_per_school_govt",
                 "acad_inspections_per_school_govt","mean_instruction_days_govt",
                 "avg_govt_school_size","pct_private_schools","pct_rural_schools",
                 "census_literacy_rate_7plus","census_male_female_literacy_gap_pp",
                 "census_sc_pct","census_st_pct","census_agri_labour_share_of_workers",
                 "census_marginal_worker_share"],
    "gp":       ["ptr_govt","pct_female_teachers_govt","pct_teachers_graduate_plus_govt",
                 "pct_sch_library_govt","pct_sch_playground_govt","pct_sch_computer_lab_govt",
                 "pct_sch_tapwater_functional_govt","pct_sch_preprimary_govt",
                 "girls_func_toilets_per_school_govt","good_classrooms_per_school_govt",
                 "acad_inspections_per_school_govt","mean_instruction_days_govt",
                 "avg_govt_school_size","pct_private_schools","n_schools_govt"],
}
TRACTABILITY = [("ptr_govt","high_is_tractable"),
                ("pct_sch_library_govt","low_is_tractable"),
                ("acad_inspections_per_school_govt","low_is_tractable"),
                ("pct_teachers_graduate_plus_govt","low_is_tractable"),
                ("mean_instruction_days_govt","low_is_tractable")]
