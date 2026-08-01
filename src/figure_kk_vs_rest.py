"""
Kalyana Karnataka against the rest of Karnataka: the UDISE+ input reality.

Standalone, reproducible: reads data/udise_csv/udise_ka_school_2024-25.csv and the
371J flag in external_data/karnataka_district_crosswalk.csv. No manual numbers.

The learning gap is only half the story. This is the other half: what the 7 Article 371J
districts actually have. Placed next to the score gap so a reader can see the deficit is
measured inputs, not effort.

Run from repo root:
    python src/figure_kk_vs_rest.py

Writes:
    outputs/figures/14_kk_vs_rest.png
    outputs/tables/kk_vs_rest_udise.csv
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
NAVY, GOLD, INK, MUT, GREY = "#123B6B", "#E0B01E", "#123B47", "#6B7C80", "#C9D4D6"

XW = pd.read_csv(os.path.join("external_data", "karnataka_district_crosswalk.csv"))
KK = set()
for _, r in XW[XW["is_371J_kalyana_karnataka"] == 1].iterrows():
    KK.add(str(r["current_name"]).strip().upper())
    for col in ("census2011_name", "nfhs5_name", "aser2024_name"):
        v = str(r.get(col, "")).strip().upper()
        if v and v != "NAN": KK.add(v)
    for a in str(r.get("alt_spellings", "")).split(";"):
        if a.strip(): KK.add(a.strip().upper())
print("Article 371J districts flagged in the crosswalk: %d name variants, %d districts"
      % (len(KK), int((XW["is_371J_kalyana_karnataka"] == 1).sum())))

d = pd.read_csv(os.path.join("data", "udise_csv", "udise_ka_school_2024-25.csv"), low_memory=False)
d["dist_u"] = d["district"].astype(str).str.strip().str.upper()
# UDISE educational districts carry a suffix (e.g. KALBURGI, YADAGIRI); match on the leading token too
d["kk"] = d["dist_u"].apply(lambda s: any(s == k or s.startswith(k + " ") for k in KK))
d["rural"] = d["rural_urban"].astype(str).str.strip().str.lower().eq("rural")
d["govt"] = d["management_group"].astype(str).str.strip().eq("State Government")
print("matched KK schools: %d of %d rows | KK districts seen: %s"
      % (int(d.kk.sum()), len(d), sorted(set(d[d.kk]["dist_u"]))))

num = lambda c: pd.to_numeric(d[c], errors="coerce").astype("float64")   # cast before arithmetic
yes = lambda c: d[c].astype(str).str.strip().str.lower().isin(["1", "yes", "y", "true"])

G = d[d.rural & d.govt].copy()                 # rural State Government: the contest's universe
ALLM = d[d.rural].copy()                       # rural, all managements: for the private-share metric
rows = []
def add(label, kk_val, rest_val, fmt, note):
    rows.append({"metric": label, "kalyana_karnataka": kk_val, "rest_of_karnataka": rest_val,
                 "format": fmt, "universe": note})

for lab, series, universe, fmt in [
    ("Pupil-Teacher Ratio", None, "rural State Govt", "{:.1f}"),
    ("Enrolment per school", None, "rural State Govt", "{:.0f}"),
    ("% schools with a library", "library_availability", "rural State Govt", "{:.1f}%"),
    ("% schools with internet", "internet", "rural State Govt", "{:.1f}%"),
]:
    if lab == "Pupil-Teacher Ratio":
        e = pd.to_numeric(G["total_enrolment"], errors="coerce").astype("float64")
        t = pd.to_numeric(G["total_tch"], errors="coerce").astype("float64")
        kk = float(e[G.kk].sum() / t[G.kk].sum()); rest = float(e[~G.kk].sum() / t[~G.kk].sum())
    elif lab == "Enrolment per school":
        e = pd.to_numeric(G["total_enrolment"], errors="coerce").astype("float64")
        kk = float(e[G.kk].mean()); rest = float(e[~G.kk].mean())
    else:
        v = G[series].astype(str).str.strip().str.lower().isin(["1", "yes", "y", "true"])
        kk = 100.0 * float(v[G.kk].mean()); rest = 100.0 * float(v[~G.kk].mean())
    add(lab, kk, rest, fmt, universe)

e_all = pd.to_numeric(ALLM["total_enrolment"], errors="coerce").astype("float64")
priv = ALLM["management_group"].astype(str).str.strip().eq("Private Unaided")
kk_p = 100.0 * e_all[ALLM.kk & priv].sum() / e_all[ALLM.kk].sum()
rest_p = 100.0 * e_all[~ALLM.kk & priv].sum() / e_all[~ALLM.kk].sum()
add("% enrolment in private unaided", float(kk_p), float(rest_p), "{:.1f}%", "rural, ALL managements")

T = pd.DataFrame(rows)
T["gap"] = T["kalyana_karnataka"] - T["rest_of_karnataka"]
T.to_csv(os.path.join(TAB, "kk_vs_rest_udise.csv"), index=False)
print("\nKALYANA KARNATAKA vs REST, UDISE+ 2024-25")
for _, r in T.iterrows():
    print("   %-32s KK %8s   rest %8s   (%s)" % (r["metric"], r["format"].format(r["kalyana_karnataka"]),
          r["format"].format(r["rest_of_karnataka"]), r["universe"]))

# ---------------------------------------------------------------- chart
plt.rcParams.update({"font.family": "DejaVu Sans", "axes.edgecolor": MUT, "text.color": INK,
                     "axes.labelcolor": INK, "xtick.color": MUT, "ytick.color": MUT})
fig, axes = plt.subplots(1, 5, figsize=(14.4, 4.5))
for k, (_, r) in enumerate(T.iterrows()):
    a = axes[k]
    vals = [r["kalyana_karnataka"], r["rest_of_karnataka"]]
    a.bar([0, 1], vals, 0.62, color=[NAVY, GOLD], zorder=3)
    for i, v in enumerate(vals):
        a.annotate(r["format"].format(v), (i, v), xytext=(0, 5), textcoords="offset points",
                   ha="center", fontsize=11, fontweight="bold", color=INK)
    a.set_xticks([0, 1]); a.set_xticklabels(["Kalyana\nKarnataka", "Rest of\nKarnataka"], fontsize=9)
    a.set_title(r["metric"].replace("% schools with a ", "% with ").replace("% schools with ", "% with ")
                           .replace("% enrolment in private unaided", "% enrolment,\nprivate unaided"),
                fontsize=11, fontweight="bold", color=INK, pad=10)
    a.set_ylim(0, max(vals) * 1.28)
    a.set_yticks([]); a.grid(axis="y", color=GREY, lw=0.7); a.set_axisbelow(True)
    for s in ("top", "right", "left"): a.spines[s].set_visible(False)
fig.suptitle("Kalyana Karnataka against the rest of Karnataka: the UDISE+ input reality, 2024-25",
             fontsize=14, fontweight="bold", color=INK, x=0.007, ha="left", y=0.985)
fig.text(0.007, 0.905, "More children per teacher, nearly twice the school size, less than half the internet. "
                       "The score gap has a supply side.", fontsize=10, color=MUT)
fig.text(0.007, 0.02,
         "Source: UDISE+ 2024-25 school records (data/udise_csv), 371J flag from external_data/karnataka_district_crosswalk.csv. Built by src/figure_kk_vs_rest.py.\n"
         "First four metrics: rural State Government schools, the contest's universe. Private-unaided share: rural schools, all managements.",
         fontsize=7.8, color=MUT)
fig.tight_layout(rect=[0, 0.075, 1, 0.88])
fig.savefig(os.path.join(FIG, "14_kk_vs_rest.png"), dpi=200, facecolor="white")
print("\nwrote outputs/figures/14_kk_vs_rest.png and outputs/tables/kk_vs_rest_udise.csv")
