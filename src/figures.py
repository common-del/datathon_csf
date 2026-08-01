"""Static figures. Colour rule: green = better for children, red = worse, white at benchmark."""
import os
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
import config

CMAP = LinearSegmentedColormap.from_list("gwr", config.DIVERGING, N=256)
plt.rcParams.update({"figure.dpi": 130, "savefig.dpi": 160, "font.size": 9,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "axes.titlesize": 11, "axes.titleweight": "bold",
                     "axes.labelcolor": config.INK, "text.color": config.INK,
                     "figure.autolayout": True})

def save(fig, name):
    os.makedirs(config.FIGURES, exist_ok=True)
    p = os.path.join(config.FIGURES, name)
    fig.savefig(p, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return p

def _bar_diverging(ax, labels, values, benchmark, xlabel):
    v = np.asarray(values, dtype=float)
    lo, hi = np.nanmin(v), np.nanmax(v)
    norm = TwoSlopeNorm(vmin=min(lo, benchmark - 1e-6), vcenter=benchmark,
                        vmax=max(hi, benchmark + 1e-6))
    ax.barh(labels, v, color=[CMAP(norm(x)) for x in v], edgecolor="none")
    ax.axvline(benchmark, color=config.INK, lw=1.1, ls="--")
    ax.set_xlabel(xlabel)
    ax.invert_yaxis()

def variance_signature(vd, path="01_variance_signature.png"):
    if vd is None or vd.empty: return None
    d = vd.copy()
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    y = np.arange(len(d))
    ax.barh(y, d["share_of_total_variation_pct"], color="#9ecae1", label="share of total variation")
    ax.barh(y, d["share_adjusted_pct"], height=0.42, color=config.GREEN,
            label="df-adjusted variance component")
    ax.set_yticks(y); ax.set_yticklabels(d["level"]); ax.invert_yaxis()
    ax.set_xlabel("% of variation in student scores")
    ax.set_title("Where does learning variation actually live?")
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    for i, v in enumerate(d["share_of_total_variation_pct"]):
        if pd.notna(v): ax.text(v + 0.7, i, "%.1f%%" % v, va="center", fontsize=8)
    return save(fig, path)

def competency_ladder(bn, path="02_competency_bottleneck.png"):
    if bn is None or bn.empty: return None
    d = bn.dropna(subset=["mastery_rate_pct"]).sort_values("mastery_rate_pct", ascending=False)
    fig, ax = plt.subplots(figsize=(8.2, 4.2))
    lab = [str(x)[:44] for x in d["competency_label"]]
    _bar_diverging(ax, lab, d["mastery_rate_pct"], float(d["mastery_rate_pct"].median()),
                   "% of students mastering the competency")
    ax.set_title("Competency ladder: mastery rate (dashed line = median competency)")
    ax2 = ax.twiny()
    ax2.plot(d["gate_lift_pp"], np.arange(len(d)), "o-", color=config.INK, ms=4, lw=1)
    ax2.set_xlabel("gate lift (pp) - how strongly this gates harder competencies")
    ax2.spines["top"].set_visible(True)
    return save(fig, path)

def unit_ranking(unit, level, path=None, top=None, value="pct_mean"):
    if unit is None or unit.empty or value not in unit.columns: return None
    top = top or config.TOP_N_REPORT
    d = unit.dropna(subset=[value]).sort_values(value)
    bench = float(d[value].median())
    sel = pd.concat([d.head(top), d.tail(top)])
    fig, ax = plt.subplots(figsize=(7.4, 0.26*len(sel) + 1.4))
    _bar_diverging(ax, [str(x)[:30] for x in sel[level]], sel[value], bench,
                   "mean % correct")
    ax.set_title("%s: weakest and strongest %d (dashed = state median %.1f%%)"
                 % (level.upper(), top, bench))
    return save(fig, path or "03_%s_ranking.png" % level)

def gender_by_competency(piv, path="04_gender_by_competency.png"):
    if piv is None or piv.empty or "gap_pp_F_minus_M" not in piv.columns: return None
    d = piv.sort_values("overall_mastery_pct", ascending=False)
    fig, ax = plt.subplots(figsize=(7.6, 4.0))
    _bar_diverging(ax, [str(x)[:42] for x in d["competency_label"]],
                   d["gap_pp_F_minus_M"], 0.0, "girls minus boys, pp (mastery)")
    ax.set_title("Gender gap by competency, ordered easiest to hardest")
    return save(fig, path)

def floor_vs_mean(ch, level, path="05_floor_vs_mean.png"):
    if ch is None or ch.empty or "floor_change_pp" not in ch.columns: return None
    d = ch.dropna(subset=["mean_change_pp","floor_change_pp"])
    fig, ax = plt.subplots(figsize=(5.8, 5.4))
    v = d["floor_minus_mean_divergence_pp"]
    norm = TwoSlopeNorm(vmin=min(v.min(), -1e-6), vcenter=0, vmax=max(v.max(), 1e-6))
    ax.scatter(d["mean_change_pp"], d["floor_change_pp"], s=52,
               c=[CMAP(norm(x)) for x in v], edgecolor=config.INK, lw=0.4)
    lim = [min(d.mean_change_pp.min(), d.floor_change_pp.min()) - 1,
           max(d.mean_change_pp.max(), d.floor_change_pp.max()) + 1]
    ax.plot(lim, lim, ls="--", lw=1, color=config.GREY)
    ax.axhline(0, lw=0.8, color=config.GREY); ax.axvline(0, lw=0.8, color=config.GREY)
    for _, r in d.iterrows():
        ax.annotate(str(r[level])[:14], (r.mean_change_pp, r.floor_change_pp),
                    fontsize=6.5, xytext=(3, 3), textcoords="offset points")
    ax.set_xlabel("change in MEAN (pp)"); ax.set_ylabel("change in FLOOR, p%d (pp)" % config.FLOOR_PERCENTILE)
    ax.set_title("Did the average move, or did the weakest children move?\nBelow the line = growth that skipped the bottom")
    return save(fig, path)

def bright_spots(sar, level, path="06_bright_spots.png"):
    if sar is None or sar.empty or "residual_pp" not in sar.columns: return None
    d = sar.dropna(subset=["predicted_pct","pct_mean"])
    fig, ax = plt.subplots(figsize=(6.2, 5.4))
    v = d["residual_pp"]
    norm = TwoSlopeNorm(vmin=min(v.min(), -1e-6), vcenter=0, vmax=max(v.max(), 1e-6))
    ax.scatter(d["predicted_pct"], d["pct_mean"], s=26, alpha=0.85,
               c=[CMAP(norm(x)) for x in v], edgecolor="none")
    lim = [min(d.predicted_pct.min(), d.pct_mean.min()) - 1,
           max(d.predicted_pct.max(), d.pct_mean.max()) + 1]
    ax.plot(lim, lim, ls="--", lw=1, color=config.INK)
    ax.set_xlabel("predicted from socio-economic + school-system conditions (%)")
    ax.set_ylabel("actual mean score (%)")
    ax.set_title("Bright spots: %s doing better than their circumstances predict" % level.upper())
    for _, r in d.head(6).iterrows():
        ax.annotate(str(r[level])[:16], (r.predicted_pct, r.pct_mean), fontsize=6.5,
                    xytext=(3, 3), textcoords="offset points")
    return save(fig, path)

def triage_map(tri, level, path="07_triage.png"):
    if tri is None or tri.empty: return None
    d = tri.head(25)
    fig, ax = plt.subplots(figsize=(7.4, 0.3*len(d) + 1.3))
    v = d["triage_score"].to_numpy(dtype=float)
    norm = TwoSlopeNorm(vmin=0, vcenter=max(v.mean(), 1e-6), vmax=max(v.max(), 1e-6))
    ax.barh([str(x)[:32] for x in d[level]], v,
            color=[CMAP(1 - norm(x)) for x in v], edgecolor="none")
    ax.invert_yaxis(); ax.set_xlabel("Intervention Triage Score")
    ax.set_title("Top 25 %s by triage priority (gap x children x tractability)" % level)
    return save(fig, path)

def progression_chart(summary, path="08_cohort_progression.png"):
    if summary is None or summary.empty: return None
    fig, ax = plt.subplots(figsize=(7.0, 3.4))
    d = summary.sort_values("cohort")
    _bar_diverging(ax, d["cohort"], d["mean_progression_pp"], 0.0,
                   "mean change in % correct as the cohort moves up a grade")
    ax.set_title("Synthetic cohort progression")
    return save(fig, path)

def heatmap_year_grade(df, path="09_year_grade_heatmap.png"):
    if df["year"].isna().all() or df["grade"].isna().all(): return None
    p = df.pivot_table(index="grade", columns="year", values="pct", aggfunc="mean")
    if p.empty: return None
    fig, ax = plt.subplots(figsize=(1.5*len(p.columns) + 2.2, 0.7*len(p) + 1.8))
    norm = TwoSlopeNorm(vmin=np.nanmin(p.values), vcenter=float(np.nanmean(p.values)),
                        vmax=np.nanmax(p.values))
    im = ax.imshow(p.values, cmap=CMAP, norm=norm, aspect="auto")
    ax.set_xticks(range(len(p.columns))); ax.set_xticklabels(p.columns)
    ax.set_yticks(range(len(p.index)));  ax.set_yticklabels(["Grade %g" % g for g in p.index])
    for i in range(p.shape[0]):
        for j in range(p.shape[1]):
            if pd.notna(p.values[i, j]):
                ax.text(j, i, "%.1f" % p.values[i, j], ha="center", va="center", fontsize=9)
    ax.set_title("Mean % correct by grade and year")
    fig.colorbar(im, ax=ax, shrink=0.8, label="% correct")
    return save(fig, path)
