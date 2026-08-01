"""Regenerate the coverage tables with the corrected denominator, without a full re-run.

src/coverage.py previously joined FROM the assessed side, dropping every district-grade-year
that had enrolled children but assessed nobody. That inflated coverage. coverage.py is now
fixed; this script applies the same fix to the already-written tables so the rest of the
pipeline can be re-run from tables rather than from the full student load.

Validation: the corrected state totals must equal external_data/udise_rural_stategovt_g46_gender_district.csv,
which was independently cross-validated to the child. The script asserts this and refuses to
write if it fails.

Run from repo root: python src/fix_coverage.py
"""
import os, sys, glob
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE); os.chdir(ROOT)
import config, external, coverage as cov_mod

T = os.path.join("outputs", "tables")
YEARS = ["2022-23", "2023-24", "2024-25"]

old = pd.read_csv(os.path.join(T, "coverage_district_grade_year.csv"))
assessed = (old[old.basis == "rural"][["canonical_district", "grade", "year", "assessed"]]
              .drop_duplicates(["canonical_district", "grade", "year"]))
print("assessed rows carried over: %d | total assessed: %s"
      % (len(assessed), f"{int(assessed.assessed.sum()):,}"))

alias = external.build_alias_table()
u = cov_mod._udise_by_district_grade()
md = external.match_districts(u["district"].unique(), alias, "district")
u = u.merge(md[["district", "canonical_district"]], on="district", how="left")
u = (u.groupby(["canonical_district", "grade", "year", "basis"])["enrolled"].sum().reset_index())

m = u.merge(assessed, on=["canonical_district", "grade", "year"], how="left")
m["assessed"] = m["assessed"].fillna(0).astype("int64")
m["coverage_pct"] = (100 * m["assessed"].astype(float) / m["enrolled"].replace(0, np.nan)).round(1)
m = m[["canonical_district", "grade", "year", "basis", "assessed", "enrolled", "coverage_pct"]] \
      .sort_values(["basis", "canonical_district", "grade", "year"])

# ---- validation against the authoritative, independently cross-validated file
A = pd.read_csv(os.path.join("external_data", "udise_rural_stategovt_g46_gender_district.csv"))
r = m[m.basis == "rural"]
ok = True
for y in YEARS:
    want = int(A["%s Total" % y].sum()); got = int(r[r.year == y]["enrolled"].sum())
    flag = "OK " if want == got else "FAIL"
    if want != got: ok = False
    print("   %s  authoritative %s  computed %s  %s" % (y, f"{want:,}", f"{got:,}", flag))
if not ok:
    sys.exit("Denominator does not match the authoritative file. Nothing written.")

strict = r
wide = strict.pivot_table(index="canonical_district", columns=["grade", "year"], values="coverage_pct").round(1)
wide["mean_coverage_pct"] = wide.mean(axis=1).round(1)
wide = wide.sort_values("mean_coverage_pct").reset_index()

summ = []
for b, g in m.groupby("basis"):
    ta, te = g["assessed"].sum(), g["enrolled"].sum()
    summ.append({"basis": b, "assessed_total": int(ta), "enrolled_total": int(te),
                 "state_coverage_pct": round(100 * ta / te, 1),
                 "district_years_over_90pct": int((g["coverage_pct"] >= 90).sum()),
                 "district_years_under_50pct": int((g["coverage_pct"] < 50).sum()),
                 "n_district_years": int(g["coverage_pct"].notna().sum())})
summ = pd.DataFrame(summ)

m.to_csv(os.path.join(T, "coverage_district_grade_year.csv"), index=False)
wide.to_csv(os.path.join(T, "coverage_matrix_strict_stategovt.csv"), index=False)
summ.to_csv(os.path.join(T, "coverage_summary.csv"), index=False)

print("\nCORRECTED STATE COVERAGE (rural State Government basis):")
for y in YEARS:
    g = r[r.year == y]
    print("   %s  %s assessed / %s enrolled = %.1f%%"
          % (y, f"{int(g.assessed.sum()):,}", f"{int(g.enrolled.sum()):,}",
             100 * g.assessed.sum() / g.enrolled.sum()))
print("   ALL YEARS  %s / %s = %.1f%%"
      % (f"{int(r.assessed.sum()):,}", f"{int(r.enrolled.sum()):,}", 100 * r.assessed.sum() / r.enrolled.sum()))
print("\nrewrote coverage_district_grade_year.csv, coverage_matrix_strict_stategovt.csv, coverage_summary.csv")

# ---------------------------------------------------------------- gender table, same fix
GP = os.path.join(T, "coverage_rural_stategovt_gender.csv")
if os.path.exists(GP):
    gv = pd.read_csv(GP)
    ga = gv[["canonical_district", "Year", "g", "assessed"]].drop_duplicates(["canonical_district", "Year", "g"])
    # authoritative denominator, long form
    long = []
    # the authoritative file uses UDISE spellings; map them onto canonical names
    A2 = A.copy()
    amd = external.match_districts(A2["District"].astype(str).str.strip().unique(), alias, "district")
    A2 = A2.merge(amd[["district", "canonical_district"]],
                  left_on=A2["District"].astype(str).str.strip(), right_on="district", how="left")
    A2["canonical_district"] = A2["canonical_district"].fillna(A2["District"].astype(str).str.strip())
    for y in YEARS:
        for lab, col in (("boys", "%s Boys" % y), ("girls", "%s Girls" % y)):
            t = A2[["canonical_district", col]].rename(columns={col: "enrolled"})
            t["Year"] = y; t["g"] = lab
            long.append(t)
    den = pd.concat(long, ignore_index=True)
    den["enrolled"] = pd.to_numeric(den["enrolled"], errors="coerce").astype("float64").fillna(0)
    gm = den.merge(ga, on=["canonical_district", "Year", "g"], how="left")
    gm["assessed"] = gm["assessed"].fillna(0).astype("int64")
    gm["coverage_pct"] = (100 * gm["assessed"].astype(float) / gm["enrolled"].replace(0, np.nan)).round(1)
    gm = gm[["canonical_district", "Year", "g", "assessed", "enrolled", "coverage_pct"]]
    tot = gm.groupby("g").agg(a=("assessed", "sum"), e=("enrolled", "sum"))
    tot["cov"] = 100 * tot.a / tot.e
    if abs(int(tot["a"].sum()) - 1379087) > 5:
        sys.exit("Gender assessed total drifted (%d). Nothing written." % int(tot["a"].sum()))
    gm.to_csv(GP, index=False)
    print("\nCORRECTED GENDER COVERAGE:")
    for k in ("boys", "girls"):
        print("   %-6s %s assessed / %s enrolled = %.1f%%"
              % (k, f"{int(tot.loc[k,'a']):,}", f"{int(tot.loc[k,'e']):,}", tot.loc[k, "cov"]))
    print("   girls-minus-boys coverage gap: %+.1fpp" % (tot.loc["girls", "cov"] - tot.loc["boys", "cov"]))
    print("rewrote coverage_rural_stategovt_gender.csv")
