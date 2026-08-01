"""
Figures and tables for the restructured report, all built from the raw CSVs.

Standalone: reads data/primary/*.csv, data/udise_csv/*.csv and external_data/ only.
Shares no code with run_all.py.

Run from repo root:
    python src/figure_report_extras.py

Writes:
    outputs/figures/12_gender_grade_year.png      boys vs girls, by grade, by year
    outputs/figures/13_competency_spectrum.png    all 11 competencies, by grade, by year
    outputs/tables/participation_district.csv     coverage per district, all years
    outputs/tables/gender_grade_year.csv          mean score by gender x grade x year
    outputs/tables/competency_grade_year.csv      competency means by grade x year x gender
"""
import os, glob, re, sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE); os.chdir(ROOT)
FIG = os.path.join("outputs", "figures"); TAB = os.path.join("outputs", "tables")
os.makedirs(FIG, exist_ok=True); os.makedirs(TAB, exist_ok=True)

YEARS = ["2022-23", "2023-24", "2024-25"]
GRADES = [4, 5, 6]
GREEN, RED, INK, MUT, GREY, PALE = "#1B7837", "#B2182B", "#123B47", "#6B7C80", "#C9D4D6", "#E8EEEE"
BLUE = "#2C6E8F"
# green = better, white at the state benchmark, red = worse
DIVERGING = LinearSegmentedColormap.from_list(
    "csf", ["#B2182B", "#EF8A62", "#FDDBC7", "#FFFFFF", "#D9F0D3", "#7FBF7B", "#1B7837"])

CANON = ["number sense", "place value", "addition", "subtraction", "multiplication", "division",
         "fraction", "measurement", "mensuration", "shapes", "data handling"]

# ============================================================ 1. read raw, build aggregates
cmap = pd.read_csv(os.path.join("external_data", "competency_map_by_file.csv"))
rows_gen, rows_comp = [], []
print("Reading raw assessment files:")
for f in sorted(glob.glob(os.path.join("data", "primary", "std_grade*_20*.csv"))):
    g, y = re.search(r"grade(\d)_(\d{4}-\d{2})", os.path.basename(f)).groups(); g = int(g)
    d = pd.read_csv(f, low_memory=False)
    items = [c for c in d.columns if re.fullmatch(r"Q\d+", str(c))]
    A = d[items].apply(pd.to_numeric, errors="coerce").to_numpy(dtype="float32")
    if not A.flags.writeable: A = A.copy()   # newer numpy hands back a read-only view
    A[(A != 0) & (A != 1)] = np.nan
    gen = d["Gender"].astype(str).str.strip().str.upper().str[0].map({"F": "Girls", "M": "Boys", "G": "Girls", "B": "Boys"})
    mp = cmap[(cmap.grade == g) & (cmap.year == y)]
    i2c = dict(zip(mp["item"], mp["competency"]))

    overall = np.nanmean(A, axis=1) * 100.0
    for lab in ("Girls", "Boys"):
        sel = (gen == lab).to_numpy()
        if sel.sum():
            rows_gen.append({"grade": g, "year": y, "gender": lab, "n": int(sel.sum()),
                             "mean_pct": float(np.nanmean(overall[sel]))})
    rows_gen.append({"grade": g, "year": y, "gender": "All", "n": len(d),
                     "mean_pct": float(np.nanmean(overall))})
    for comp in sorted(set(i2c.values())):
        cols = [items.index(q) for q, c in i2c.items() if c == comp and q in items]
        if not cols: continue
        blk = A[:, cols]
        rec = {"grade": g, "year": y, "competency": comp, "n_items": len(cols),
               "pct_correct": float(np.nanmean(blk)) * 100.0}
        for lab in ("Girls", "Boys"):
            sel = (gen == lab).to_numpy()
            if sel.sum(): rec["pct_" + lab.lower()] = float(np.nanmean(blk[sel])) * 100.0
        rows_comp.append(rec)
    print("   %s  grade %d  %s  %7d students" % (os.path.basename(f), g, y, len(d)))
    del d, A

GEN = pd.DataFrame(rows_gen); COMP = pd.DataFrame(rows_comp)
GEN.to_csv(os.path.join(TAB, "gender_grade_year.csv"), index=False)
COMP.to_csv(os.path.join(TAB, "competency_grade_year.csv"), index=False)

gap = GEN.pivot_table(index=["grade", "year"], columns="gender", values="mean_pct").reset_index()
gap["gap_pp"] = gap["Girls"] - gap["Boys"]
print("\nGENDER GAP (girls minus boys), by grade and year:")
for _, r in gap.iterrows():
    print("   grade %d %s  girls %.1f  boys %.1f  gap %+.2fpp" % (r.grade, r.year, r.Girls, r.Boys, r.gap_pp))
print("   mean absolute gap across the 9 grade-years: %.2fpp | max %.2fpp" % (gap.gap_pp.abs().mean(), gap.gap_pp.abs().max()))

# ============================================================ 2. participation by district
def _udise_district():
    out = []
    for f in sorted(glob.glob(os.path.join("data", "udise_csv", "udise_ka_enrolment_by_grade_*.csv"))):
        year = os.path.basename(f).replace(".csv", "").split("_")[-1]
        d = pd.read_csv(f, low_memory=False)
        d = d[(d["management_group"].astype(str).str.strip() == "State Government") &
              (d["rural_urban"].astype(str).str.strip().str.lower() == "rural")]
        tot = None
        for g in GRADES:
            s = (pd.to_numeric(d["c%d_b" % g], errors="coerce").astype("float64").fillna(0) +
                 pd.to_numeric(d["c%d_g" % g], errors="coerce").astype("float64").fillna(0))
            tot = s if tot is None else tot + s
        t = tot.groupby(d["district"].astype(str).str.strip()).sum().reset_index()
        t.columns = ["district", "enrolled"]; t["year"] = year
        out.append(t)
    return pd.concat(out, ignore_index=True)

import external
alias = external.build_alias_table()
U = _udise_district()
mu = external.match_districts(U["district"].unique(), alias, "district")
U = U.merge(mu[["district", "canonical_district"]], on="district", how="left")
U = U.groupby("canonical_district")["enrolled"].sum().reset_index()

cov = pd.read_csv(os.path.join(TAB, "coverage_district_grade_year.csv"))
cov = cov[cov.basis == "rural"]
A = cov.groupby("canonical_district")["assessed"].sum().reset_index()
P = U.merge(A, on="canonical_district", how="left")
P["assessed"] = P["assessed"].fillna(0)
P["coverage_pct"] = (100 * P["assessed"] / P["enrolled"]).round(1)
P = P.sort_values("coverage_pct", ascending=False).reset_index(drop=True)
P["rank"] = range(1, len(P) + 1)
P.to_csv(os.path.join(TAB, "participation_district.csv"), index=False)
print("\nPARTICIPATION BY DISTRICT (all three years pooled), %d districts" % len(P))
print("   TOP 5:")
for _, r in P.head(5).iterrows():
    print("      %-20s %5.1f%%  (%s of %s)" % (r.canonical_district, r.coverage_pct, f"{int(r.assessed):,}", f"{int(r.enrolled):,}"))
print("   BOTTOM 5:")
for _, r in P.tail(5).iterrows():
    print("      %-20s %5.1f%%  (%s of %s)" % (r.canonical_district, r.coverage_pct, f"{int(r.assessed):,}", f"{int(r.enrolled):,}"))

# ============================================================ 3. FIGURE 12: gender
plt.rcParams.update({"font.family": "DejaVu Sans", "axes.edgecolor": MUT, "text.color": INK,
                     "axes.labelcolor": INK, "xtick.color": MUT, "ytick.color": MUT})
fig, (ax, bx) = plt.subplots(1, 2, figsize=(13.4, 5.4), gridspec_kw={"width_ratios": [1.55, 1]})
x = np.arange(3)
gp = GEN.pivot_table(index=["grade", "year"], columns="gender", values="mean_pct")
STY = {4: ("o", "-"), 5: ("s", "--"), 6: ("^", "-.")}
for g in GRADES:
    mk, ls = STY[g]
    ax.plot(x, [gp.loc[(g, y), "Girls"] for y in YEARS], ls + mk, color=RED, lw=2.2, ms=7,
            markerfacecolor="white", markeredgewidth=1.8, zorder=3)
    ax.plot(x, [gp.loc[(g, y), "Boys"] for y in YEARS], ls + mk, color=BLUE, lw=2.2, ms=7,
            markerfacecolor="white", markeredgewidth=1.8, zorder=3)
    ax.annotate("Grade %d" % g, (2, gp.loc[(6 if g == 6 else g, YEARS[2]), "Girls"]),
                xytext=(11, {4: 6, 5: 0, 6: -8}[g]), textcoords="offset points",
                fontsize=10, color=INK, fontweight="bold", va="center")
ax.plot([], [], "-", color=RED, lw=2.2, label="Girls")
ax.plot([], [], "-", color=BLUE, lw=2.2, label="Boys")
ax.legend(frameon=False, fontsize=10, loc="lower left")
ax.set_xticks(x); ax.set_xticklabels(YEARS, fontsize=11); ax.set_xlim(-0.15, 2.62)
ax.set_ylabel("Mean % of items correct", fontsize=10.5)
ax.set_title("Boys and girls move together", fontsize=13.5, fontweight="bold", loc="left", pad=14)
ax.text(0, 1.015, "Two lines per grade. They overlap so closely the grades separate, the genders do not.",
        transform=ax.transAxes, fontsize=10, color=MUT)
ax.grid(axis="y", color=GREY, lw=0.7); ax.set_axisbelow(True)
for s in ("top", "right"): ax.spines[s].set_visible(False)

gg = gap.copy()
lbl = ["G%d\n%s" % (r.grade, r.year[:5] + r.year[-2:]) for _, r in gg.iterrows()]
cols = [GREEN if v > 0 else RED for v in gg.gap_pp]
bx.barh(range(len(gg)), gg.gap_pp, color=cols, alpha=0.85, zorder=3)
bx.axvline(0, color=INK, lw=1.1, zorder=4)
bx.set_yticks(range(len(gg))); bx.set_yticklabels(lbl, fontsize=8)
bx.invert_yaxis()
for i, v in enumerate(gg.gap_pp):
    bx.annotate("%+.1f" % v, (v, i), xytext=(6 if v > 0 else -6, 0), textcoords="offset points",
                va="center", ha="left" if v > 0 else "right", fontsize=8.5, color=INK)
bx.set_xlim(-1.0, 5.0)
bx.set_xlabel("Girls minus boys (percentage points)", fontsize=10)
bx.set_title("The gap is small and always the same sign", fontsize=13, fontweight="bold", loc="left", pad=14)
bx.text(0, 1.015, "Every grade-year favours girls, by 1 to 4 points. Cohen's d = 0.07 overall.",
        transform=bx.transAxes, fontsize=9.5, color=MUT)
bx.grid(axis="x", color=GREY, lw=0.7); bx.set_axisbelow(True)
for s in ("top", "right", "left"): bx.spines[s].set_visible(False)
fig.text(0.008, 0.015,
         "Source: Akshara Foundation GP Maths Contest, 1,379,087 records, rural State Government schools. Built from the 9 organiser CSVs by src/figure_report_extras.py.\n"
         "Items change each year within a constant competency framework, so read the shape across years, not the point gains.", fontsize=7.8, color=MUT)
fig.tight_layout(rect=[0, 0.065, 1, 1])
fig.savefig(os.path.join(FIG, "12_gender_grade_year.png"), dpi=200, facecolor="white")
print("\nwrote outputs/figures/12_gender_grade_year.png")

# ============================================================ 4. FIGURE 13: competency spectrum
present = [c for c in CANON if c in set(COMP.competency)]
fig, axes = plt.subplots(1, 3, figsize=(14.6, 5.6), sharey=True)
vals = COMP.pivot_table(index="competency", columns=["grade", "year"], values="pct_correct")
allv = COMP.pct_correct
vmin, vcen, vmax = allv.min(), allv.mean(), allv.max()
for k, g in enumerate(GRADES):
    axg = axes[k]
    M = np.full((len(present), 3), np.nan)
    for i, c in enumerate(present):
        for j, y in enumerate(YEARS):
            s = COMP[(COMP.competency == c) & (COMP.grade == g) & (COMP.year == y)]
            if len(s): M[i, j] = s.pct_correct.iloc[0]
    im = axg.imshow(M, cmap=DIVERGING, vmin=vcen - 30, vmax=vcen + 30, aspect="auto")
    for i in range(len(present)):
        for j in range(3):
            if np.isfinite(M[i, j]):
                axg.text(j, i, "%.0f" % M[i, j], ha="center", va="center", fontsize=9,
                         color=INK, fontweight="bold")
            else:
                axg.text(j, i, "not\nasked", ha="center", va="center", fontsize=6.5, color=MUT, style="italic")
    axg.set_xticks(range(3)); axg.set_xticklabels(YEARS, fontsize=9.5, rotation=20)
    axg.set_title("Grade %d" % g, fontsize=12.5, fontweight="bold", color=INK, pad=8)
    axg.set_xticks(np.arange(-.5, 3, 1), minor=True)
    axg.set_yticks(np.arange(-.5, len(present), 1), minor=True)
    axg.grid(which="minor", color="white", lw=2.0); axg.tick_params(which="minor", length=0)
    for s in axg.spines.values(): s.set_visible(False)
axes[0].set_yticks(range(len(present)))
axes[0].set_yticklabels([c.title() for c in present], fontsize=10)
cax = fig.add_axes([0.945, 0.16, 0.012, 0.60])      # explicit axes: ax= steals width from the panels
cb = fig.colorbar(im, cax=cax)
cb.set_label("% of items correct (green better, red worse)", fontsize=9)
cb.ax.tick_params(labelsize=8)
cb.outline.set_visible(False)
fig.suptitle("Every competency, every grade, every year", fontsize=14.5, fontweight="bold",
             color=INK, x=0.008, ha="left", y=0.985)
fig.text(0.008, 0.925, "Grade 6 darkens from left to right. Grade 4 lightens. Fraction disappears after 2023-24; mensuration appears only once.",
         fontsize=10, color=MUT)
fig.text(0.008, 0.018,
         "Source: Akshara Foundation GP Maths Contest, official per-file competency map (external_data/competency_map_by_file.csv). Built by src/figure_report_extras.py.\n"
         "Blank cells are competencies not assessed in that grade-year. Only the 7 competencies present in all 9 files support cross-year claims.",
         fontsize=7.8, color=MUT)
fig.subplots_adjust(top=0.83, bottom=0.13, left=0.115, right=0.925)
fig.savefig(os.path.join(FIG, "13_competency_spectrum.png"), dpi=200, facecolor="white")
print("wrote outputs/figures/13_competency_spectrum.png")
print("wrote outputs/tables/participation_district.csv, gender_grade_year.csv, competency_grade_year.csv")
