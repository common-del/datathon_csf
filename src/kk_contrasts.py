"""
kk_contrasts.py
Kalyana Karnataka against the rest of Karnataka, on learning outcomes first and inputs second.

Three independent instruments measure the same 31 districts. If all three put the seven Article
371J districts behind, the finding is about the region and not about one test. That is the whole
point of leading with outcomes: the input comparison only earns its place once the outcome gap
is established on more than our own data.

  1. Akshara GP Maths Contest   our own data, 3 years pooled, rural State Government schools
  2. ASER 2024                  share of Std 6-8 children who can do division, rural
  3. PARAKH RS 2024             grade 6 maths score, State Government schools

District names differ across the three files, so every join goes through the alt_spellings
column of the crosswalk rather than through exact string matching. Two real joins were failing
silently before this: PARAKH writes "Vijayanagar" and "Davangere", the crosswalk writes
"Vijayanagara" and "Davanagere".

Writes outputs/tables/kk_learning_outcomes.csv and kk_inputs.csv.
"""
import os, sys
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXT = os.path.join(ROOT, "external_data")
TAB = os.path.join(ROOT, "outputs", "tables")

XW = pd.read_csv(os.path.join(EXT, "karnataka_district_crosswalk.csv"))


def resolver():
    """Map every spelling the crosswalk knows about onto the 371J flag.

    Exact matching on current_name loses districts that other agencies spell differently, and
    a silent inner join then just drops them without saying so."""
    out = {}
    for r in XW.itertuples():
        names = {r.current_name, r.census2011_name, r.nfhs5_name, r.aser2024_name}
        if isinstance(r.alt_spellings, str):
            names |= set(r.alt_spellings.split(";"))
        for n in names:
            if isinstance(n, str) and n.strip():
                out[n.strip().lower()] = int(r.is_371J_kalyana_karnataka)
    return out


FLAG = resolver()
N_KK_TOTAL = int((XW["is_371J_kalyana_karnataka"] == 1).sum())


def split(df, name_col, value_col, label):
    """Mean value for the 371J districts and for everyone else, with the counts kept."""
    d = df.copy()
    d["kk"] = d[name_col].astype(str).str.strip().str.lower().map(FLAG)
    lost = sorted(d.loc[d.kk.isna(), name_col].astype(str))
    if lost:
        print("   %-24s unmatched, dropped: %s" % (label, ", ".join(lost)))
    d = d.dropna(subset=["kk", value_col])
    g = d.groupby("kk")[value_col].agg(["mean", "count"])
    return dict(kk_value=round(g.loc[1, "mean"], 1), rest_value=round(g.loc[0, "mean"], 1),
                gap_pp=round(g.loc[1, "mean"] - g.loc[0, "mean"], 1),
                n_kk=int(g.loc[1, "count"]), n_rest=int(g.loc[0, "count"]))


def learning_outcomes():
    rows = []

    # 1. our own data. District mean first, then averaged, so the three sources are compared
    #    the same way. ASER and PARAKH publish district figures with no enrolment weights, so
    #    a student-weighted contest figure would not be like for like.
    u = pd.read_csv(os.path.join(TAB, "unit_district_by_year.csv"))
    per = (u.groupby("district")
             .apply(lambda t: (t.pct_mean * t.n_students).sum() / t.n_students.sum(),
                    include_groups=False)
             .reset_index(name="pct"))
    rows.append(dict(source="GP Maths Contest", measure="Mean % of questions correct",
                     universe="rural State Government, classes 4-6, 3 years pooled",
                     **split(per, "district", "pct", "GP Maths Contest")))

    # 2. ASER 2024. Vijayanagara does not appear: ASER still reports on 2011 district
    #    boundaries and Vijayanagara was carved out of Ballari in 2021, so it is inside the
    #    Bellary figure. 6 of the 7 371J districts, and that is the correct number, not a bug.
    a = pd.read_csv(os.path.join(EXT, "aser2024_karnataka_districts.csv"))
    rows.append(dict(source="ASER 2024", measure="% of Std 6-8 who can do division",
                     universe="rural, all managements",
                     **split(a, "aser2024_name", "std6_8_division_pct", "ASER 2024")))

    # 3. PARAKH RS 2024, State Government schools, grade 6 maths: the closest published
    #    universe to ours.
    p = pd.read_csv(os.path.join(EXT, "prs2024_karnataka_maths.csv"))
    rows.append(dict(source="PARAKH RS 2024", measure="Grade 6 maths score",
                     universe="State Government schools",
                     **split(p, "prs_district", "prs24_state_govt_g6", "PARAKH RS 2024")))

    df = pd.DataFrame(rows)[["source", "measure", "universe", "kk_value", "rest_value",
                             "gap_pp", "n_kk", "n_rest"]]
    df.to_csv(os.path.join(TAB, "kk_learning_outcomes.csv"), index=False)
    return df


def inputs():
    """The UDISE input comparison, all five metrics.

    Library coverage and the private unaided share were dropped from an earlier version of the
    slide for space. Both belong: the library row is the one input where the gap is small, and
    the private share is the row that cuts the other way. Leaving them out made the comparison
    look more one-sided than the data is."""
    d = pd.read_csv(os.path.join(TAB, "kk_vs_rest_udise.csv"))
    order = ["Pupil-Teacher Ratio", "Enrolment per school", "% schools with internet",
             "% schools with a library", "% enrolment in private unaided"]
    short = {"Pupil-Teacher Ratio": "Children\nper teacher",
             "Enrolment per school": "Children\nper school",
             "% schools with internet": "Internet\nin school",
             "% schools with a library": "Library\nin school",
             "% enrolment in private unaided": "In private\nschool"}
    missing = [m for m in order if m not in set(d["metric"])]
    if missing:
        sys.exit("kk_vs_rest_udise.csv is missing: %s" % missing)
    d = d.set_index("metric").loc[order].reset_index()
    d["short_label"] = d["metric"].map(short)
    # the private-school row is context, not a deficit: it says government schools in Kalyana
    # Karnataka carry a larger share of all children, on fewer teachers
    d["kk_is_worse"] = [True, True, True, True, False]
    d.to_csv(os.path.join(TAB, "kk_inputs.csv"), index=False)
    return d


def main():
    print("Learning outcomes, Kalyana Karnataka against the rest\n")
    lo = learning_outcomes()
    for r in lo.itertuples():
        print("   %-18s KK %5.1f   rest %5.1f   gap %+5.1f   (%d vs %d districts)"
              % (r.source, r.kk_value, r.rest_value, r.gap_pp, r.n_kk, r.n_rest))
    if not (lo["gap_pp"] < 0).all():
        print("\n   NOTE: not all three instruments put Kalyana Karnataka behind. Check before "
              "claiming they agree.")
    else:
        print("\n   All %d instruments put Kalyana Karnataka behind." % len(lo))

    print("\nInputs, UDISE+ 2024-25\n")
    ip = inputs()
    for r in ip.itertuples():
        f = r.format
        print("   %-32s KK %-8s rest %-8s"
              % (r.metric, f.format(r.kalyana_karnataka), f.format(r.rest_of_karnataka)))
    print("\n-> outputs/tables/kk_learning_outcomes.csv, kk_inputs.csv")


if __name__ == "__main__":
    main()
