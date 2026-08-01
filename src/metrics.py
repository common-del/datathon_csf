"""The original metrics. These are the innovation content of the submission."""
import numpy as np, pandas as pd, config

# ---------------------------------------------------------------- 1. variance
def variance_decomposition(df, levels=None,
                           value="pct"):
    """
    Learning Variance Signature.
    Splits total variation in student scores across the administrative hierarchy.
    Returns share of total sum of squares at each nested level, plus a
    degrees-of-freedom-adjusted variance-component estimate.

    Interpretation that matters: if the 'within Gram Panchayat' share is large,
    then targeting districts or blocks cannot reach most of the gap, however
    well it is executed.
    """
    levels = levels or getattr(config, "GEO_LEVELS", ["district","block","cluster","gp"])
    lv = [l for l in levels if l in df.columns and df[l].notna().any()]
    # subset to needed columns BEFORE any copy: at census scale the full-frame copy is an OOM
    d = df[lv + [value]].dropna()
    if len(d) == 0 or not lv:
        return pd.DataFrame(), pd.DataFrame()

    y = d[value].astype(float)
    grand = y.mean()
    ss_total = float(((y - grand) ** 2).sum())
    rows, prev_key, prev_fit = [], None, pd.Series(grand, index=d.index)

    for i, l in enumerate(lv):
        key = lv[: i + 1]
        grp = d.groupby(key, dropna=False)[value]
        fit = grp.transform("mean")
        ss = float(((fit - prev_fit) ** 2).sum())
        ngroups = int(grp.ngroups)
        df_lvl = max(ngroups - (0 if prev_key is None else d.groupby(prev_key).ngroups), 1)
        rows.append({"level": l, "n_units": ngroups, "df": df_lvl,
                     "ss": ss, "ms": ss / df_lvl,
                     "share_of_total_variation_pct": 100.0 * ss / ss_total if ss_total else np.nan})
        prev_key, prev_fit = key, fit

    ss_res = float(((y - prev_fit) ** 2).sum())
    df_res = max(len(d) - d.groupby(prev_key).ngroups, 1)
    rows.append({"level": "within_%s (student)" % lv[-1], "n_units": len(d), "df": df_res,
                 "ss": ss_res, "ms": ss_res / df_res,
                 "share_of_total_variation_pct": 100.0 * ss_res / ss_total if ss_total else np.nan})

    out = pd.DataFrame(rows)
    # df-adjusted variance components (nested ANOVA method of moments, bottom-up)
    ms = out["ms"].to_numpy(dtype=float)
    comp = np.zeros(len(ms)); comp[-1] = ms[-1]
    for i in range(len(ms) - 2, -1, -1):
        nbar = len(d) / max(out.loc[i, "n_units"], 1)
        comp[i] = max((ms[i] - ms[i + 1]) / nbar, 0.0)
    out["variance_component_adj"] = comp
    tot = comp.sum()
    out["share_adjusted_pct"] = 100.0 * comp / tot if tot > 0 else np.nan
    out[["ss","ms","variance_component_adj"]] = out[["ss","ms","variance_component_adj"]].round(3)
    out[["share_of_total_variation_pct","share_adjusted_pct"]] = \
        out[["share_of_total_variation_pct","share_adjusted_pct"]].round(2)

    # Ceiling rides the df-ADJUSTED shares so it stays consistent with every quoted share.
    # The raw cumulative is kept alongside for transparency; never mix the two in one sentence.
    ceiling = out[out["level"] != out["level"].iloc[-1]].copy()
    ceiling["targeting_efficiency_ceiling_pct"] = ceiling["share_adjusted_pct"].cumsum().round(2)
    ceiling["ceiling_raw_basis_pct"] = ceiling["share_of_total_variation_pct"].cumsum().round(2)
    ceiling = ceiling[["level","targeting_efficiency_ceiling_pct","ceiling_raw_basis_pct"]]
    ceiling["reads_as"] = ("max share of learning variation reachable by targeting at "
                          + ceiling["level"] + " level or coarser (df-adjusted basis)")
    return out, ceiling

# ------------------------------------------------------- 2. competency ladder
def competency_bottleneck(df, cmap, items):
    """
    For each competency A, how strongly does mastering A gate mastery of harder
    competencies?  gate_lift = P(master B | master A) - P(master B | not A),
    averaged over all B harder than A.
    Bottleneck Score = gate_lift x (1 - mastery_rate_A):
    high gate AND low current mastery = the binding constraint on progress.
    """
    ccols = [c for c in df.columns if c.startswith("C_")]
    if len(ccols) < 2:
        return pd.DataFrame(), pd.DataFrame()
    mast = pd.DataFrame(index=df.index)
    for c in ccols:
        mast[c[2:].replace("_", " ")] = (df[c] >= 0.5).astype(float).where(df[c].notna())
    rate = mast.mean().sort_values(ascending=False)
    order = list(rate.index)                       # easiest (highest mastery) first
    lab = {k: k for k in order}

    # vectorised pairwise conditionals via matrix products (census-scale safe)
    M   = mast[order].to_numpy(dtype="float32")
    fin = np.isfinite(M)
    X1  = ((M == 1) & fin).astype("float32")
    X0  = ((M == 0) & fin).astype("float32")
    Xv  = fin.astype("float32")
    n11, n1v = X1.T @ X1, X1.T @ Xv          # a=1&b=1 ; a=1&b valid
    n01, n0v = X0.T @ X1, X0.T @ Xv          # a=0&b=1 ; a=0&b valid
    del M, fin, X1, X0, Xv

    pairs, rows = [], []
    for i, a in enumerate(order):
        lifts = []
        for j in range(i + 1, len(order)):
            b = order[j]
            if n1v[i, j] + n0v[i, j] < 200:
                continue
            p1 = n11[i, j] / n1v[i, j] if n1v[i, j] > 0 else np.nan
            p0 = n01[i, j] / n0v[i, j] if n0v[i, j] > 0 else np.nan
            if np.isnan(p1) or np.isnan(p0):
                continue
            lifts.append(p1 - p0)
            pairs.append({"prerequisite": a, "prerequisite_label": lab.get(a, a),
                          "dependent": b, "dependent_label": lab.get(b, b),
                          "p_dep_given_prereq_pct": round(100*p1, 1),
                          "p_dep_without_prereq_pct": round(100*p0, 1),
                          "lift_pp": round(100*(p1 - p0), 1)})
        gate = float(np.mean(lifts)) if lifts else np.nan
        rows.append({"competency_code": a, "competency_label": lab.get(a, a),
                     "mastery_rate_pct": round(100*float(rate[a]), 1),
                     "gate_lift_pp": round(100*gate, 1) if pd.notna(gate) else np.nan,
                     "n_downstream": len(lifts),
                     "bottleneck_score": round(gate*(1 - float(rate[a])), 4)
                                          if pd.notna(gate) else np.nan})
    bn = pd.DataFrame(rows).sort_values("bottleneck_score", ascending=False)
    return bn, pd.DataFrame(pairs)

# ---------------------------------------------------------------- 3. the floor
def floor_index(df, level="district", value="pct"):
    """
    Floor Index = the score at the FLOOR_PERCENTILE of the distribution.
    Floor-Mean Divergence = change in floor minus change in mean between first
    and last year. Positive means the weakest children gained faster than average;
    negative means the average moved without the bottom moving.
    """
    if level not in df.columns or df[level].isna().all():
        return pd.DataFrame()
    p = config.FLOOR_PERCENTILE
    g = (df.dropna(subset=[level, value])
           .groupby([level, "year", "year_n"], dropna=False)[value]
           .agg(n="size", mean="mean",
                floor=lambda s: np.nanpercentile(s, p),
                p90=lambda s: np.nanpercentile(s, 90))
           .reset_index())
    g["spread_p90_minus_floor"] = (g["p90"] - g["floor"]).round(2)
    yrs = sorted(g["year_n"].dropna().unique())
    if len(yrs) >= 2:
        first, last = g[g.year_n == yrs[0]], g[g.year_n == yrs[-1]]
        ch = (first.set_index(level)[["mean","floor"]]
                   .join(last.set_index(level)[["mean","floor"]], lsuffix="_first", rsuffix="_last",
                         how="inner"))
        ch["mean_change_pp"]  = (ch["mean_last"]  - ch["mean_first"]).round(2)
        ch["floor_change_pp"] = (ch["floor_last"] - ch["floor_first"]).round(2)
        ch["floor_minus_mean_divergence_pp"] = (ch["floor_change_pp"] - ch["mean_change_pp"]).round(2)
        ch = ch.reset_index().sort_values("floor_change_pp")
        ch["years_compared"] = "%s -> %s" % (
            first["year"].iloc[0] if len(first) else "", last["year"].iloc[0] if len(last) else "")
        return ch
    return g.round(2)

# ------------------------------------------------- 4. structural residual (SAR)
def structural_residual(unit_df, y="pct_mean", features=None, min_features=2):
    """
    Structural Advantage Residual: actual learning minus what socio-economic and
    school-system conditions predict. Positive residual = a bright spot that is
    doing better than its circumstances, and therefore worth studying.
    Ridge regression, standardised features, median-imputed.
    """
    from sklearn.linear_model import RidgeCV
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import make_pipeline
    from sklearn.impute import SimpleImputer
    from sklearn.model_selection import cross_val_predict, KFold

    feats = [c for c in (features or []) if c in unit_df.columns
             and pd.to_numeric(unit_df[c], errors="coerce").notna().sum() > 0.5*len(unit_df)]
    if len(feats) < min_features or y not in unit_df.columns:
        return pd.DataFrame(), {"ok": False, "reason": "not enough usable features (%d)" % len(feats)}
    d = unit_df.dropna(subset=[y]).copy()
    if len(d) < 40:
        return pd.DataFrame(), {"ok": False, "reason": "only %d units" % len(d)}

    X = d[feats].apply(pd.to_numeric, errors="coerce")
    yv = d[y].astype(float)
    pipe = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                         RidgeCV(alphas=np.logspace(-2, 3, 20)))
    cv = KFold(n_splits=5, shuffle=True, random_state=config.SEED)
    pred = cross_val_predict(pipe, X, yv, cv=cv)
    pipe.fit(X, yv)
    coef = pipe[-1].coef_
    r2 = 1 - float(((yv - pred) ** 2).sum() / ((yv - yv.mean()) ** 2).sum())

    d["predicted_pct"] = np.round(pred, 2)
    d["residual_pp"]   = np.round(yv - pred, 2)
    d["residual_z"]    = np.round((d["residual_pp"] - d["residual_pp"].mean())
                                  / d["residual_pp"].std(ddof=0), 2)
    d["bright_spot"]   = np.where(d["residual_z"] >= 1.0, "BRIGHT SPOT",
                          np.where(d["residual_z"] <= -1.0, "UNDER-PERFORMING", "as expected"))
    info = {"ok": True, "n_units": len(d), "cv_r2": round(r2, 3), "features": feats,
            "coefficients": dict(zip(feats, np.round(coef, 3)))}
    return d.sort_values("residual_pp", ascending=False), info

# -------------------------------------------------------------- 5. triage tool
def triage(unit_df, unit_col, y="pct_mean", n_col="n_students",
           benchmark=None, tractability_cols=None):
    """
    Intervention Triage Score = normalised (learning gap) x (children affected)
    x (tractability). Tractability rises when the shortfall looks like something
    a programme can move (weak teacher availability, weak inputs) rather than
    deep structural poverty alone.
    Output is a ranked action list, not a league table.
    """
    d = unit_df.dropna(subset=[y]).copy()
    if len(d) == 0:
        return pd.DataFrame()
    bench = benchmark if benchmark is not None else float(d[y].median())
    d["gap_pp"] = (bench - d[y]).clip(lower=0).round(2)
    n = pd.to_numeric(d[n_col], errors="coerce").fillna(0) if n_col in d.columns else pd.Series(1.0, index=d.index)

    def nz(s):
        s = pd.to_numeric(s, errors="coerce").astype(float)
        rng = s.max() - s.min()
        return (s - s.min()) / rng if rng and pd.notna(rng) else pd.Series(0.5, index=s.index)

    tract = pd.Series(0.5, index=d.index)
    used = []
    if tractability_cols:
        parts = []
        for c, direction in tractability_cols:
            if c in d.columns and pd.to_numeric(d[c], errors="coerce").notna().sum() > 0.5*len(d):
                v = nz(d[c]); parts.append(v if direction == "high_is_tractable" else 1 - v)
                used.append(c)
        if parts:
            tract = pd.concat(parts, axis=1).mean(axis=1).fillna(0.5)

    d["children_affected"] = n.round(0)
    d["norm_gap"]          = nz(d["gap_pp"]).round(3)
    d["norm_children"]     = nz(n).round(3)
    d["tractability"]      = tract.round(3)
    d["triage_score"]      = (100 * d["norm_gap"] * (0.35 + 0.65*d["norm_children"])
                              * (0.5 + 0.5*d["tractability"])).round(1)
    d["priority_band"] = pd.qcut(d["triage_score"].rank(method="first"), 4,
                                 labels=["4 - monitor","3 - plan","2 - act soon","1 - act now"])
    keep = [unit_col] if unit_col in d.columns else []
    keep += [c for c in ["division","district","block","cluster","gp"] if c in d.columns and c != unit_col]
    keep += [y, "children_affected", "gap_pp", "norm_gap", "norm_children",
             "tractability", "triage_score", "priority_band"] + used
    keep = list(dict.fromkeys([c for c in keep if c in d.columns]))
    return d[keep].sort_values("triage_score", ascending=False), bench
