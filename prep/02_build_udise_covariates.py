"""
Build Karnataka geography hierarchy + school-system covariates from the UDISE+ parquet store.

Produces, in external_data/:
  karnataka_geography_hierarchy.csv        State > Division > District > Block > Gram Panchayat
  udise_karnataka_gp_covariates.csv        one row per district|block|GP per year
  udise_karnataka_block_covariates.csv     one row per district|block per year
  udise_karnataka_district_covariates.csv  one row per district per year

The outputs are already committed to external_data/, so you do NOT need to run this at the
event. It is here for reproducibility and in case you want to change the metric definitions.

UDISE_ROOT below must point at the folder containing school_yearly/.
"""
import os, sys
import numpy as np, pandas as pd
import pyarrow.parquet as pq

UDISE_ROOT = os.environ.get("UDISE_ROOT", r"C:\Users\CSF\Claude CoWork Folder\1. Ed Sector Updates\K-12 School Education Data & Insights\UDISE_Data")
YEARS  = ["2022-23", "2023-24", "2024-25"]
HERE   = os.path.dirname(os.path.abspath(__file__))
OUTDIR = os.path.join(HERE, "..", "external_data")

COLS = ["state","district","block","lgd_block_name","lgd_vill_panchayat_name","lgd_vill_name",
        "rural_urban","management_group","lowclass","highclass","total_enrolment","total_tch",
        "female","graduate","post_graduate_and_above","electricity_availability",
        "library_availability","playground_available","tap_fun_yn","internet","comp_ict_lab_yn",
        "pre_primary","total_girls_func_toilet","classrooms_in_good_condition","avg_instr_days",
        "acad_inspections","crc_coordinator","smc_smdc_meetings","medium_of_instr1",
        "reading_corner","furniture_availability","availability_ramps","handwash_facility_for_meal"]

GOVT = {"State Government","Govt. Aided","Central Government"}
YES  = lambda s: (s.astype(str).str.strip().str.lower() == "yes")


def load_year(y):
    p = os.path.join(UDISE_ROOT, "school_yearly", "academic_year=%s" % y, "data.parquet")
    if not os.path.exists(p):
        print("   MISSING %s" % p); return None
    avail = set(pq.ParquetFile(p).schema_arrow.names)
    use   = [c for c in COLS if c in avail]
    df = pq.read_table(p, columns=use, filters=[("state", "=", "KARNATAKA")]).to_pandas()
    df["academic_year"] = y
    for c in COLS:
        if c not in df.columns: df[c] = np.nan
    return df


def prep(df):
    for c in ["district","block","lgd_block_name","lgd_vill_panchayat_name","lgd_vill_name"]:
        df[c] = df[c].astype(str).str.strip().str.upper().replace({"NONE": np.nan, "NAN": np.nan, "": np.nan})
    num = ["lowclass","highclass","total_enrolment","total_tch","female","graduate",
           "post_graduate_and_above","total_girls_func_toilet","classrooms_in_good_condition",
           "avg_instr_days","acad_inspections","crc_coordinator","smc_smdc_meetings"]
    for c in num:
        # CRITICAL: UDISE stores counts as int16. Any later "100 * sum" overflows and
        # wraps to negative numbers. Force float64 before any arithmetic touches these.
        df[c] = pd.to_numeric(df[c], errors="coerce").astype("float64")
    # schools that actually serve at least one of grades 4, 5, 6
    df["serves_4_6"] = (df["lowclass"].fillna(99) <= 6) & (df["highclass"].fillna(-1) >= 4)
    df["is_govt"]    = df["management_group"].isin(GOVT)
    df["is_private"] = df["management_group"].eq("Private Unaided")
    df["is_rural"]   = df["rural_urban"].astype(str).str.strip().str.lower().eq("rural")
    df["elec_ok"]    = YES(df["electricity_availability"])
    df["lib"]        = YES(df["library_availability"])
    df["play"]       = YES(df["playground_available"])
    df["tap"]        = YES(df["tap_fun_yn"])
    df["net"]        = YES(df["internet"])
    df["complab"]    = YES(df["comp_ict_lab_yn"])
    df["ramps"]      = YES(df["availability_ramps"])
    df["readcorner"] = YES(df["reading_corner"])
    df["handwash"]   = YES(df["handwash_facility_for_meal"])
    pp = df["pre_primary"].astype(str).str.strip().str.lower()
    df["preprim"]    = np.where(pp.eq("9"), np.nan, pp.eq("yes").astype(float))
    df["kannada"]    = df["medium_of_instr1"].astype(str).str.strip().str.lower().str.contains("kannada")
    df["instr_days"] = df["avg_instr_days"].where(df["avg_instr_days"] > 0)
    df["tch_grad_plus"] = df["graduate"].fillna(0) + df["post_graduate_and_above"].fillna(0)
    return df


def aggregate(df, keys, label):
    g46 = df[df["serves_4_6"]]
    gv  = g46[g46["is_govt"]]

    def pct(frame, col):
        return frame.groupby(keys, dropna=False)[col].mean().mul(100).round(2)

    out = pd.DataFrame(index=g46.groupby(keys, dropna=False).size().index)
    out["n_schools_4_6"]      = g46.groupby(keys, dropna=False).size()
    out["n_schools_govt"]     = gv.groupby(keys, dropna=False).size().reindex(out.index).fillna(0).astype(int)
    out["pct_govt_schools"]   = pct(g46, "is_govt")
    out["pct_private_schools"]= pct(g46, "is_private")
    out["pct_rural_schools"]  = pct(g46, "is_rural")
    out["enrolment_all"]      = g46.groupby(keys, dropna=False)["total_enrolment"].sum(min_count=1)
    out["enrolment_govt"]     = gv.groupby(keys, dropna=False)["total_enrolment"].sum(min_count=1).reindex(out.index)
    out["teachers_govt"]      = gv.groupby(keys, dropna=False)["total_tch"].sum(min_count=1).reindex(out.index)
    out["ptr_govt"]           = (out["enrolment_govt"] / out["teachers_govt"].replace(0, np.nan)).round(2)
    fem = gv.groupby(keys, dropna=False)["female"].sum(min_count=1).reindex(out.index)
    out["pct_female_teachers_govt"] = (100 * fem / out["teachers_govt"].replace(0, np.nan)).round(2)
    gpl = gv.groupby(keys, dropna=False)["tch_grad_plus"].sum(min_count=1).reindex(out.index)
    out["pct_teachers_graduate_plus_govt"] = (100 * gpl / out["teachers_govt"].replace(0, np.nan)).round(2)
    for col, name in [("elec_ok","pct_sch_electricity"),("lib","pct_sch_library"),
                      ("play","pct_sch_playground"),("tap","pct_sch_tapwater_functional"),
                      ("net","pct_sch_internet"),("complab","pct_sch_computer_lab"),
                      ("ramps","pct_sch_ramps"),("readcorner","pct_sch_reading_corner"),
                      ("handwash","pct_sch_handwash_meal"),("kannada","pct_sch_kannada_medium")]:
        out[name + "_govt"] = pct(gv, col).reindex(out.index)
    out["pct_sch_preprimary_govt"] = gv.groupby(keys, dropna=False)["preprim"].mean().mul(100).round(2).reindex(out.index)
    for col, name in [("total_girls_func_toilet","girls_func_toilets_per_school"),
                      ("classrooms_in_good_condition","good_classrooms_per_school"),
                      ("acad_inspections","acad_inspections_per_school"),
                      ("crc_coordinator","crc_coordinators_per_school"),
                      ("smc_smdc_meetings","smc_meetings_per_school"),
                      ("instr_days","mean_instruction_days")]:
        out[name + "_govt"] = gv.groupby(keys, dropna=False)[col].mean().round(2).reindex(out.index)
    out["avg_govt_school_size"] = (out["enrolment_govt"] / out["n_schools_govt"].replace(0, np.nan)).round(1)
    out = out.reset_index()
    print("   %-10s -> %6d rows, %d cols" % (label, len(out), out.shape[1]))
    return out


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    frames = []
    for y in YEARS:
        print("Loading %s ..." % y)
        d = load_year(y)
        if d is not None: frames.append(prep(d))
    if not frames:
        sys.exit("No UDISE years loaded. Check UDISE_ROOT.")
    df = pd.concat(frames, ignore_index=True)
    print("Karnataka school-years loaded: %d" % len(df))

    xw = pd.read_csv(os.path.join(OUTDIR, "pgid_2025_26_karnataka.csv"))
    ed2rev = dict(zip(xw["pgid_educational_district"].str.upper().str.strip(),
                      xw["maps_to_district"].str.strip()))
    cw = pd.read_csv(os.path.join(OUTDIR, "karnataka_district_crosswalk.csv"))
    rev2div = dict(zip(cw["current_name"].str.strip(), cw["revenue_division"].str.strip()))

    def attach(frame):
        frame.insert(0, "state", "KARNATAKA")
        frame["revenue_district"] = frame["district"].map(ed2rev)
        frame["division"] = frame["revenue_district"].map(rev2div)
        return frame

    gp  = attach(aggregate(df, ["academic_year","district","block","lgd_vill_panchayat_name"], "GP"))
    gp  = gp.rename(columns={"lgd_vill_panchayat_name": "gram_panchayat"})
    blk = attach(aggregate(df, ["academic_year","district","block"], "BLOCK"))
    dis = attach(aggregate(df, ["academic_year","district"], "DISTRICT"))

    lead = ["state","division","revenue_district","district","block","gram_panchayat","academic_year"]
    for frame in (gp, blk, dis):
        cols = [c for c in lead if c in frame.columns]
        frame_cols = cols + [c for c in frame.columns if c not in cols]
        frame.drop(columns=[c for c in frame.columns if c not in frame_cols], inplace=True, errors="ignore")

    gp  = gp[[c for c in lead if c in gp.columns]  + [c for c in gp.columns  if c not in lead]]
    blk = blk[[c for c in lead if c in blk.columns] + [c for c in blk.columns if c not in lead]]
    dis = dis[[c for c in lead if c in dis.columns] + [c for c in dis.columns if c not in lead]]

    latest = max(YEARS)
    hier = (gp[gp["academic_year"] == latest]
            [["state","division","revenue_district","district","block","gram_panchayat",
              "n_schools_4_6","n_schools_govt","enrolment_govt"]]
            .dropna(subset=["gram_panchayat"])
            .sort_values(["division","district","block","gram_panchayat"]))

    gp.to_csv(  os.path.join(OUTDIR, "udise_karnataka_gp_covariates.csv"),       index=False)
    blk.to_csv( os.path.join(OUTDIR, "udise_karnataka_block_covariates.csv"),    index=False)
    dis.to_csv( os.path.join(OUTDIR, "udise_karnataka_district_covariates.csv"), index=False)
    hier.to_csv(os.path.join(OUTDIR, "karnataka_geography_hierarchy.csv"),       index=False)
    print("\nHierarchy (%s): %d GP rows | %d districts | %d blocks | %d GPs" % (
        latest, len(hier), hier["district"].nunique(), hier["block"].nunique(),
        hier["gram_panchayat"].nunique()))
    print("Wrote 4 files to external_data/")

if __name__ == "__main__":
    main()
