"""
THE HEADLINE, BUILT FROM THE RAW FILES. Independent of the rest of the pipeline.

This script reads the 9 organiser CSVs in data/primary/ directly with pandas,
applies the official per-file competency map, and reproduces the grade 6
multiplicative collapse from scratch. It shares no code with run_all.py, so if
both agree the number is not an artefact of our loader.

Run from repo root:
    python src/figure_g6_collapse.py

Writes:
    outputs/figures/10_g6_collapse.png          the chart
    outputs/tables/g6_collapse_from_raw.csv     every number in the chart
    outputs/tables/g6_collapse_panel_gps.csv    the constant-GP panel figures

Reading the chart: red is the grade 6 multiplicative collapse, the thing that
got worse. Green is grade 4, which improved in the raw data. Dashed lines are
the same-GP panel, which is the honest comparison.
"""
import os, glob, re, sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, ".."))
os.chdir(ROOT)
FIG = os.path.join("outputs", "figures"); TAB = os.path.join("outputs", "tables")
os.makedirs(FIG, exist_ok=True); os.makedirs(TAB, exist_ok=True)

YEARS = ["2022-23", "2023-24", "2024-25"]
RED, GREEN, INK, MUT, GREY = "#B2182B", "#1B7837", "#123B47", "#6B7C80", "#C9D4D6"
MIN_PANEL_N = 10          # a GP must field this many G6 children in EVERY year to enter the panel

# ---------------------------------------------------------------- 1. read raw
cmap = pd.read_csv(os.path.join("external_data", "competency_map_by_file.csv"))
files = sorted(glob.glob(os.path.join("data", "primary", "std_grade*_20*.csv")))
if not files:
    sys.exit("No files matched data/primary/std_grade<G>_<YEAR>.csv. Put the organiser CSVs there.")

recs, panel_src = [], []
print("Reading raw files:")
for f in files:
    g, y = re.search(r"grade(\d)_(\d{4}-\d{2})", os.path.basename(f)).groups()
    g = int(g)
    df = pd.read_csv(f, low_memory=False)
    items = [c for c in df.columns if re.fullmatch(r"Q\d+", str(c))]
    A = df[items].apply(pd.to_numeric, errors="coerce").to_numpy(dtype="float32")
    A[(A != 0) & (A != 1)] = np.nan                      # only 0/1 responses count
    mp = cmap[(cmap.grade == g) & (cmap.year == y)]
    if mp.empty:
        sys.exit("No competency map for grade %d %s" % (g, y))
    item2comp = dict(zip(mp["item"], mp["competency"]))

    row = {"grade": g, "year": y, "n_students": len(df), "n_items": len(items)}
    for comp in sorted(set(item2comp.values())):
        cols = [items.index(q) for q, c in item2comp.items() if c == comp and q in items]
        if cols:
            row[comp] = float(np.nanmean(A[:, cols])) * 100.0
    row["overall_pct"] = float(np.nanmean(A)) * 100.0
    recs.append(row)
    print("   %s  grade %d  %s  %7d students  %2d items" % (os.path.basename(f), g, y, len(df), len(items)))

    if g == 6:                                            # keep GP-level detail for the panel
        for comp in ("multiplication", "division"):
            cols = [items.index(q) for q, c in item2comp.items() if c == comp and q in items]
            if cols:
                df["_" + comp] = np.nanmean(A[:, cols], axis=1) * 100.0
        keep = ["GP_ID", "year"] if "year" in df.columns else ["GP_ID"]
        sub = df[["GP_ID"] + [c for c in ("_multiplication", "_division") if c in df.columns]].copy()
        sub["year"] = y
        panel_src.append(sub)
    del df, A

raw = pd.DataFrame(recs).sort_values(["grade", "year"]).reset_index(drop=True)

# ---------------------------------------------------------------- 2. constant-GP panel
p = pd.concat(panel_src, ignore_index=True)
gp = (p.groupby(["GP_ID", "year"])
        .agg(n=("_multiplication", "size"),
             mult=("_multiplication", "mean"),
             div=("_division", "mean")).reset_index())
elig = gp[gp.n >= MIN_PANEL_N]
keep_ids = elig.groupby("GP_ID")["year"].nunique()
keep_ids = keep_ids[keep_ids == len(YEARS)].index
panel = elig[elig.GP_ID.isin(keep_ids)]

def wavg(d, col):
    return float(np.average(d[col], weights=d["n"]))
pan = pd.DataFrame([{"year": y,
                     "n_gps": int(panel[panel.year == y].GP_ID.nunique()),
                     "n_students": int(panel[panel.year == y].n.sum()),
                     "mult": wavg(panel[panel.year == y], "mult"),
                     "div":  wavg(panel[panel.year == y], "div")} for y in YEARS])

g6 = raw[raw.grade == 6].set_index("year")
g4 = raw[raw.grade == 4].set_index("year")
g5 = raw[raw.grade == 5].set_index("year")
pn = pan.set_index("year")

print("\nGRADE 6, ALL CHILDREN WHO SAT THE TEST (raw):")
print("   multiplication  %.1f -> %.1f -> %.1f   (%+.1fpp)" % (g6.loc[YEARS[0],"multiplication"], g6.loc[YEARS[1],"multiplication"], g6.loc[YEARS[2],"multiplication"], g6.loc[YEARS[2],"multiplication"]-g6.loc[YEARS[0],"multiplication"]))
print("   division        %.1f -> %.1f -> %.1f   (%+.1fpp)" % (g6.loc[YEARS[0],"division"], g6.loc[YEARS[1],"division"], g6.loc[YEARS[2],"division"], g6.loc[YEARS[2],"division"]-g6.loc[YEARS[0],"division"]))
print("GRADE 6, SAME %d GRAM PANCHAYATS EVERY YEAR (panel):" % pn.loc[YEARS[0],"n_gps"])
print("   multiplication  %.1f -> %.1f -> %.1f   (%+.1fpp)" % (pn.loc[YEARS[0],"mult"], pn.loc[YEARS[1],"mult"], pn.loc[YEARS[2],"mult"], pn.loc[YEARS[2],"mult"]-pn.loc[YEARS[0],"mult"]))
print("   division        %.1f -> %.1f -> %.1f   (%+.1fpp)" % (pn.loc[YEARS[0],"div"], pn.loc[YEARS[1],"div"], pn.loc[YEARS[2],"div"], pn.loc[YEARS[2],"div"]-pn.loc[YEARS[0],"div"]))
print("GRADE 4 division (the apparent good news):  %.1f -> %.1f  (%+.1fpp)"
      % (g4.loc[YEARS[0],"division"], g4.loc[YEARS[2],"division"], g4.loc[YEARS[2],"division"]-g4.loc[YEARS[0],"division"]))

raw.to_csv(os.path.join(TAB, "g6_collapse_from_raw.csv"), index=False)
pan.to_csv(os.path.join(TAB, "g6_collapse_panel_gps.csv"), index=False)

# ---------------------------------------------------------------- 3. chart
plt.rcParams.update({"font.family": "DejaVu Sans", "axes.edgecolor": MUT, "text.color": INK,
                     "axes.labelcolor": INK, "xtick.color": MUT, "ytick.color": MUT})
fig, (ax, bx) = plt.subplots(1, 2, figsize=(13.2, 5.6), gridspec_kw={"width_ratios": [1.35, 1]})
x = np.arange(3)

# -- left: the collapse, raw and panel
pkey = {"multiplication": "mult", "division": "div"}
VOFF = {"division": 12, "multiplication": -19}          # keep the two series' labels apart
for col, lab in (("division", "Division"), ("multiplication", "Multiplication")):
    ax.plot(x, g6[col].reindex(YEARS).values, "-o", color=RED, lw=2.6, ms=8,
            markerfacecolor="white", markeredgewidth=2.2, zorder=3)
    ax.plot(x, pn[pkey[col]].reindex(YEARS).values, "--s", color=RED, lw=1.7, ms=6, alpha=0.5, zorder=2)
    for i, y in enumerate(YEARS):                        # value label on every point
        ax.annotate("%.1f" % g6.loc[y, col], (i, g6.loc[y, col]), xytext=(0, VOFF[col]),
                    textcoords="offset points", ha="center", fontsize=10, color=INK, fontweight="bold")
    # series name parked to the right of the last point, clear of the lines
    ax.annotate("%s\n%+.1fpp" % (lab, g6.loc[YEARS[2], col] - g6.loc[YEARS[0], col]),
                (x[2], g6.loc[YEARS[2], col]), xytext=(14, 14 if col == "division" else -20),
                textcoords="offset points", ha="left", va="center", fontsize=11,
                color=RED, fontweight="bold")

ax.plot([], [], "-o", color=RED, lw=2.6, markerfacecolor="white", markeredgewidth=2.2,
        label="All grade 6 children who sat the test")
ax.plot([], [], "--s", color=RED, lw=1.7, alpha=0.5,
        label="Same %s Gram Panchayats in all 3 years" % f"{pn.loc[YEARS[0],'n_gps']:,}")
ax.legend(loc="lower left", frameon=False, fontsize=9.5)
ax.set_xticks(x); ax.set_xticklabels(YEARS, fontsize=11)
ax.set_xlim(-0.22, 2.62)
ax.set_ylim(25, 60); ax.set_ylabel("% of items correct", fontsize=10.5)
ax.set_title("Grade 6 multiplicative reasoning collapsed", fontsize=13.5, fontweight="bold", loc="left", pad=14)
ax.text(0, 1.015, "And it collapsed further inside the same places, so this is not new weaker schools joining",
        transform=ax.transAxes, fontsize=10, color=MUT)
ax.grid(axis="y", color=GREY, lw=0.7); ax.set_axisbelow(True)
for s in ("top", "right"): ax.spines[s].set_visible(False)

# -- right: the gradient inversion
w = 0.26
for k, (gd, tab, colr) in enumerate([(4, g4, GREEN), (5, g5, MUT), (6, g6, RED)]):
    vals = tab["overall_pct"].reindex(YEARS).values
    bx.bar(x + (k - 1) * w, vals, w, color=colr, alpha=0.9 if gd != 5 else 0.55,
           label="Grade %d" % gd, zorder=3)
    for i, v in enumerate(vals):
        bx.annotate("%.0f" % v, (i + (k - 1) * w, v), xytext=(0, 3), textcoords="offset points",
                    ha="center", fontsize=8.5, color=INK)
bx.set_xticks(x); bx.set_xticklabels(YEARS, fontsize=11)
bx.set_ylim(0, 72); bx.set_ylabel("Mean % of items correct", fontsize=10.5)
bx.legend(frameon=False, fontsize=9.5, ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.02))
bx.set_title("The grade gradient flipped", fontsize=13.5, fontweight="bold", loc="left", pad=14)
bx.text(0, 1.015, "Older children used to score highest. By 2024-25 they scored lowest.",
        transform=bx.transAxes, fontsize=10, color=MUT)
bx.grid(axis="y", color=GREY, lw=0.7); bx.set_axisbelow(True)
for s in ("top", "right"): bx.spines[s].set_visible(False)

fig.text(0.008, 0.015,
         "Source: Akshara Foundation GP Maths Contest, %s student records, rural State Government schools, grades 4-6. "
         "Built directly from the 9 organiser CSVs by src/figure_g6_collapse.py.\n"
         "Items change each year within a constant competency framework, so comparison is at competency level, never item level. "
         "Panel = GPs fielding %d or more grade 6 children in every year, student-weighted."
         % (f"{int(raw.n_students.sum()):,}", MIN_PANEL_N),
         fontsize=7.8, color=MUT)
fig.tight_layout(rect=[0, 0.055, 1, 1])
out = os.path.join(FIG, "10_g6_collapse.png")
fig.savefig(out, dpi=200, facecolor="white")
print("\nwrote %s" % out)
print("wrote %s" % os.path.join(TAB, "g6_collapse_from_raw.csv"))
print("wrote %s" % os.path.join(TAB, "g6_collapse_panel_gps.csv"))
