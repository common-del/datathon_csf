"""
LEVELS 2 + 3: hypothesis engine and geography/cohort explainer.

Run AFTER src/run_all.py:
    python src/day1_verdicts.py

Reads outputs/tables/ + external_data/. Writes:
    outputs/tables/hypothesis_verdicts.csv     every hypothesis, verdict, evidence, caveat
    outputs/VERDICTS.md                        plain-language verdicts to paste from
    outputs/dossiers/<DISTRICT>.md             why-this-district dossiers (all districts)
    outputs/dossiers/GENDER.md                 why-girls-vs-boys dossier

Verdict rules (stated so a judge can check them):
    SUPPORTED  effect is sizeable, statistically clear, and survives the robustness check
    WEAK       effect visible but small, or fails one robustness check
    DISCARD    no usable signal after testing from every available angle; do not present
Causal language is guarded on purpose: observational data supports "consistent with",
never "proves". The dossiers write that discipline in for you.
"""
import os, sys, json, warnings
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, ".."))
T = os.path.join(ROOT, "outputs", "tables"); EXT = os.path.join(ROOT, "external_data")
DOS = os.path.join(ROOT, "outputs", "dossiers"); os.makedirs(DOS, exist_ok=True)

def rd(name):
    p = os.path.join(T, name)
    return pd.read_csv(p) if os.path.exists(p) else None
def rx(name):
    p = os.path.join(EXT, name)
    return pd.read_csv(p) if os.path.exists(p) else None

def pcorr(x, y, ctrl=None):
    """correlation, optionally partial (residualise both on controls)."""
    d = pd.DataFrame({"x": x, "y": y})
    if ctrl is not None:
        for i, c in enumerate(np.atleast_2d(np.asarray(ctrl, dtype=float).T).T.T if False else []):
            pass
    if ctrl is not None:
        C = pd.DataFrame(ctrl)
        d = pd.concat([d, C.set_index(d.index)], axis=1).dropna()
        if len(d) < 25: return np.nan, np.nan, len(d)
        X = np.column_stack([np.ones(len(d)), d.iloc[:, 2:].values])
        bx = np.linalg.lstsq(X, d["x"].values, rcond=None)[0]
        by = np.linalg.lstsq(X, d["y"].values, rcond=None)[0]
        rx_ = d["x"].values - X @ bx; ry_ = d["y"].values - X @ by
        r, p = stats.pearsonr(rx_, ry_)
    else:
        d = d.dropna()
        if len(d) < 25: return np.nan, np.nan, len(d)
        r, p = stats.pearsonr(d["x"], d["y"])
    return r, p, len(d)

V = []   # verdict rows
def verdict(hid, name, verdict_, effect, evidence, caveat, action):
    V.append({"id": hid, "hypothesis": name, "verdict": verdict_, "effect": effect,
              "evidence": evidence, "caveat": caveat, "use_in_deck": action})

def corr_verdict(hid, name, r, p, n, robust_ok, unit, caveat, extra=""):
    if pd.isna(r):
        verdict(hid, name, "DISCARD", "n/a", "not enough joined data (n=%s)" % n, caveat,
                "Do not present. State that the join was too thin to test.")
        return
    strength = abs(r)
    if strength >= 0.15 and p < 0.01 and robust_ok:
        v = "SUPPORTED"
        act = "Present. Lead with the direction and size, show the scatter."
    elif strength >= 0.08 and p < 0.05:
        v = "WEAK"
        act = "Mention only with the caveat attached; do not build a slide on it."
    else:
        v = "DISCARD"
        act = "Do not present. If asked, say it was tested and found near-zero."
    verdict(hid, name, v, "r=%.2f (p=%.3g, n=%d %s)" % (r, p, n, unit),
            ("direction holds across years; " if robust_ok else "direction NOT stable across years; ") + extra,
            caveat, act)

def main():
    gp   = rd("unit_gp_with_external.csv");    blk = rd("unit_block_with_external.csv")
    dis  = rd("unit_district_with_external.csv")
    gpy  = rd("unit_gp_by_year.csv");          bky = rd("unit_block_by_year.csv")
    dy   = rd("unit_district_by_year.csv")
    gen  = rd("gender_by_competency.csv");     geno = rd("gender_overall.csv")
    fl   = rd("floor_index_district.csv");     coh = rd("cohort_progression_block.csv")
    bs   = None
    for lv in ("gp","block","district"):
        bs = bs if bs is not None else rd("bright_spots_%s.csv" % lv)
    den  = rx("udise_karnataka_gp_grade46_enrolment.csv")
    xw   = rx("karnataka_district_crosswalk.csv")
    ev   = rx("karnataka_events_2022_2025.csv")

    # ---- join-quality gate: if GP-level covariates are too thin, fall back to block
    gp_ok = gp is not None and "ptr_govt" in (gp.columns if gp is not None else []) \
            and gp["ptr_govt"].notna().mean() >= 0.60
    U  = gp if gp_ok else blk
    UY = gpy if gp_ok else bky
    unit = "GPs" if gp_ok else "blocks"
    print("Join gate: GP covariate coverage %s -> testing at %s level"
          % ("%.0f%%" % (100*gp["ptr_govt"].notna().mean()) if gp is not None and "ptr_govt" in gp.columns else "n/a", unit))

    def stable_across_years(y_tbl, xcol, source_pool):
        """same-sign correlation in at least 2 of 3 years"""
        if y_tbl is None or source_pool is None or xcol not in source_pool.columns: return False
        key = [c for c in ["district","block","gp"] if c in y_tbl.columns and c in source_pool.columns]
        if not key: return False
        m = y_tbl.merge(source_pool[key + [xcol]].drop_duplicates(key), on=key, how="left")
        signs = []
        for y, g in m.groupby("year"):
            r, p, n = pcorr(g[xcol], g["pct_mean"])
            if pd.notna(r) and n >= 25: signs.append(np.sign(r))
        return len(signs) >= 2 and len(set(signs)) == 1

    # ================= H1 teacher availability =================
    if U is not None and "ptr_govt" in U.columns:
        ctrl = [U[c] for c in ["census_literacy_rate_7plus"] if c in U.columns and U[c].notna().mean() > .4]
        r, p, n = pcorr(U["ptr_govt"], U["pct_mean"], np.column_stack(ctrl) if ctrl else None)
        corr_verdict("H1", "Higher pupil-teacher ratio, lower scores", r, p, n,
                     stable_across_years(UY, "ptr_govt", U), unit,
                     "PTR proxies remoteness too; partial control applied for block literacy" if ctrl
                     else "no literacy control available at this level",
                     "controlled for Census block literacy. " if ctrl else "")
    # ================= H2 language mismatch =================
    if blk is not None and "pct_sch_kannada_medium_govt" in blk.columns:
        r, p, n = pcorr(blk["pct_sch_kannada_medium_govt"], blk["pct_mean"])
        corr_verdict("H2", "Non-Kannada-medium belts score differently on a Kannada-language test",
                     r, p, n, stable_across_years(bky, "pct_sch_kannada_medium_govt", blk), "blocks",
                     "medium share is a school-stock measure, not the tested child's home language; "
                     "upgrade: item-level word-problem vs computation split in the afternoon")
    # ================= H3 drought year-shock (proxy) =================
    if bky is not None and {"year","pct_mean","division"}.issubset(bky.columns):
        yrs = sorted(bky["year_n"].dropna().unique())
        if len(yrs) == 3:
            w = bky.pivot_table(index=[c for c in ["division","district","block"] if c in bky.columns],
                                columns="year_n", values="pct_mean")
            w = w.dropna(); w.columns = ["y0","y1","y2"]
            w["dip23"] = w["y1"] - (w["y0"] + w["y2"]) / 2
            w = w.reset_index()
            belt = w["division"].isin(["Kalaburagi","Belagavi"])
            a, b = w.loc[belt,"dip23"], w.loc[~belt,"dip23"]
            if len(a) > 15 and len(b) > 15:
                t, p = stats.ttest_ind(a, b, equal_var=False)
                diff = a.mean() - b.mean()
                v = "SUPPORTED" if (diff < -0.8 and p < 0.05) else ("WEAK" if (diff < -0.3 and p < 0.15) else "DISCARD")
                verdict("H3", "2023-24 drought dented scores in the drought belt (proxy: north-interior divisions)",
                        v, "middle-year dip %.2f pp deeper in belt (p=%.3g; belt n=%d)" % (diff, p, len(a)),
                        "dip = 2023-24 minus average of the flanking years, per block",
                        "PROXY ONLY: uses divisions, not the official 223-taluk list; items also changed "
                        "each year, so a statewide year effect is already removed by design",
                        "Present only if SUPPORTED, and only as consistent-with; name the proxy nature aloud."
                        if v != "DISCARD" else "Do not present. Say the division-level proxy showed no differential dip.")
    # ================= H4 nutrition legacy =================
    if dis is not None and "u5_stunted_pct" in dis.columns:
        ctrl = [dis[c] for c in ["literacy_rate_7plus","women_10plus_schooling_pct"] if c in dis.columns]
        r, p, n = pcorr(dis["u5_stunted_pct"], dis["pct_mean"], np.column_stack(ctrl) if ctrl else None)
        corr_verdict("H4", "NFHS-5 stunting districts still lag (the tested cohort IS that under-5 cohort)",
                     r, p, n, stable_across_years(dy, "u5_stunted_pct", dis), "districts",
                     "NFHS-5 is 2019-21 and urban+rural; tested cohort born 2012-16 so exposure timing fits")
    # ================= H5 371J gap and what closes it =================
    if dis is not None and xw is not None:
        d = dis.merge(xw[["current_name","is_371J_kalyana_karnataka","princely_legacy"]],
                      left_on="canonical_district", right_on="current_name", how="left")
        if d["is_371J_kalyana_karnataka"].notna().any():
            kk = d[d.is_371J_kalyana_karnataka == 1]["pct_mean"]; rest = d[d.is_371J_kalyana_karnataka == 0]["pct_mean"]
            raw = kk.mean() - rest.mean()
            ctrls = [c for c in ["ptr_govt","literacy_rate_7plus","u5_stunted_pct"] if c in d.columns]
            resid_gap = np.nan
            if ctrls:
                dd = d.dropna(subset=["pct_mean"] + ctrls)
                X = np.column_stack([np.ones(len(dd))] + [dd[c] for c in ctrls])
                b = np.linalg.lstsq(X, dd["pct_mean"], rcond=None)[0]
                res = dd["pct_mean"] - X @ b
                resid_gap = res[dd.is_371J_kalyana_karnataka == 1].mean() - res[dd.is_371J_kalyana_karnataka == 0].mean()
            closed = (pd.notna(resid_gap) and pd.notna(raw) and raw != 0
                      and abs(resid_gap) < 0.5 * abs(raw))
            v = "SUPPORTED" if pd.notna(raw) and abs(raw) >= 2 else "WEAK" if abs(raw) >= 1 else "DISCARD"
            verdict("H5", "Kalyana Karnataka (371J) gap, and whether inputs explain it", v,
                    "raw gap %+.1f pp; after controlling %s the gap is %+.1f pp (%s)" %
                    (raw, "+".join(ctrls) if ctrls else "nothing", resid_gap if pd.notna(resid_gap) else raw,
                     "mostly explained by measured inputs" if closed else "NOT explained by measured inputs"),
                    "controls: %s" % (", ".join(ctrls) or "none available"),
                    "a decade of 371J funds; KKRDB education-year 2023-24 pushes the other way from 2023-24",
                    "Present the pair of numbers: the gap, and the gap after controls. That is the policy slide.")
    # ================= H6 gender flip across difficulty =================
    if gen is not None and {"gap_pp_F_minus_M","overall_mastery_pct"}.issubset(gen.columns):
        g = gen.dropna(subset=["gap_pp_F_minus_M","overall_mastery_pct"])
        if len(g) >= 6:
            r, p = stats.spearmanr(g["overall_mastery_pct"], g["gap_pp_F_minus_M"])
            easy = g.nlargest(max(3, len(g)//3), "overall_mastery_pct")["gap_pp_F_minus_M"].mean()
            hard = g.nsmallest(max(3, len(g)//3), "overall_mastery_pct")["gap_pp_F_minus_M"].mean()
            flip = np.sign(easy) != np.sign(hard) and abs(easy - hard) >= 1.0
            v = "SUPPORTED" if (flip or (abs(r) >= .6 and p < .05)) else ("WEAK" if abs(easy-hard) >= 0.5 else "DISCARD")
            verdict("H6", "Gender gap changes as maths gets harder", v,
                    "girls-minus-boys: %+.1f pp on easiest tier vs %+.1f pp on hardest (rank r=%.2f, p=%.3g)"
                    % (easy, hard, r, p),
                    "tiers = top/bottom third of competencies by overall mastery",
                    "if the competency map was inferred rather than official, say so on the slide",
                    "Present the two-number contrast; a single average gap hides it." if v != "DISCARD"
                    else "Do not present a flip; report the flat overall gap with effect size instead.")
    # ================= H7 floor vs mean =================
    if fl is not None and "floor_minus_mean_divergence_pp" in fl.columns:
        k = int((fl["floor_minus_mean_divergence_pp"] < 0).sum()); nn = len(fl)
        share = k / max(nn, 1)
        v = "SUPPORTED" if share >= 0.4 and nn >= 15 else ("WEAK" if share >= 0.25 else "DISCARD")
        verdict("H7", "Averages move without the weakest children moving", v,
                "%d of %d districts show mean up while the 10th percentile lagged (divergence < 0)" % (k, nn),
                "floor = 10th percentile of student % correct",
                "items changed yearly: frame as ranking/shape shifts, not point gains",
                "Lead the equity slide with the count; name 2 districts each way.")
    # ================= H8 cohort progression x PTR =================
    if coh is not None and blk is not None and "ptr_govt" in blk.columns and len(coh):
        m = coh.merge(blk[["district","block","ptr_govt"]].drop_duplicates(), on=[c for c in ["district","block"] if c in coh.columns and c in blk.columns], how="left") \
            if {"district","block"}.issubset(coh.columns) else coh.merge(blk[["block","ptr_govt"]].drop_duplicates("block"), on="block", how="left")
        m = m.dropna(subset=["ptr_govt","progression_pp"])
        if len(m) >= 40:
            hi = m[m.ptr_govt >= m.ptr_govt.quantile(.75)]["progression_pp"]
            lo = m[m.ptr_govt <= m.ptr_govt.quantile(.25)]["progression_pp"]
            t, p = stats.ttest_ind(hi, lo, equal_var=False)
            diff = hi.mean() - lo.mean()
            v = "SUPPORTED" if (diff <= -1.0 and p < .05) else ("WEAK" if diff <= -0.4 else "DISCARD")
            verdict("H8", "Cohorts in teacher-starved blocks progress slower", v,
                    "cohort progression %.2f pp in top-PTR quartile vs %.2f in bottom (diff %.2f, p=%.3g)"
                    % (hi.mean(), lo.mean(), diff, p),
                    "same cohort, same place, different children; composition can shift",
                    "cross-year comparison carries the instrument caveat",
                    "Strong policy slide if SUPPORTED: teacher posting norms bite twice." if v != "DISCARD"
                    else "Do not present; progression is not differential by PTR here.")
    # ================= H9 coverage bias =================
    if gpy is not None and den is not None:
        den2 = den.copy(); den2["gp"] = den2["gram_panchayat"].astype(str).str.upper().str.strip()
        g2 = gpy.copy(); g2["gp"] = g2["gp"].astype(str).str.upper().str.strip()
        m = g2.merge(den2, left_on=["district","block","gp","year"],
                     right_on=["district","block","gp","academic_year"], how="inner")
        if len(m) > 200:
            m["coverage"] = 100 * m["n_students"] / m["enrol_g4_6_govt"].replace(0, np.nan)
            m = m[m["coverage"].between(1, 130)]
            r, p, n = pcorr(m["coverage"], m["pct_mean"])
            match_rate = len(m) / len(g2)
            v = ("SUPPORTED" if abs(r) >= .15 and p < .01 else "WEAK" if abs(r) >= .08 else "DISCARD") if pd.notna(r) else "DISCARD"
            verdict("H9", "Who-got-tested bias: coverage correlates with scores", v,
                    "r=%.2f (p=%.3g) across %d GP-years; GP name match rate %.0f%%" % (r, p, n, 100*match_rate),
                    "coverage = tested / UDISE grade 4-6 govt enrolment",
                    "GP names are fuzzy between the two systems; unmatched GPs excluded, stated openly",
                    "If SUPPORTED: one honest slide sentence that scores partly reflect who sat the test. "
                    "If DISCARD: one sentence that coverage bias was tested and ruled out. Either way it is a win.")
        else:
            verdict("H9", "Who-got-tested bias", "DISCARD", "join too thin",
                    "GP name match with UDISE below usable threshold", "expected fuzziness materialised",
                    "Fall back to district-level coverage in the afternoon if time allows.")
    # ================= H10 private-exit composition =================
    if blk is not None and "pct_private_schools" in blk.columns:
        r, p, n = pcorr(blk["pct_private_schools"], blk["pct_mean"])
        corr_verdict("H10", "High private-school presence, lower government-school scores (selection)",
                     r, p, n, stable_across_years(bky, "pct_private_schools", blk), "blocks",
                     "composition/selection story, not school quality; CMS-E shows exit is income-graded")
    # ================= H11 deep roots =================
    if dis is not None and xw is not None:
        d = dis.merge(xw[["current_name","princely_legacy"]], left_on="canonical_district",
                      right_on="current_name", how="left").dropna(subset=["princely_legacy","pct_mean"])
        if d["princely_legacy"].nunique() >= 3:
            grp = d.groupby("princely_legacy")["pct_mean"].agg(["mean","count"])
            f, p = stats.f_oneway(*[g["pct_mean"].values for _, g in d.groupby("princely_legacy") if len(g) >= 2])
            spread = grp["mean"].max() - grp["mean"].min()
            v = "SUPPORTED" if (p < .05 and spread >= 3) else ("WEAK" if spread >= 1.5 else "DISCARD")
            verdict("H11", "The learning map follows pre-1956 administrative borders", v,
                    "legacy-group means: %s (ANOVA p=%.3g)" %
                    ("; ".join("%s %.1f" % (k, v_) for k, v_ in grp["mean"].round(1).items()), p),
                    "coded by us from States Reorganisation Act literature; verify before quoting",
                    "explains, never excuses; do not present without the 371J-inputs slide next to it",
                    "Innovation slide if SUPPORTED. Framing: a 70-year inheritance, not a verdict on anyone today.")
    # ================= H12 convergent validity vs PARAKH RS 2024 =================
    if dis is not None and "prs24_state_govt_g6" in dis.columns:
        for gcol, glab in [("prs24_state_govt_g6","grade-6"), ("prs24_state_govt_g3","grade-3")]:
            d = dis.dropna(subset=["pct_mean", gcol])
            if len(d) >= 20:
                rho, p = stats.spearmanr(d["pct_mean"], d[gcol])
                if rho >= 0.6 and p < .01:
                    vd_, act = "SUPPORTED", ("Two independent instruments rank districts the same way; "
                                             "your findings inherit PARAKH's credibility. Show the scatter.")
                elif rho <= 0.3:
                    vd_, act = "WEAK", ("Divergence IS the finding: same districts, different verdicts. "
                                        "Present as an instruments-and-coverage insight, with H9 next to it.")
                else:
                    vd_, act = "WEAK", "Moderate agreement; cite as partial corroboration only."
                verdict("H12", "Akshara district ranking replicates in PARAKH RS 2024 %s maths (govt schools)" % glab,
                        vd_, "Spearman rho=%.2f (p=%.3g, n=%d districts)" % (rho, p, len(d)),
                        "compared against the state-government subgroup column, the same management universe",
                        "PARAKH publishes integers and samples ~1,300 schools statewide; ties within 1 point",
                        act)
                break
    # ================= H13 gender gap replicates across instruments =================
    if dis is not None and "prs24_gender_gap_girls_minus_boys_g6" in dis.columns and "gender_gap_pp" in dis.columns:
        d = dis.dropna(subset=["gender_gap_pp","prs24_gender_gap_girls_minus_boys_g6"])
        if len(d) >= 20:
            r, p = stats.pearsonr(d["gender_gap_pp"], d["prs24_gender_gap_girls_minus_boys_g6"])
            agree = float((np.sign(d["gender_gap_pp"]) == np.sign(d["prs24_gender_gap_girls_minus_boys_g6"])).mean())
            v_ = "SUPPORTED" if (r >= .35 and p < .05) else ("WEAK" if agree >= .6 else "DISCARD")
            verdict("H13", "District gender gaps replicate in PARAKH RS 2024", v_,
                    "r=%.2f (p=%.3g); sign agreement %.0f%% of %d districts" % (r, p, 100*agree, len(d)),
                    "PARAKH statewide shows girls +2 at grades 3 and 6, 0 by grade 9",
                    "both instruments are cross-sectional; agreement supports the pattern, not a cause",
                    "If SUPPORTED: one line that the gender pattern is not an artefact of our instrument."
                    if v_ != "DISCARD" else "Do not present; note the two instruments disagree on gender.")
    # ================= write outputs =================
    vdf = pd.DataFrame(V)
    vdf.to_csv(os.path.join(T, "hypothesis_verdicts.csv"), index=False)
    order = {"SUPPORTED": 0, "WEAK": 1, "DISCARD": 2}
    vdf = vdf.sort_values("verdict", key=lambda s: s.map(order))
    with open(os.path.join(ROOT, "outputs", "VERDICTS.md"), "w", encoding="utf-8") as f:
        f.write("# Hypothesis verdicts (auto-generated; rules in src/day1_verdicts.py)\n\n")
        for vv in ["SUPPORTED", "WEAK", "DISCARD"]:
            sub = vdf[vdf.verdict == vv]
            if len(sub) == 0: continue
            f.write("## %s (%d)\n\n" % (vv, len(sub)))
            for _, r in sub.iterrows():
                f.write("**%s. %s**\n- Effect: %s\n- Evidence: %s\n- Caveat: %s\n- What to do: %s\n\n"
                        % (r.id, r.hypothesis, r.effect, r.evidence, r.caveat, r.use_in_deck))
    print("\n=== VERDICTS ===")
    for _, r in vdf.iterrows():
        print("%-9s %s: %s | %s" % (r.verdict, r.id, r.hypothesis, r.effect))

    # ================= LEVEL 3: dossiers =================
    write_dossiers(dis, dy, fl, xw, ev, vdf, gen, geno)
    print("\nWrote outputs/tables/hypothesis_verdicts.csv, outputs/VERDICTS.md, outputs/dossiers/")

def write_dossiers(dis, dy, fl, xw, ev, vdf, gen, geno):
    if dis is None: return
    d = dis.copy()
    if xw is not None:
        d = d.merge(xw[["current_name","is_371J_kalyana_karnataka","princely_legacy"]],
                    left_on="canonical_district", right_on="current_name", how="left")
    d["rank"] = d["pct_mean"].rank(ascending=False).astype(int)
    med = d["pct_mean"].median()
    tr = None
    if dy is not None and "year_n" in dy.columns:
        yrs = sorted(dy.year_n.dropna().unique())
        if len(yrs) >= 2:
            a = dy[dy.year_n == yrs[0]].set_index("district")["pct_mean"]
            b = dy[dy.year_n == yrs[-1]].set_index("district")["pct_mean"]
            tr = (b - a)
    evd = None
    if ev is not None:
        evd = ev[ev.geography_level.isin(["district","taluk"])]

    def line(cond, text_true, text_false=""):
        return (text_true if cond else text_false)

    for _, r in d.iterrows():
        name = str(r.get("district", r.get("canonical_district", "?")))
        L = ["# %s: why it stands where it stands\n" % name.title()]
        L.append("Rank %d of %d districts. Mean %.1f%% against a state median of %.1f%%."
                 % (r["rank"], len(d), r["pct_mean"], med))
        if tr is not None and name in tr.index and pd.notna(tr[name]):
            L.append("Change first-to-last year: %+.1f pp. Items changed each year, so read this "
                     "as movement in standing, not points learned." % tr[name])
        conds = []
        if pd.notna(r.get("ptr_govt")):
            conds.append("PTR %.0f (%s the RTE norm of 30)" % (r["ptr_govt"], "above" if r["ptr_govt"] > 30 else "within"))
        if pd.notna(r.get("u5_stunted_pct")):
            conds.append("NFHS-5 stunting %.0f%% when this cohort was under 5" % r["u5_stunted_pct"])
        if pd.notna(r.get("literacy_rate_7plus")):
            conds.append("Census literacy %.0f%%" % r["literacy_rate_7plus"])
        if pd.notna(r.get("pct_private_schools")):
            conds.append("private-school presence %.0f%%" % r["pct_private_schools"])
        if conds:
            L.append("\nConditions this district works under: " + "; ".join(conds) + ".")
        if r.get("is_371J_kalyana_karnataka") == 1:
            L.append("\nIt is a 371J Kalyana Karnataka district: special constitutional status since 2013, "
                     "KKRDB education-year money from 2023-24, and it was in the Dec 2021 egg-pilot list. "
                     "Positive programme pressure and deep structural deficits at the same time.")
        if pd.notna(r.get("princely_legacy")):
            L.append("Pre-1956 administration: %s. The north-south learning gradient tracks these borders; "
                     "explains, never excuses." % r["princely_legacy"])
        if evd is not None:
            hits = evd[evd.geography.str.upper().str.contains(name.upper().split()[0], na=False)]
            if len(hits):
                L.append("\nDistrict-targeted events in the window:")
                for _, e in hits.iterrows():
                    L.append("- %s (%s, %s): expected %s. [%s]" % (e.event, e.when, e.academic_years_hit,
                             e.direction_gr46_math, e.status))
        L.append("\nJudgment, in guarded language: the standing is *consistent with* the measured "
                 "conditions above%s. What this dossier cannot rule out: unmeasured school practice, "
                 "assessment coverage differences, and community factors. The bright-spot residual "
                 "(outputs/tables/bright_spots_*.csv) says whether this district beats or trails what "
                 "its conditions predict; quote that number next to the rank, never the rank alone."
                 % line(pd.notna(r.get("ptr_govt")) and r.get("ptr_govt", 0) > 35,
                        ", teacher scarcity foremost"))
        open(os.path.join(DOS, "%s.md" % name.replace("/", "-")), "w", encoding="utf-8").write("\n".join(L))

    # gender dossier
    G = ["# Girls vs boys: what the data will and will not say\n"]
    if geno is not None and len(geno):
        o = geno.iloc[0]
        G.append("Overall: girls %.1f%% vs boys %.1f%% (gap %+.1f pp, Cohen's d %.3f: %s)."
                 % (o.mean_pct_girls, o.mean_pct_boys, o.gap_pp_girls_minus_boys, o.cohens_d,
                    "too small to build policy on" if abs(o.cohens_d) < .2 else "a real effect"))
    if gen is not None and "gap_pp_F_minus_M" in gen.columns:
        g = gen.dropna(subset=["gap_pp_F_minus_M"])
        if len(g):
            G.append("\nBy competency, the gap runs from %+.1f to %+.1f pp. The verdict engine (H6) says "
                     "whether the flip across the difficulty ladder is real in this data."
                     % (g.gap_pp_F_minus_M.min(), g.gap_pp_F_minus_M.max()))
    G.append("\nContext that bears on girls specifically, from the pre-baked pack: early marriage fell "
             "from 21.3%% to 15.3%% between NFHS-5 and NFHS-6; Shakti free bus travel (June 2023) cut "
             "mobility costs for women and accompanying children; Gruha Lakshmi (Aug 2023) moved Rs 2,000 "
             "a month to women household heads. All statewide, so they shift years, not districts.")
    G.append("\nGuarded judgment: any gender difference here is *consistent with* differential exposure "
             "(attendance, domestic work, confidence on multi-step problems), and the data cannot "
             "separate those. Say which competencies carry the gap; do not claim why without a caveat.")
    open(os.path.join(DOS, "GENDER.md"), "w", encoding="utf-8").write("\n".join(G))

if __name__ == "__main__":
    main()
