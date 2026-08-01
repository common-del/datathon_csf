"""
VARIANCE DECOMPOSITION ON GP MEANS (not on students).

Why this exists. The student-level decomposition attributes 78% of variation to "within GP".
That residual is not a GP effect. It is everything we cannot see: school, teacher, household,
and the child. Those cannot be separated because the data carries no school or student ID.

So this script removes that layer entirely. It collapses every Gram Panchayat to a single mean
score, then asks a cleaner question: of the differences BETWEEN places, how much is district,
how much is block, how much is cluster, and how much is the GP itself?

Two honest warnings, both handled below.
  1. More groups always explain more variance. There are 29 districts, ~168 blocks, ~2,961
     clusters. Cluster will win any raw R2 contest by degrees of freedom alone. Every number
     here is therefore reported both raw and df-adjusted (omega-squared style).
  2. GP and cluster do not nest. 1,718 GP IDs span more than one cluster. Each GP is assigned
     its modal cluster (the one most of its children sat in) and the share of GPs where that
     assignment is ambiguous is reported.

Run from repo root:
    python src/variance_gp_level.py

Writes:
    outputs/figures/16_variance_gp_level.png
    outputs/tables/variance_gp_level.csv
    outputs/tables/variance_gp_level_sequential.csv
"""
import os, sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE); os.chdir(ROOT)
FIG = os.path.join("outputs", "figures"); TAB = os.path.join("outputs", "tables")
GREEN, RED, BLUE, INK, MUT, GREY = "#1B7837", "#B2182B", "#2C6E8F", "#123B47", "#6B7C80", "#C9D4D6"
MIN_STUDENTS_PER_GP = 15          # a GP mean built on fewer children is mostly noise

import loader
df, meta = loader.load()
df = df[["district", "block", "cluster", "gp_id", "pct"]].dropna(subset=["gp_id", "pct"])
print("student rows with a GP ID and a score: %s" % f"{len(df):,}")

# ---------------------------------------------------------------- collapse to GP means
g = (df.groupby("gp_id")
       .agg(n=("pct", "size"), mean_pct=("pct", "mean"),
            district=("district", lambda s: s.mode().iat[0] if len(s.mode()) else np.nan),
            block=("block", lambda s: s.mode().iat[0] if len(s.mode()) else np.nan),
            cluster=("cluster", lambda s: s.mode().iat[0] if len(s.mode()) else np.nan))
       .reset_index())
amb = (df.groupby("gp_id")["cluster"].nunique() > 1).mean()
print("GPs before filtering: %d | share spanning >1 cluster (modal cluster assigned): %.1f%%"
      % (len(g), 100 * amb))
G = g[g.n >= MIN_STUDENTS_PER_GP].dropna(subset=["district", "block", "cluster"]).copy()
print("GPs kept (>= %d students): %d | districts %d | blocks %d | clusters %d"
      % (MIN_STUDENTS_PER_GP, len(G), G.district.nunique(), G.block.nunique(), G.cluster.nunique()))
del df

y = G["mean_pct"].to_numpy(dtype="float64")
gm = y.mean(); sst = float(((y - gm) ** 2).sum()); N = len(y)
print("\nvariance being explained: SD of GP means = %.2f pp across %d GPs" % (y.std(ddof=1), N))

def eta(labels):
    """share of the variance in GP means explained by these groups, raw and df-adjusted."""
    lab = pd.Series(labels).astype(str).to_numpy()
    dfm = pd.DataFrame({"y": y, "g": lab})
    grp = dfm.groupby("g")["y"]
    k = grp.ngroups
    ssb = float((grp.count() * (grp.mean() - gm) ** 2).sum())
    r2 = ssb / sst
    ssw = sst - ssb
    dfb, dfw = k - 1, N - k
    if dfw <= 0: return r2 * 100, np.nan, k
    ms_w = ssw / dfw
    omega = (ssb - dfb * ms_w) / (sst + ms_w)      # omega-squared: penalises group count
    return r2 * 100, max(omega, 0.0) * 100, k

rows = []
for name, col in [("District", G.district), ("Block", G.block),
                  ("Cluster", G.cluster), ("GP (each its own group)", G.gp_id)]:
    r2, om, k = eta(col)
    rows.append({"level": name, "n_groups": k, "raw_pct_of_between_place_variance": round(r2, 1),
                 "df_adjusted_pct": round(om, 1) if np.isfinite(om) else np.nan})
R = pd.DataFrame(rows)
R.to_csv(os.path.join(TAB, "variance_gp_level.csv"), index=False)
print("\nEACH LEVEL ON ITS OWN (share of variance BETWEEN GP means)")
print("   %-26s %8s %10s %14s" % ("level", "groups", "raw %", "df-adjusted %"))
for _, r in R.iterrows():
    print("   %-26s %8d %9.1f%% %13s" % (r.level, r.n_groups, r.raw_pct_of_between_place_variance,
          ("%.1f%%" % r.df_adjusted_pct) if pd.notna(r.df_adjusted_pct) else "n/a"))

# ---------------------------------------------------------------- sequential (nested) build-up
def add_level(prev_labels, new_col):
    """R2 of the finer grouping formed by combining what we already have with the new column."""
    if prev_labels is None:
        lab = new_col.astype(str)
    else:
        lab = pd.Series(prev_labels).astype(str).to_numpy() + "||" + new_col.astype(str).to_numpy()
    return lab

seq, prev, prev_r2 = [], None, 0.0
for name, col in [("District", G.district), ("+ Block within district", G.block),
                  ("+ Cluster within block", G.cluster)]:
    prev = add_level(prev, col)
    r2, om, k = eta(prev)
    seq.append({"step": name, "n_groups": k, "cumulative_raw_pct": round(r2, 1),
                "incremental_raw_pct": round(r2 - prev_r2, 1),
                "cumulative_df_adjusted_pct": round(om, 1) if np.isfinite(om) else np.nan})
    prev_r2 = r2
seq.append({"step": "Remainder: the GP itself", "n_groups": N,
            "cumulative_raw_pct": 100.0, "incremental_raw_pct": round(100 - prev_r2, 1),
            "cumulative_df_adjusted_pct": np.nan})
Q = pd.DataFrame(seq)
Q.to_csv(os.path.join(TAB, "variance_gp_level_sequential.csv"), index=False)
print("\nBUILDING UP, ONE LEVEL AT A TIME (nested)")
print("   %-28s %8s %12s %12s" % ("step", "groups", "cumulative", "adds"))
for _, r in Q.iterrows():
    print("   %-28s %8d %11.1f%% %11.1f%%" % (r.step, r.n_groups, r.cumulative_raw_pct, r.incremental_raw_pct))

# ---------------------------------------------------------------- verdict on the stated inference
d_raw = R.loc[R.level == "District", "raw_pct_of_between_place_variance"].iat[0]
b_raw = R.loc[R.level == "Block", "raw_pct_of_between_place_variance"].iat[0]
c_raw = R.loc[R.level == "Cluster", "raw_pct_of_between_place_variance"].iat[0]
d_adj = R.loc[R.level == "District", "df_adjusted_pct"].iat[0]
b_adj = R.loc[R.level == "Block", "df_adjusted_pct"].iat[0]
c_adj = R.loc[R.level == "Cluster", "df_adjusted_pct"].iat[0]
inc_b = Q.loc[Q.step == "+ Block within district", "incremental_raw_pct"].iat[0]
inc_c = Q.loc[Q.step == "+ Cluster within block", "incremental_raw_pct"].iat[0]
inc_g = Q.loc[Q.step == "Remainder: the GP itself", "incremental_raw_pct"].iat[0]
print("\n" + "=" * 78)
print("TESTING THE STATED INFERENCE: 'variation comes more from districts and clusters")
print("than from blocks and GPs'")
print("=" * 78)
print("  raw, each level alone:      district %.1f%%  block %.1f%%  cluster %.1f%%" % (d_raw, b_raw, c_raw))
print("  df-adjusted, each alone:    district %.1f%%  block %.1f%%  cluster %.1f%%" % (d_adj, b_adj, c_adj))
print("  new information each adds:  block adds %.1f%%, cluster adds %.1f%%, GP itself %.1f%%"
      % (inc_b, inc_c, inc_g))
print()
print("  district beats block?          %s" % ("YES" if d_adj > b_adj else "NO"))
print("  cluster beats block (raw)?     %s" % ("YES" if c_raw > b_raw else "NO"))
print("  cluster beats block (adjusted)? %s" % ("YES" if c_adj > b_adj else "NO"))
print("  GP itself is the largest share? %s" % ("YES" if inc_g > max(d_raw, inc_b, inc_c) else "NO"))
print("=" * 78)

# ---------------------------------------------------------------- chart
plt.rcParams.update({"font.family": "DejaVu Sans", "axes.edgecolor": MUT, "text.color": INK,
                     "axes.labelcolor": INK, "xtick.color": MUT, "ytick.color": MUT})
fig, (ax, bx) = plt.subplots(1, 2, figsize=(13.8, 5.6), gridspec_kw={"width_ratios": [1.15, 1]})
lv = R.level.tolist(); x = np.arange(len(lv)); w = 0.38
ax.bar(x - w / 2, R.raw_pct_of_between_place_variance, w, color=GREY, label="Raw share", zorder=3)
ax.bar(x + w / 2, R.df_adjusted_pct.fillna(0), w, color=GREEN, label="After adjusting for group count", zorder=3)
for i, (a, b) in enumerate(zip(R.raw_pct_of_between_place_variance, R.df_adjusted_pct)):
    ax.annotate("%.0f%%" % a, (i - w / 2, a), xytext=(0, 4), textcoords="offset points", ha="center", fontsize=9, color=INK)
    if pd.notna(b):
        ax.annotate("%.0f%%" % b, (i + w / 2, b), xytext=(0, 4), textcoords="offset points",
                    ha="center", fontsize=9, fontweight="bold", color=GREEN)
ax.set_xticks(x); ax.set_xticklabels([l.replace(" (each its own group)", "\n(each its own group)") for l in lv], fontsize=9.5)
ax.set_ylabel("% of the differences between GP averages", fontsize=10.5)
ax.set_ylim(0, 108); ax.legend(frameon=False, fontsize=9.5, loc="upper left")
ax.set_title("Each level on its own", fontsize=13, fontweight="bold", loc="left", pad=12)
ax.text(0, 1.015, "Grey rewards having more groups. Green removes that advantage. Read the green bars.",
        transform=ax.transAxes, fontsize=9.5, color=MUT)
ax.grid(axis="y", color=GREY, lw=0.7); ax.set_axisbelow(True)
for s in ("top", "right"): ax.spines[s].set_visible(False)

steps = ["District", "Block\n(new info)", "Cluster\n(new info)", "The GP\nitself"]
vals = [Q.cumulative_raw_pct.iat[0], inc_b, inc_c, inc_g]
cols = [BLUE, GREY, GREY, GREEN]
bx.bar(range(4), vals, 0.6, color=cols, zorder=3)
for i, v in enumerate(vals):
    bx.annotate("%.0f%%" % v, (i, v), xytext=(0, 5), textcoords="offset points", ha="center",
                fontsize=11, fontweight="bold", color=INK)
bx.set_xticks(range(4)); bx.set_xticklabels(steps, fontsize=9.5)
bx.set_ylabel("% of the differences between GP averages", fontsize=10.5)
bx.set_ylim(0, max(vals) * 1.28)
bx.set_title("Splitting it up, level by level", fontsize=13, fontweight="bold", loc="left", pad=12)
bx.text(0, 1.015, "Each bar is the NEW information that level adds after the ones before it.",
        transform=bx.transAxes, fontsize=9.5, color=MUT)
bx.grid(axis="y", color=GREY, lw=0.7); bx.set_axisbelow(True)
for s in ("top", "right"): bx.spines[s].set_visible(False)

fig.suptitle("Where do the differences between places come from?", fontsize=14.5, fontweight="bold",
             color=INK, x=0.007, ha="left", y=0.985)
fig.text(0.007, 0.925, "Each Gram Panchayat collapsed to one average score, so school, household and child effects are removed before asking the question.",
         fontsize=10, color=MUT)
fig.text(0.007, 0.015,
         "Source: Akshara Foundation GP Maths Contest, %d Gram Panchayats with at least %d children, all years pooled. Built by src/variance_gp_level.py.\n"
         "1,718 GPs sit across more than one cluster, so each GP is assigned the cluster most of its children sat in."
         % (N, MIN_STUDENTS_PER_GP), fontsize=7.8, color=MUT)
fig.tight_layout(rect=[0, 0.06, 1, 0.90])
fig.savefig(os.path.join(FIG, "16_variance_gp_level.png"), dpi=200, facecolor="white")
print("\nwrote outputs/figures/16_variance_gp_level.png")
print("wrote outputs/tables/variance_gp_level.csv, variance_gp_level_sequential.csv")
