"""
SINGLE ENTRY POINT. Reproduces everything in outputs/ from data/ .

    python src/run_all.py

Offline. Relative paths. Fixed seed. Designed so that a failure in one analysis
never stops the rest: each step is wrapped, and anything that breaks is reported
at the end in outputs/RUN_LOG.txt instead of killing the run.
"""
import os, sys, time, json, traceback, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np, pandas as pd
import config, loader, schema, qa, metrics, analyses, external, figures, dashboard, model, coverage, choropleth

np.random.seed(config.SEED)
T0, LOG, FAILED, CLAIMS = time.time(), [], [], []

def say(m=""):
    print(m); LOG.append(m)

def step(name, fn, *a, **k):
    t = time.time()
    say("\n[%5.1fs] %s" % (time.time() - T0, name))
    try:
        r = fn(*a, **k)
        say("          done in %.1fs" % (time.time() - t))
        return r
    except Exception as e:
        FAILED.append(name)
        say("          !! FAILED: %s: %s" % (type(e).__name__, e))
        for ln in traceback.format_exc().splitlines()[-6:]:
            say("             " + ln)
        return None

def write(df, name, note=""):
    if df is None or (hasattr(df, "__len__") and len(df) == 0):
        say("          (nothing to write for %s)" % name); return None
    os.makedirs(config.TABLES, exist_ok=True)
    p = os.path.join(config.TABLES, name)
    try:
        df.to_csv(p, index=False)
    except PermissionError:
        # Classic Day-1 trap: the file is open in Excel, so Windows locks it.
        alt = p.replace(".csv", "_NEW.csv")
        try:
            df.to_csv(alt, index=False)
            say("          !! %s is LOCKED (open in Excel?). Wrote %s instead. "
                "Close the file and re-run to restore the normal name."
                % (name, os.path.basename(alt)))
            return alt
        except Exception as e:
            say("          !! could not write %s: %s" % (name, e)); return None
    say("          -> tables/%s  (%d rows)%s" % (name, len(df), ("  " + note) if note else ""))
    return p

def claim(text, value, how, output="", method="programmatic", unit="", detail=None):
    CLAIMS.append({"claim_id": "claim-%d" % (len(CLAIMS) + 1),
                   "description": text, "claimed_value": str(value), "unit": unit,
                   "supporting_output": output or (how.split(",")[0].replace("outputs/", "outputs/")
                                                   if "outputs/" in how else ""),
                   "verification_method": method,
                   "verification_detail": detail or {"how_to_check": how}})

def main():
    for d in (config.OUTPUTS, config.FIGURES, config.TABLES):
        os.makedirs(d, exist_ok=True)
    # fresh slate: stale files from a previous run must never mask a failed step
    for d in (config.TABLES, config.FIGURES, os.path.join(config.OUTPUTS, "dossiers")):
        if os.path.isdir(d):
            for f in os.listdir(d):
                try: os.remove(os.path.join(d, f))
                except Exception: pass
    for f in ("dashboard.html", "VERDICTS.md"):
        try: os.remove(os.path.join(config.OUTPUTS, f))
        except Exception: pass
    say("=" * 78)
    say("DATATHON 2026 PIPELINE   seed=%d" % config.SEED)
    say("=" * 78)

    # ---------------------------------------------------------------- load
    say("\n[  0.0s] LOAD PRIMARY DATA")
    df, meta = loader.load()
    items, n_items = meta["items"], meta["n_items"]
    say("   usable rows: %d | items: %d | mean %% correct: %.2f"
        % (len(df), n_items, df["pct"].mean()))
    claim("Analysis dataset size", "%d student records, %d items" % (len(df), n_items),
          "outputs/tables/qa_summary.csv row 'rows'")

    ccols = [c for c in df.columns if c.startswith("C_")]
    if ccols:
        say("   per-file competency columns present (%d) - official mapping, no inference needed" % len(ccols))
        cmap, real_map = None, True
    else:
        cmap, real_map = step("COMPETENCY MAP", loader.load_competency_map, items) or (None, False)
        if cmap is None:
            cmap = step("INFER COMPETENCY GROUPS", loader.infer_competency_map, df, items)
    if cmap is not None:
        write(cmap, "competency_map_used.csv",
              "REAL mapping" if real_map else "INFERRED - state this as a limitation")

    # ---------------------------------------------------------------- QA
    res = step("DATA QUALITY AND ANOMALY CHECKS", qa.run, df, meta)
    qa_sum, qa_flags = res if res else (None, None)
    write(qa_sum, "qa_summary.csv"); write(qa_flags, "qa_flags.csv")
    if qa_flags is not None and len(qa_flags):
        say("          %d flags raised (%d HIGH). Read tables/qa_flags.csv before writing the report."
            % (len(qa_flags), int((qa_flags.severity == "HIGH").sum())))

    # ------------------------------------------------------- items/competency
    ia = step("ITEM ANALYSIS (difficulty, discrimination, gender DIF)",
              analyses.item_analysis, df, items, cmap)
    write(ia, "item_analysis.csv")
    if ia is not None and len(ia):
        claim("Hardest item", "%s at %.1f%% correct" % (ia.iloc[0]["item"], ia.iloc[0]["pct_correct"]),
              "outputs/tables/item_analysis.csv, first row when sorted by pct_correct")

    cp = step("COMPETENCY PROFILE", analyses.competency_profile, df, cmap, items,
              ("year", "grade", "gender"))
    write(cp, "competency_profile.csv")

    bn_pair = step("COMPETENCY BOTTLENECK (original metric)",
                   metrics.competency_bottleneck, df, cmap, items)
    bn, pairs = bn_pair if bn_pair else (None, None)
    write(bn, "competency_bottleneck.csv"); write(pairs, "competency_prerequisite_pairs.csv")
    if bn is not None and len(bn):
        t = bn.dropna(subset=["bottleneck_score"]).iloc[0]
        claim("Binding competency bottleneck",
              "%s: %.1f%% mastery, gate lift %.1f pp" % (t.competency_label,
              t.mastery_rate_pct, t.gate_lift_pp),
              "outputs/tables/competency_bottleneck.csv, top row by bottleneck_score")

    # ------------------------------------------------------------- variance
    vres = step("LEARNING VARIANCE SIGNATURE (original metric)",
                metrics.variance_decomposition, df)
    vd, ceiling = vres if vres else (None, None)
    write(vd, "variance_signature.csv"); write(ceiling, "targeting_efficiency_ceiling.csv")
    if vd is not None and len(vd):
        w = vd.iloc[-1]
        claim("Share of learning variation that is within Gram Panchayat",
              "%.1f%% of total variation (df-adjusted %.1f%%)"
              % (w["share_of_total_variation_pct"], w["share_adjusted_pct"]),
              "outputs/tables/variance_signature.csv, last row")

    # ------------------------------------------------------------- geography
    units, per_years = {}, {}
    for lvl in config.GEO_LEVELS:
        r = step("AGGREGATE TO %s" % lvl.upper(), analyses.unit_summary, df, lvl, items)
        if r:
            u, py = r
            units[lvl], per_years[lvl] = u, py
            write(u, "unit_%s.csv" % lvl)
            if py is not None and len(py):
                write(py, "unit_%s_by_year.csv" % lvl)
            tr = step("TREND AT %s" % lvl.upper(), analyses.trends, py, lvl)
            if tr is not None and len(tr):
                if not config.ITEMS_COMPARABLE_ACROSS_YEARS:
                    tr["instrument_caveat"] = config.CROSS_YEAR_CAVEAT
                write(tr, "trend_%s.csv" % lvl)
                if lvl == "district":
                    best = tr.iloc[-1]; worst = tr.iloc[0]
                    claim("Fastest improving district",
                          "%s %+.2f pp" % (best[lvl], best["change_pp"]),
                          "outputs/tables/trend_district.csv, max change_pp")
                    claim("Most declining district",
                          "%s %+.2f pp" % (worst[lvl], worst["change_pp"]),
                          "outputs/tables/trend_district.csv, min change_pp")

    fl = step("FLOOR INDEX AND FLOOR-MEAN DIVERGENCE (original metric)",
              metrics.floor_index, df, "district")
    if fl is not None and len(fl) and "floor_change_pp" in getattr(fl, "columns", []) \
       and not config.ITEMS_COMPARABLE_ACROSS_YEARS:
        fl["instrument_caveat"] = config.CROSS_YEAR_CAVEAT
    write(fl, "floor_index_district.csv")

    # ---------------------------------------------------------------- gender
    gg = step("GENDER GAP ANALYSIS", analyses.gender_gaps, df, items, cmap) or {}
    for k, v in (gg or {}).items():
        write(v, "gender_%s.csv" % k)
    if "overall" in gg:
        o = gg["overall"].iloc[0]
        claim("Overall gender gap",
              "girls %.2f%% vs boys %.2f%% (%+.2f pp, p=%s, d=%.3f)"
              % (o.mean_pct_girls, o.mean_pct_boys, o.gap_pp_girls_minus_boys,
                 o.p_value, o.cohens_d),
              "outputs/tables/gender_overall.csv")

    # ------------------------------------------------------------ progression
    pres = step("SYNTHETIC COHORT PROGRESSION", analyses.progression, df, "block")
    coh, coh_sum = pres if pres else (None, None)
    if coh is not None and len(coh) and not config.ITEMS_COMPARABLE_ACROSS_YEARS:
        coh["instrument_caveat"] = config.CROSS_YEAR_CAVEAT
        say("          NOTE: " + config.CROSS_YEAR_CAVEAT)
    write(coh, "cohort_progression_block.csv"); write(coh_sum, "cohort_progression_summary.csv")

    # -------------------------------------------------------- external joins
    say("\n[%5.1fs] EXTERNAL DATASET JOINS" % (time.time() - T0))
    alias = step("BUILD DISTRICT ALIAS TABLE", external.build_alias_table)
    joined, join_reports, all_sources = {}, [], []
    if alias is not None:
        for lvl in ["district", "block", "gp"]:
            if lvl not in units or units[lvl] is None or units[lvl].empty:
                continue
            r = step("JOIN EXTERNAL DATA AT %s LEVEL" % lvl.upper(),
                     external.unit_join, units[lvl], lvl, alias)
            if r:
                u2, src, rep = r
                joined[lvl] = u2
                if rep: join_reports.append(rep)
                all_sources += src
                write(u2, "unit_%s_with_external.csv" % lvl)
    if join_reports:
        write(pd.DataFrame(join_reports), "external_join_report.csv")
        for rep in join_reports:
            claim("External join coverage at %s level" % rep["level"],
                  "%.1f%% of %d units matched" % (rep["match_rate_pct"], rep["n_units"]),
                  "outputs/tables/external_join_report.csv")

    # ---------------------------------------------- external reliability gate
    say("\n[%5.1fs] EXTERNAL RELIABILITY GATE" % (time.time() - T0))
    gate, gate_rows = {}, []
    for lvl in config.GEO_LEVELS:
        u = joined.get(lvl)
        okg, info = external.reliability_gate(u, lvl)
        gate[lvl] = okg; gate_rows.append(info)
        say("   %-9s %s  (%s)" % (lvl, "USABLE" if okg else "REFUSED", info["reason"]))
    write(pd.DataFrame(gate_rows), "external_reliability_gate.csv")
    usable_levels = [l for l in config.GEO_LEVELS if gate.get(l)]
    say("   external associations restricted to: %s" % (", ".join(usable_levels) or "NONE"))
    claim("Levels at which external covariates may be associated with outcomes",
          ", ".join(usable_levels) or "none",
          "outputs/tables/external_reliability_gate.csv",
          output="outputs/tables/external_reliability_gate.csv", method="programmatic",
          detail={"rule": "student-weighted match >= %.0f%% AND no significant matched-vs-unmatched "
                          "outcome difference (alpha %.2f); cluster refused because UDISE+ has no "
                          "cluster field" % (external.MIN_MATCH_PCT, external.BIAS_ALPHA)})

    # ---------------------------------------------- assessment coverage
    if alias is not None:
        cres = step("ASSESSMENT COVERAGE vs UDISE ENROLMENT", coverage.build, df, alias)
        if cres:
            cov_long, cov_wide, cov_summ = cres
            write(cov_long, "coverage_district_grade_year.csv")
            write(cov_wide, "coverage_matrix_rural_stategovt.csv")
            write(cov_summ, "coverage_summary.csv")
            step("COVERAGE CHOROPLETH", choropleth.build, cov_long)
            s_ = cov_summ[cov_summ.basis == "rural"]
            if len(s_):
                s_ = s_.iloc[0]
                say("          state coverage %.1f%% of State Government enrolment "
                    "(%d of %d district-years under 50%%)"
                    % (s_.state_coverage_pct, s_.district_years_under_50pct, s_.n_district_years))
                claim("Assessment coverage against UDISE RURAL State Government enrolment (the contest universe)",
                      "%.1f%% statewide; %d of %d district-year-grade cells below 50%%"
                      % (s_.state_coverage_pct, s_.district_years_under_50pct, s_.n_district_years),
                      "outputs/tables/coverage_summary.csv",
                      output="outputs/tables/coverage_summary.csv", method="programmatic",
                      unit="percent",
                      detail={"numerator": "students in the assessment file",
                              "denominator": "UDISE+ grade-wise enrolment, State Government schools, same year",
                              "group_by": "district x grade x year"})

    # ------------------------------------------------------- bright spots
    sar, sar_level, sar_info = None, None, {}
    for lvl in [l for l in ["block", "district"] if l in usable_levels]:
        if lvl not in joined:
            continue
        u = joined[lvl]
        minn = config.MIN_STUDENTS_PER_GP if lvl == "gp" else config.MIN_STUDENTS_PER_BLOCK
        u = u[u["n_students"] >= minn] if "n_students" in u.columns else u
        r = step("STRUCTURAL ADVANTAGE RESIDUAL at %s (original metric)" % lvl.upper(),
                 metrics.structural_residual, u, "pct_mean", external.FEATURE_SETS.get(lvl, []))
        if r and r[1].get("ok"):
            sar, sar_info, sar_level = r[0], r[1], lvl
            say("          cv_r2=%.3f on %d units, %d features"
                % (sar_info["cv_r2"], sar_info["n_units"], len(sar_info["features"])))
            write(sar, "bright_spots_%s.csv" % lvl)
            with open(os.path.join(config.TABLES, "bright_spots_model_card.json"), "w") as f:
                json.dump(sar_info, f, indent=2, default=str)
            claim("Bright-spot model fit",
                  "cross-validated R2 = %.3f at %s level using %d structural features"
                  % (sar_info["cv_r2"], lvl, len(sar_info["features"])),
                  "outputs/tables/bright_spots_model_card.json")
            if len(sar):
                top = sar.iloc[0]
                claim("Strongest bright spot",
                      "%s: actual %.1f%% vs predicted %.1f%% (%+.1f pp)"
                      % (top[lvl], top["pct_mean"], top["predicted_pct"], top["residual_pp"]),
                      "outputs/tables/bright_spots_%s.csv, top row" % lvl)
            break
        elif r:
            say("          skipped: %s" % r[1].get("reason"))

    # ------------------------------------------------------------- triage
    tri, tri_level, bench = None, None, None
    for lvl in [l for l in ["block", "district"] if l in usable_levels] or ["block"]:
        src = joined.get(lvl, units.get(lvl))
        if src is None or src.empty:
            continue
        minn = config.MIN_STUDENTS_PER_GP if lvl == "gp" else config.MIN_STUDENTS_PER_BLOCK
        s = src[src["n_students"] >= minn] if "n_students" in src.columns else src
        r = step("INTERVENTION TRIAGE SCORE at %s (decision tool)" % lvl.upper(),
                 metrics.triage, s, lvl, "pct_mean", "n_students", None, external.TRACTABILITY)
        if r and len(r[0]):
            tri, bench, tri_level = r[0], r[1], lvl
            write(tri, "triage_%s.csv" % lvl)
            claim("Triage benchmark used", "%.2f%% (median %s)" % (bench, lvl),
                  "outputs/tables/triage_%s.csv" % lvl)
            claim("Top triage priority",
                  "%s, gap %.1f pp, %d children"
                  % (tri.iloc[0][lvl], tri.iloc[0]["gap_pp"], int(tri.iloc[0]["children_affected"])),
                  "outputs/tables/triage_%s.csv, top row" % lvl)
            break

    # ---------------------------------------------------------- early warning
    minfo, mscores, watch = {}, None, None
    for lvl in ["gp", "block"]:
        if lvl not in per_years or per_years[lvl] is None or per_years[lvl].empty:
            continue
        # GP keeps the model (predictions.csv needs GP ID) but with LAG features only
        # when GP fails the external gate: no unreliable covariates enter the model.
        if lvl not in usable_levels:
            joined_for_model = None
            say("   %s: external features withheld (gate refused); persistence features only" % lvl)
        else:
            joined_for_model = joined.get(lvl)
        r = step("EARLY-WARNING MODEL at %s LEVEL" % lvl.upper(), model.run,
                 per_years[lvl], lvl, joined_for_model,
                 external.FEATURE_SETS.get(lvl, []) if joined_for_model is not None else [])
        if r and r[0]:
            minfo, mscores, watch = r
            write(mscores, "model_comparison_%s.csv" % lvl)
            write(watch, "early_warning_watchlist_%s.csv" % lvl)
            with open(os.path.join(config.TABLES, "model_card.json"), "w") as f:
                json.dump(minfo, f, indent=2, default=str)
            say("          best=%s/%s  RMSE=%.2f pp  R2=%.3f" %
                (minfo["best_feature_set"], minfo["best_model"],
                 minfo["cv_rmse_pp"], minfo["cv_r2"]))
            say("          %s" % minfo["verdict"])
            claim("Early-warning model performance",
                  "%s at %s level: CV RMSE %.2f pp, R2 %.3f, precision %.2f, recall %.2f"
                  % (minfo["best_feature_set"], lvl, minfo["cv_rmse_pp"], minfo["cv_r2"],
                     minfo["early_warning_precision"], minfo["early_warning_recall"]),
                  "outputs/tables/model_card.json and model_comparison_%s.csv" % lvl)
            break

    # ------------------------------------------------- Track 2 deliverable
    try:
        full = minfo.get("_full_predictions") if minfo else None
        pdir = os.path.join(config.OUTPUTS, "predictions"); os.makedirs(pdir, exist_ok=True)
        if full is not None and "gp_id" in full.columns and full["gp_id"].notna().any():
            pred = full.dropna(subset=["gp_id"]).copy()
            pred["GP ID"] = pred["gp_id"].astype(int)
            pred["predicted_mean"] = (pred["predicted_pct"] * 0.20).round(3)   # 0-20 scale
            pred[["GP ID", "predicted_mean"]].drop_duplicates("GP ID") \
                .to_csv(os.path.join(pdir, "predictions.csv"), index=False)
            say("          -> outputs/predictions/predictions.csv (%d GPs, 0-20 scale)" % pred["GP ID"].nunique())
            claim("Track 2 predictions produced for every modelled GP",
                  "%d GPs" % pred["GP ID"].nunique(), "outputs/predictions/predictions.csv",
                  output="outputs/predictions/predictions.csv", method="reproducible", unit="GPs",
                  detail={"expected_output_file": "outputs/predictions/predictions.csv",
                          "metric_to_check": "row count and 0-20 range", "random_seed": config.SEED})
        elif units.get("gp") is not None and "gp_id" in units["gp"].columns:
            u = units["gp"].dropna(subset=["gp_id"]).copy()
            u["GP ID"] = u["gp_id"].astype(int)
            u["predicted_mean"] = (u["pct_mean"] * 0.20).round(3)
            u[["GP ID", "predicted_mean"]].drop_duplicates("GP ID") \
                .to_csv(os.path.join(pdir, "predictions.csv"), index=False)
            say("          -> predictions.csv (persistence fallback: latest observed mean)")
    except Exception as e:
        say("          predictions.csv failed: %s" % e)

    # ---------------------------------------------------------------- figures
    say("\n[%5.1fs] FIGURES" % (time.time() - T0))
    step("fig variance",     figures.variance_signature, vd)
    step("fig competency",   figures.competency_ladder, bn)
    for lvl in ["district", "block"]:
        if lvl in units and units[lvl] is not None and not units[lvl].empty:
            step("fig ranking %s" % lvl, figures.unit_ranking, units[lvl], lvl,
                 "03_%s_ranking.png" % lvl)
    step("fig gender",       figures.gender_by_competency, gg.get("by_competency"))
    step("fig floor",        figures.floor_vs_mean, fl, "district")
    if sar is not None:
        step("fig bright spots", figures.bright_spots, sar, sar_level)
    if tri is not None:
        step("fig triage",   figures.triage_map, tri, tri_level)
    step("fig progression",  figures.progression_chart, coh_sum)
    step("fig year x grade", figures.heatmap_year_grade, df)

    # -------------------------------------------------------------- dashboard
    say("\n[%5.1fs] DASHBOARD" % (time.time() - T0))
    ctx = {"df": df, "meta": meta, "variance": vd, "unit_district": units.get("district"),
           "bottleneck": bn, "gender_by_competency": gg.get("by_competency"), "floor": fl,
           "sar": sar, "sar_level": sar_level, "triage": tri, "watch": watch,
           "qa_flags": qa_flags,
           "title": "Karnataka mathematics learning: from data to decisions",
           "subtitle": "Datathon 2026 | %d student records | %d districts | %d blocks | %d GPs | seed %d"
                       % (len(df), df.district.nunique(), df.block.nunique(),
                          df.gp.nunique(), config.SEED),
           "footer": "Sources: Akshara Foundation competency assessments (primary). "
                     + "; ".join(sorted(set(all_sources))) if all_sources else ""}
    step("build dashboard", dashboard.build, ctx)

    # ------------------------------------------------------------- manifest
    say("\n[%5.1fs] MANIFEST AND CLAIMS" % (time.time() - T0))
    def rel(p):
        return os.path.relpath(p, config.ROOT).replace("\\", "/")
    produced = []
    for root, _dirs, files in os.walk(config.OUTPUTS):
        for f in sorted(files):
            if f.startswith("."):
                continue
            produced.append(rel(os.path.join(root, f)))
    DESC = {"dashboard.html": "interactive dashboard, static export",
            "predictions.csv": "predicted mean score per GP (0-20 scale), Track 2 deliverable"}
    with open(os.path.join(config.ROOT, "manifest.yml"), "w", encoding="utf-8") as f:
        f.write("# Auto-generated by src/run_all.py against the official template schema.\n")
        f.write('team_name: "datathon_csf"\n\n')
        f.write("tracks_addressed:\n")
        for t_ in ['Data Insights & Visualization', 'Predictive Analytics',
                   'Policy & Intervention Design']:
            f.write('  - "%s"\n' % t_)
        f.write('\nproblem_statements:\n  - "Where and for whom is mathematics being lost in the '
                'GP Contest data, and what would move it"\n')
        f.write("\noutputs:\n")
        for p in produced:
            d_ = DESC.get(os.path.basename(p), "")
            f.write('  - file: "%s"\n' % p)
            f.write('    description: "%s"\n' % (d_ or os.path.basename(p).replace("_", " ").rsplit(".", 1)[0]))
            if os.path.basename(p) == "predictions.csv":
                f.write('    evaluation_file: "outputs/tables/model_comparison_gp.csv"\n')
        f.write("\nexternal_datasets:\n")
        for s_ in sorted(set(all_sources)) or []:
            f.write('  - file: "external_data/ (see external_data/SOURCES.md)"\n    source: "%s"\n' % s_)
    say("          -> manifest.yml (%d output files)" % len(produced))

    with open(os.path.join(config.ROOT, "claims.json"), "w", encoding="utf-8") as f:
        json.dump({"team_name": "datathon_csf", "claims": CLAIMS}, f, indent=2, default=str)
    say("          -> claims.json (%d claims, template schema)" % len(CLAIMS))

    say("\n" + "=" * 78)
    say("FINISHED in %.1f seconds" % (time.time() - T0))
    if FAILED:
        say("STEPS THAT FAILED (%d) - the rest still ran:" % len(FAILED))
        for s in FAILED:
            say("   - %s" % s)
    else:
        say("All steps completed with no failures.")
    say("Outputs in: outputs/    Read outputs/tables/qa_flags.csv FIRST.")
    say("=" * 78)

if __name__ == "__main__":
    try:
        main()
    except Exception:
        say("\nFATAL: the pipeline could not start.")
        say(traceback.format_exc())
    finally:
        os.makedirs(config.OUTPUTS, exist_ok=True)
        with open(os.path.join(config.OUTPUTS, "RUN_LOG.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(LOG))
        print("\nFull log written to outputs/RUN_LOG.txt")
