"""
How the 11 competencies relate to each other, and to the total score.

Standalone and reproducible: reads data/primary/*.csv and the official competency map in
external_data/competency_map_by_file.csv. Shares no code with run_all.py.

Two things are computed at student level, pooled across all 9 files:
  1. correlation of each competency with TOTAL score (includes itself, so it is inflated)
  2. correlation of each competency with every other competency
Both matter: (1) says which competency best predicts the whole test, (2) says which skills
travel together.

Run from repo root:
    python src/figure_competency_correlation.py

Writes:
    outputs/figures/15_competency_correlation.png
    outputs/tables/competency_correlation_matrix.csv
    outputs/tables/competency_total_correlation.csv
"""
import os, glob, re, sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, ".."))
os.chdir(ROOT)
FIG = os.path.join("outputs", "figures"); TAB = os.path.join("outputs", "tables")
INK, MUT, GREY = "#123B47", "#6B7C80", "#C9D4D6"
SEQ = LinearSegmentedColormap.from_list("csf_seq", ["#FFFFFF", "#D9F0D3", "#7FBF7B", "#1B7837"])

ORDER = ["number sense", "place value", "addition", "subtraction", "multiplication", "division",
         "fraction", "measurement", "mensuration", "shapes", "data handling"]
SHORT = {"number sense": "Number Sense", "place value": "Place Value", "addition": "Addition",
         "subtraction": "Subtraction", "multiplication": "Multiplication", "division": "Division",
         "fraction": "Fractions", "measurement": "Measurement", "mensuration": "Mensuration",
         "shapes": "Shapes", "data handling": "Data Handling"}

cmap = pd.read_csv(os.path.join("external_data", "competency_map_by_file.csv"))
frames = []
print("Reading raw assessment files:")
for f in sorted(glob.glob(os.path.join("data", "primary", "std_grade*_20*.csv"))):
    g, y = re.search(r"grade(\d)_(\d{4}-\d{2})", os.path.basename(f)).groups(); g = int(g)
    d = pd.read_csv(f, low_memory=False)
    items = [c for c in d.columns if re.fullmatch(r"Q\d+", str(c))]
    A = d[items].apply(pd.to_numeric, errors="coerce").to_numpy(dtype="float32")
    if not A.flags.writeable: A = A.copy()   # newer numpy hands back a read-only view
    A[(A != 0) & (A != 1)] = np.nan
    i2c = dict(zip(cmap[(cmap.grade == g) & (cmap.year == y)]["item"],
                   cmap[(cmap.grade == g) & (cmap.year == y)]["competency"]))
    out = pd.DataFrame(index=range(len(d)))
    for comp in ORDER:
        cols = [items.index(q) for q, c in i2c.items() if c == comp and q in items]
        out[comp] = np.nanmean(A[:, cols], axis=1) if cols else np.nan
    out["TOTAL"] = np.nanmean(A, axis=1)
    frames.append(out.astype("float32"))
    print("   %s  grade %d  %s  %7d students" % (os.path.basename(f), g, y, len(d)))
    del d, A
S = pd.concat(frames, ignore_index=True); del frames
print("pooled student rows: %s" % f"{len(S):,}")

# ---- correlation with total score (part-whole overlap present, stated openly)
tot = []
for comp in ORDER:
    ok = S[comp].notna() & S["TOTAL"].notna()
    if ok.sum() < 1000: continue
    r = float(np.corrcoef(S.loc[ok, comp], S.loc[ok, "TOTAL"])[0, 1])
    tot.append({"competency": SHORT[comp], "r_with_total": round(r, 3), "n": int(ok.sum())})
T = pd.DataFrame(tot).sort_values("r_with_total", ascending=False)
T.to_csv(os.path.join(TAB, "competency_total_correlation.csv"), index=False)
print("\nCORRELATION WITH TOTAL SCORE (highest first):")
for _, r in T.iterrows(): print("   %-15s %.2f  (n=%s)" % (r.competency, r.r_with_total, f"{int(r.n):,}"))

# ---- competency x competency
M = pd.DataFrame(
    np.nan, index=ORDER, columns=ORDER, dtype="float64")
pairs = []
for i, a in enumerate(ORDER):
    for b in ORDER[i:]:
        ok = S[a].notna() & S[b].notna()
        if ok.sum() < 1000: continue
        r = 1.0 if a == b else float(np.corrcoef(S.loc[ok, a], S.loc[ok, b])[0, 1])
        M.loc[a, b] = M.loc[b, a] = round(r, 3)
        if a != b: pairs.append({"a": SHORT[a], "b": SHORT[b], "r": round(r, 3), "n": int(ok.sum())})
P = pd.DataFrame(pairs).sort_values("r", ascending=False)
M.rename(index=SHORT, columns=SHORT).to_csv(os.path.join(TAB, "competency_correlation_matrix.csv"))
print("\nSTRONGEST PAIRS:")
for _, r in P.head(5).iterrows(): print("   %-15s %-15s %.2f" % (r.a, r.b, r.r))
print("WEAKEST PAIRS:")
for _, r in P.tail(4).iterrows(): print("   %-15s %-15s %.2f" % (r.a, r.b, r.r))
und = [(SHORT[a], SHORT[b]) for i, a in enumerate(ORDER) for b in ORDER[i + 1:] if pd.isna(M.loc[a, b])]
print("undefined pairs (never co-occur for the same child):", und if und else "none")

# ---------------------------------------------------------------- chart
plt.rcParams.update({"font.family": "DejaVu Sans", "text.color": INK, "axes.labelcolor": INK,
                     "xtick.color": MUT, "ytick.color": MUT})
fig, (ax, bx) = plt.subplots(1, 2, figsize=(14.6, 6.4), gridspec_kw={"width_ratios": [1.42, 1]})
lab = [SHORT[c] for c in ORDER]
V = M.values.astype(float)
im = ax.imshow(V, cmap=SEQ, vmin=0.2, vmax=1.0)
for i in range(len(ORDER)):
    for j in range(len(ORDER)):
        if np.isfinite(V[i, j]):
            ax.text(j, i, "%.2f" % V[i, j], ha="center", va="center", fontsize=7.6,
                    color="white" if V[i, j] > 0.72 else INK,
                    fontweight="bold" if i == j else "normal")
        else:
            ax.text(j, i, "n/a", ha="center", va="center", fontsize=6.5, color=MUT, style="italic")
ax.set_xticks(range(len(ORDER))); ax.set_xticklabels(lab, rotation=42, ha="right", fontsize=8.5)
ax.set_yticks(range(len(ORDER))); ax.set_yticklabels(lab, fontsize=8.5)
ax.set_xticks(np.arange(-.5, len(ORDER), 1), minor=True)
ax.set_yticks(np.arange(-.5, len(ORDER), 1), minor=True)
ax.grid(which="minor", color="white", lw=1.6); ax.tick_params(which="minor", length=0)
for s in ax.spines.values(): s.set_visible(False)
ax.set_title("Which skills travel together", fontsize=13, fontweight="bold", color=INK, loc="left", pad=10)

T2 = T.sort_values("r_with_total")
bars = bx.barh(range(len(T2)), T2.r_with_total, color="#1B7837", alpha=0.88, zorder=3)
for i, v in enumerate(T2.r_with_total):
    bx.annotate("%.2f" % v, (v, i), xytext=(5, 0), textcoords="offset points", va="center",
                fontsize=9.5, fontweight="bold", color=INK)
bx.set_yticks(range(len(T2))); bx.set_yticklabels(T2.competency, fontsize=9.5)
bx.set_xlim(0, 0.92); bx.set_xlabel("Correlation with a child's total score", fontsize=10)
bx.grid(axis="x", color=GREY, lw=0.7); bx.set_axisbelow(True)
for s in ("top", "right", "left"): bx.spines[s].set_visible(False)
bx.set_title("Which skill tells you the most", fontsize=13, fontweight="bold", color=INK, loc="left", pad=10)
fig.suptitle("How the 11 skills relate to each other and to the whole test",
             fontsize=14.5, fontweight="bold", color=INK, x=0.007, ha="left", y=0.985)
fig.text(0.007, 0.928, "Darker means the two skills move together more closely. The bars show which single skill best predicts a child's overall score.",
         fontsize=10, color=MUT)
fig.text(0.007, 0.018,
         "Source: Akshara Foundation GP Maths Contest, %s student rows pooled across all 9 files, official competency map. Built by src/figure_competency_correlation.py.\n"
         "The bar chart includes each skill inside the total, so those numbers run higher than a like-for-like comparison would. Fractions and Mensuration never appear for the same child, so that one pair is undefined."
         % f"{len(S):,}", fontsize=7.8, color=MUT)
fig.tight_layout(rect=[0, 0.06, 1, 0.90])
fig.savefig(os.path.join(FIG, "15_competency_correlation.png"), dpi=200, facecolor="white")
print("\nwrote outputs/figures/15_competency_correlation.png")
print("wrote outputs/tables/competency_correlation_matrix.csv, competency_total_correlation.csv")
