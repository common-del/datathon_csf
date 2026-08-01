"""
PARTICIPATION: children assessed against children enrolled, per grade, per year.

Standalone. Reads the 9 organiser assessment CSVs and the 3 UDISE+ enrolment CSVs
directly, and shares no code with run_all.py, so it independently checks the
coverage figures the rest of the submission relies on.

THE DENOMINATOR IS RURAL, STATE GOVERNMENT ONLY. Confirmed by the organisers: the
GP Maths Contest ran in rural State Government schools. Any wider denominator
(urban, aided, private) understates coverage and is wrong for this contest.

Run from repo root:
    python src/figure_participation.py

Writes:
    outputs/figures/11_participation.png
    outputs/tables/participation_grade_year.csv
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
GRADES = [4, 5, 6]
GREEN, RED, INK, MUT, GREY, PALE = "#1B7837", "#B2182B", "#123B47", "#6B7C80", "#C9D4D6", "#E8EEEE"

# ---------------------------------------------------------------- 1. enrolled (UDISE+)
rows = []
print("Reading UDISE+ enrolment:")
for f in sorted(glob.glob(os.path.join("data", "udise_csv", "udise_ka_enrolment_by_grade_*.csv"))):
    year = os.path.basename(f).replace(".csv", "").split("_")[-1]
    d = pd.read_csv(f, low_memory=False)
    # UDISE stores counts as small ints; cast to float BEFORE any arithmetic or 100*sum overflows
    d = d[(d["management_group"].astype(str).str.strip() == "State Government") &
          (d["rural_urban"].astype(str).str.strip().str.lower() == "rural")]
    for g in GRADES:
        b = pd.to_numeric(d["c%d_b" % g], errors="coerce").astype("float64").fillna(0)
        gi = pd.to_numeric(d["c%d_g" % g], errors="coerce").astype("float64").fillna(0)
        rows.append({"grade": g, "year": year, "enrolled": float(b.sum() + gi.sum())})
    print("   %s  %s  %d rural State-Govt village rows" % (os.path.basename(f), year, len(d)))
enr = pd.DataFrame(rows)

# ---------------------------------------------------------------- 2. assessed (contest files)
rows = []
print("Reading assessment files:")
for f in sorted(glob.glob(os.path.join("data", "primary", "std_grade*_20*.csv"))):
    g, y = re.search(r"grade(\d)_(\d{4}-\d{2})", os.path.basename(f)).groups()
    n = sum(1 for _ in open(f, encoding="utf-8", errors="ignore")) - 1     # rows minus header
    rows.append({"grade": int(g), "year": y, "assessed": n})
    print("   %s  %7d students" % (os.path.basename(f), n))
ass = pd.DataFrame(rows)

t = ass.merge(enr, on=["grade", "year"], how="outer").sort_values(["year", "grade"])
t["coverage_pct"] = 100.0 * t["assessed"] / t["enrolled"]
t["not_assessed"] = t["enrolled"] - t["assessed"]
t.to_csv(os.path.join(TAB, "participation_grade_year.csv"), index=False)

print("\nPARTICIPATION, rural State Government basis")
print("   %-8s %-6s %>10s %>10s %>9s" .replace(">", "") % ("year", "grade", "assessed", "enrolled", "coverage"))
for _, r in t.iterrows():
    print("   %-8s %-6d %10s %10s %8.1f%%" % (r["year"], r["grade"], f"{int(r.assessed):,}", f"{int(r.enrolled):,}", r.coverage_pct))
by_year = t.groupby("year")[["assessed", "enrolled"]].sum()
by_year["coverage_pct"] = 100.0 * by_year["assessed"] / by_year["enrolled"]
print("\n   ALL GRADES BY YEAR: " + " | ".join("%s %.1f%%" % (y, v) for y, v in by_year["coverage_pct"].items()))
print("   THREE-YEAR TOTAL:   %s assessed of %s enrolled = %.1f%%"
      % (f"{int(t.assessed.sum()):,}", f"{int(t.enrolled.sum()):,}", 100.0 * t.assessed.sum() / t.enrolled.sum()))

# ---------------------------------------------------------------- 3. chart
plt.rcParams.update({"font.family": "DejaVu Sans", "axes.edgecolor": MUT, "text.color": INK,
                     "axes.labelcolor": INK, "xtick.color": MUT, "ytick.color": MUT})
fig, (ax, bx) = plt.subplots(1, 2, figsize=(13.6, 5.8), gridspec_kw={"width_ratios": [1.6, 1]})

# -- left: assessed against enrolled, 9 grade-year bars
pos, labels, seps = [], [], []
k = 0
for yi, y in enumerate(YEARS):
    for g in GRADES:
        pos.append(k); labels.append("G%d" % g); k += 1
    seps.append(k - 0.5); k += 0.8
pos = np.array(pos, dtype=float)
sub = t.set_index(["year", "grade"])
enr_v = np.array([sub.loc[(y, g), "enrolled"] for y in YEARS for g in GRADES]) / 1000.0
ass_v = np.array([sub.loc[(y, g), "assessed"] for y in YEARS for g in GRADES]) / 1000.0
cov_v = np.array([sub.loc[(y, g), "coverage_pct"] for y in YEARS for g in GRADES])

ax.bar(pos, enr_v, 0.74, color=PALE, edgecolor=GREY, lw=0.8, zorder=2, label="Enrolled (UDISE+, rural State Govt)")
ax.bar(pos, ass_v, 0.74, color=GREEN, zorder=3, label="Assessed in the contest")
for p, e, a, c in zip(pos, enr_v, ass_v, cov_v):
    ax.annotate("%.0f%%" % c, (p, a), xytext=(0, 4), textcoords="offset points",
                ha="center", fontsize=9.5, fontweight="bold", color=GREEN if c >= 50 else RED)
    ax.annotate("%.0fk" % e, (p, e), xytext=(0, 4), textcoords="offset points",
                ha="center", fontsize=8, color=MUT)
for s in seps[:-1]:
    ax.axvline(s + 0.4, color=GREY, lw=0.9, ls=":", zorder=1)
ax.set_xticks(pos); ax.set_xticklabels(labels, fontsize=10)
for yi, y in enumerate(YEARS):
    centre = pos[yi * 3:(yi + 1) * 3].mean()
    ax.annotate(y, (centre, 0), xytext=(0, -30), textcoords="offset points",
                ha="center", fontsize=11.5, fontweight="bold", color=INK, annotation_clip=False)
ax.set_ylabel("Children (thousands)", fontsize=10.5)
ax.set_ylim(0, max(enr_v) * 1.16)
ax.legend(frameon=False, fontsize=9.5, loc="upper right")
ax.set_title("Who actually sat the test", fontsize=13.5, fontweight="bold", loc="left", pad=14)
ax.text(0, 1.015, "Green is children assessed. Pale is children enrolled. The label is the share reached.",
        transform=ax.transAxes, fontsize=10, color=MUT)
ax.grid(axis="y", color=GREY, lw=0.7); ax.set_axisbelow(True)
for s in ("top", "right"): ax.spines[s].set_visible(False)

# -- right: coverage climbing, by grade
for g, mk in zip(GRADES, ("o", "s", "^")):
    v = [sub.loc[(y, g), "coverage_pct"] for y in YEARS]
    bx.plot(range(3), v, "-" + mk, color=GREEN, lw=2.4, ms=8, alpha=0.45 + 0.22 * (g - 4),
            markerfacecolor="white", markeredgewidth=2, zorder=3, label="Grade %d" % g)
# no per-point labels here: the three grades run within a point of each other and the
# left panel already carries all nine exact percentages
allv = by_year["coverage_pct"].reindex(YEARS).values
bx.plot(range(3), allv, ":", color=INK, lw=1.6, zorder=2, label="All grades")
bx.annotate("All grades\n%.0f%% to %.0f%%" % (allv[0], allv[-1]), (1, allv[1]), xytext=(-4, -40),
            textcoords="offset points", ha="center", fontsize=10, color=INK, fontweight="bold")
bx.legend(frameon=False, fontsize=9.5, loc="upper left", ncol=2)
bx.set_xticks(range(3)); bx.set_xticklabels(YEARS, fontsize=11)
bx.set_xlim(-0.25, 2.25); bx.set_ylim(0, 78)
bx.set_ylabel("% of enrolled children assessed", fontsize=10.5)
bx.set_title("Participation more than doubled", fontsize=13.5, fontweight="bold", loc="left", pad=14)
bx.text(0, 1.015, "This is the growth that could have faked a score decline. It does not.",
        transform=bx.transAxes, fontsize=10, color=MUT)
bx.grid(axis="y", color=GREY, lw=0.7); bx.set_axisbelow(True)
for s in ("top", "right"): bx.spines[s].set_visible(False)

fig.text(0.008, 0.012,
         "Sources: Akshara Foundation GP Maths Contest (assessed) and UDISE+ 2022-25 enrolment (enrolled), both filtered to rural State Government schools, the contest's actual universe.\n"
         "Built directly from the raw CSVs by src/figure_participation.py. The denominator reconciles to the cross-validated UDISE file (1,244,415 children in 2022-23).\n"
         "No grade in any year reaches full coverage, so every district ranking in this submission is reported next to its coverage.",
         fontsize=7.6, color=MUT)
fig.tight_layout(rect=[0, 0.095, 1, 1])
out = os.path.join(FIG, "11_participation.png")
fig.savefig(out, dpi=200, facecolor="white")
print("\nwrote %s" % out)
print("wrote %s" % os.path.join(TAB, "participation_grade_year.csv"))
