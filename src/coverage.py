"""
Assessment coverage: students assessed vs UDISE+ enrolment, by district x grade x year.

The organisers describe the file as covering "all students assessed" - which is true, and
is not the same as covering all enrolled children. This module quantifies the difference.

THE CORRECT DENOMINATOR IS "rural". Confirmed by the organisers: the GP Maths Contest ran
in RURAL, STATE GOVERNMENT schools only (not urban, not aided, not private). Quote the
"rural" basis in every headline. The other two are kept only to show the choice was tested.
  rural   : State Government + rural  <-- THE UNIVERSE. Use this.
  strict  : State Government, rural and urban (too wide: includes urban schools never assessed)
  broad   : + Govt. Aided + Central Government (far too wide)

A grade-4 assessed count is compared with grade-4 enrolment in the same academic year.
"""
import glob, os
import numpy as np, pandas as pd
import config, external

GOVT_STRICT = {"State Government"}
GOVT_BROAD  = {"State Government", "Govt. Aided", "Central Government"}

def _udise_by_district_grade():
    rows = []
    for f in sorted(glob.glob(os.path.join(config.ROOT, "data", "udise_csv",
                                           "udise_ka_enrolment_by_grade_*.csv"))):
        year = os.path.basename(f).replace(".csv", "").split("_")[-1]
        d = pd.read_csv(f, low_memory=False)
        for g in (4, 5, 6):
            for c in ("c%d_b" % g, "c%d_g" % g):
                d[c] = pd.to_numeric(d[c], errors="coerce").fillna(0)
            d["g%d" % g] = d["c%d_b" % g] + d["c%d_g" % g]
        d["rural"] = d["rural_urban"].astype(str).str.strip().str.lower().eq("rural")
        for label, mgmt, rural_only in [("strict", GOVT_STRICT, False),
                                        ("broad",  GOVT_BROAD,  False),
                                        ("rural",  GOVT_STRICT, True)]:
            sel = d[d.management_group.isin(mgmt)]
            if rural_only:
                sel = sel[sel.rural]
            agg = sel.groupby("district")[["g4", "g5", "g6"]].sum().reset_index()
            agg = agg.melt(id_vars="district", var_name="grade", value_name="enrolled")
            agg["grade"] = agg["grade"].str[1].astype(int)
            agg["year"] = year; agg["basis"] = label
            rows.append(agg)
    return pd.concat(rows, ignore_index=True)

def build(df, alias):
    """df = student-level frame from loader. Returns (long, wide_strict, summary)."""
    a = (df.dropna(subset=["district", "grade"])
           .groupby(["district", "grade", "year"]).size().reset_index(name="assessed"))
    a["grade"] = a["grade"].astype(int)
    mu = external.match_districts(a["district"].unique(), alias, "district")
    a = a.merge(mu[["district", "canonical_district"]], on="district", how="left")

    u = _udise_by_district_grade()
    md = external.match_districts(u["district"].unique(), alias, "district")
    u = u.merge(md[["district", "canonical_district"]], on="district", how="left")
    u = (u.groupby(["canonical_district", "grade", "year", "basis"])["enrolled"]
           .sum().reset_index())

    # CRITICAL: the UDISE universe drives the denominator, not the assessed file.
    # A left join FROM the assessed side silently drops every district-grade-year that
    # had enrolled children but assessed nobody, which inflates coverage. Three coastal
    # districts skipped 2024-25 entirely, so that bias grows across the window.
    # Joining FROM the UDISE side and filling assessed=0 keeps non-participation visible.
    a_slim = (a.dropna(subset=["canonical_district"])
                .groupby(["canonical_district", "grade", "year"])["assessed"].sum().reset_index())
    m = u.merge(a_slim, on=["canonical_district", "grade", "year"], how="left")
    m["assessed"] = m["assessed"].fillna(0).astype("int64")
    m["coverage_pct"] = (100 * m["assessed"].astype(float) / m["enrolled"].replace(0, np.nan)).round(1)
    m = m[["canonical_district", "grade", "year", "basis", "assessed", "enrolled", "coverage_pct"]] \
          .sort_values(["basis", "canonical_district", "grade", "year"])

    strict = m[m.basis == "rural"]
    wide = strict.pivot_table(index="canonical_district", columns=["grade", "year"],
                              values="coverage_pct").round(1)
    wide["mean_coverage_pct"] = wide.mean(axis=1).round(1)
    wide = wide.sort_values("mean_coverage_pct")

    summ = []
    for b, g in m.groupby("basis"):
        tot_a, tot_e = g["assessed"].sum(), g["enrolled"].sum()
        summ.append({"basis": b, "assessed_total": int(tot_a), "enrolled_total": int(tot_e),
                     "state_coverage_pct": round(100 * tot_a / tot_e, 1),
                     "district_years_over_90pct": int((g["coverage_pct"] >= 90).sum()),
                     "district_years_under_50pct": int((g["coverage_pct"] < 50).sum()),
                     "n_district_years": int(g["coverage_pct"].notna().sum())})
    return m, wide.reset_index(), pd.DataFrame(summ)
