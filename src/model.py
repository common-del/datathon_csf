"""
Early-warning model.
Question asked: can we flag the places that will be behind NEXT year, using only
what is knowable this year? Three nested models, honestly compared:
  A  persistence  - last year's own score only (the baseline a district officer already has)
  B  structural   - socio-economic + school-system conditions only
  C  both
If C does not beat A, say so. That is a finding, not a failure.
"""
import numpy as np, pandas as pd
import config

def _pipe(alpha_grid=None):
    from sklearn.pipeline import make_pipeline
    from sklearn.impute import SimpleImputer
    from sklearn.preprocessing import StandardScaler
    from sklearn.linear_model import RidgeCV
    return make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                         RidgeCV(alphas=alpha_grid if alpha_grid is not None else np.logspace(-2, 3, 20)))

def _gbm():
    from sklearn.ensemble import HistGradientBoostingRegressor
    return HistGradientBoostingRegressor(random_state=config.SEED, max_iter=250,
                                         learning_rate=0.06, max_depth=3)

def build_panel(per_year, level, cov, features):
    """Wide panel: one row per unit, prior-year score + structural features + target."""
    if per_year is None or len(per_year) == 0 or "year_n" not in per_year.columns:
        return None, None, None
    yrs = sorted(per_year["year_n"].dropna().unique())
    if len(yrs) < 2:
        return None, None, None
    keys = [c for c in ["division","district","block","cluster","gp"] if c in per_year.columns]
    key = keys[: keys.index(level) + 1] if level in keys else [level]

    frames = []
    extra = ["gp_id"] if "gp_id" in per_year.columns else []
    for i, y in enumerate(yrs):
        s = (per_year[per_year.year_n == y][key + extra + ["pct_mean","pct_floor","n_students"]]
             .rename(columns={"pct_mean": "score_y%d" % i, "pct_floor": "floor_y%d" % i,
                              "n_students": "n_y%d" % i}))
        s = s.drop(columns=[c for c in extra if i > 0 and c in s.columns])
        frames.append(s.set_index(key))
    panel = frames[0]
    for f in frames[1:]:
        panel = panel.join(f, how="inner")
    panel = panel.reset_index()

    last = len(yrs) - 1
    panel["target"] = panel["score_y%d" % last]
    lag_cols = ["score_y%d" % i for i in range(last)] + ["floor_y%d" % i for i in range(last)]
    if cov is not None and len(cov):
        cov_keys = [c for c in key if c in cov.columns]
        usable = [c for c in features if c in cov.columns]
        if cov_keys and usable:
            panel = panel.merge(cov[cov_keys + usable].drop_duplicates(cov_keys),
                                on=cov_keys, how="left")
    struct = [c for c in features if c in panel.columns]
    panel = panel[panel["n_y%d" % last].fillna(0) >= (config.MIN_STUDENTS_PER_GP if level == "gp"
                                                      else config.MIN_STUDENTS_PER_BLOCK)]
    return panel, lag_cols, struct

def run(per_year, level, cov, features):
    from sklearn.model_selection import KFold, cross_val_predict
    panel, lag, struct = build_panel(per_year, level, cov, features)
    if panel is None or len(panel) < 60:
        return {}, pd.DataFrame(), pd.DataFrame()

    y = panel["target"].astype(float)
    cv = KFold(n_splits=5, shuffle=True, random_state=config.SEED)
    specs = {"A_persistence": lag, "B_structural_only": struct, "C_both": lag + struct}
    rows, preds = [], {}
    for name, cols in specs.items():
        cols = [c for c in cols if c in panel.columns]
        if not cols:
            continue
        X = panel[cols].apply(pd.to_numeric, errors="coerce")
        for mdl_name, mdl in [("ridge", _pipe()), ("gbm", _gbm())]:
            if mdl_name == "gbm":
                Xg = X.fillna(X.median(numeric_only=True))
                p = cross_val_predict(mdl, Xg, y, cv=cv)
            else:
                p = cross_val_predict(mdl, X, y, cv=cv)
            rmse = float(np.sqrt(((y - p) ** 2).mean()))
            mae  = float(np.abs(y - p).mean())
            r2   = 1 - float(((y - p) ** 2).sum() / ((y - y.mean()) ** 2).sum())
            rows.append({"feature_set": name, "model": mdl_name, "n_units": len(panel),
                         "n_features": len(cols), "cv_rmse_pp": round(rmse, 3),
                         "cv_mae_pp": round(mae, 3), "cv_r2": round(r2, 3)})
            preds[(name, mdl_name)] = p
    scores = pd.DataFrame(rows).sort_values("cv_rmse_pp")
    if scores.empty:
        return {}, pd.DataFrame(), pd.DataFrame()

    best = scores.iloc[0]
    a = scores[scores.feature_set == "A_persistence"]["cv_rmse_pp"].min() if (scores.feature_set == "A_persistence").any() else np.nan
    verdict = ("structural data improves on the persistence baseline by %.2f pp RMSE"
               % (a - best.cv_rmse_pp)) if pd.notna(a) and best.feature_set != "A_persistence" \
              else "no feature set beats simple persistence - report that honestly"

    p = preds[(best.feature_set, best.model)]
    panel = panel.copy()
    panel["predicted_pct"] = np.round(p, 2)
    panel["prediction_error_pp"] = np.round(y - p, 2)
    cut = float(np.nanpercentile(panel["target"], 25))
    panel["actual_bottom_quartile"] = (panel["target"] <= cut).astype(int)
    panel["predicted_bottom_quartile"] = (panel["predicted_pct"] <= cut).astype(int)
    tp = int(((panel.actual_bottom_quartile == 1) & (panel.predicted_bottom_quartile == 1)).sum())
    fp = int(((panel.actual_bottom_quartile == 0) & (panel.predicted_bottom_quartile == 1)).sum())
    fn = int(((panel.actual_bottom_quartile == 1) & (panel.predicted_bottom_quartile == 0)).sum())
    prec = tp / max(tp + fp, 1); rec = tp / max(tp + fn, 1)

    info = {"level": level, "best_feature_set": best.feature_set, "best_model": best.model,
            "cv_rmse_pp": float(best.cv_rmse_pp), "cv_r2": float(best.cv_r2),
            "persistence_rmse_pp": float(a) if pd.notna(a) else None,
            "verdict": verdict, "n_units": int(len(panel)),
            "bottom_quartile_cutoff_pct": round(cut, 2),
            "early_warning_precision": round(prec, 3), "early_warning_recall": round(rec, 3),
            "n_structural_features": len(struct), "structural_features": struct}

    keys = [c for c in ["division","district","block","cluster","gp"] if c in panel.columns]
    watch = panel[panel.predicted_bottom_quartile == 1][
        keys + ["target","predicted_pct","prediction_error_pp","n_y%d" % (len(
            [c for c in panel.columns if c.startswith("score_y")]) - 1)]].copy()
    watch = watch.rename(columns={"target": "latest_actual_pct"}) \
                 .sort_values("predicted_pct").head(120)
    full = panel[keys + (["gp_id"] if "gp_id" in panel.columns else []) +
                 ["target", "predicted_pct"]].copy()
    info["_full_predictions"] = full
    return info, scores, watch
