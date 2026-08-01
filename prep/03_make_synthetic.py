"""
Generate a REHEARSAL dataset that matches the announced schema of the Akshara file.

Purpose: let you run the entire pipeline end to end BEFORE the event, on your own laptop,
so that on Day 1 the only new thing is the real CSV.

Writes: data/primary/SYNTHETIC_rehearsal.csv

This is fake data. Never present any number from it. It exists only to prove the plumbing.
Real Karnataka geography is used (from the UDISE hierarchy) so the joins get exercised properly.
"""
import os, numpy as np, pandas as pd

SEED = 20260801
HERE = os.path.dirname(os.path.abspath(__file__))
EXT  = os.path.join(HERE, "..", "external_data")
OUT  = os.path.join(HERE, "..", "data", "primary", "SYNTHETIC_rehearsal.csv")
YEARS  = ["2022-23", "2023-24", "2024-25"]
GRADES = [4, 5, 6]
N_GP_SAMPLE      = 900     # how many GPs to include
STUDENTS_PER_CELL = 9      # per GP x year x grade  -> ~ 900*3*3*9 = 72,900 rows

# 10 competencies, 2 items each. Ordered easy -> hard, with a prerequisite chain.
COMPETENCIES = [
    ("C01", "Number recognition & place value", 0),
    ("C02", "Addition without carry",           1),
    ("C03", "Subtraction with borrowing",       2),
    ("C04", "Multiplication tables & facts",    3),
    ("C05", "Division (sharing & grouping)",    4),
    ("C06", "Fractions - identify & compare",   5),
    ("C07", "Measurement (length, weight)",     6),
    ("C08", "Time & money word problems",       7),
    ("C09", "Data handling & simple graphs",    8),
    ("C10", "Multi-step word problems",         9),
]

def main():
    rng = np.random.default_rng(SEED)
    hier = pd.read_csv(os.path.join(EXT, "karnataka_geography_hierarchy.csv"))
    hier = hier.dropna(subset=["gram_panchayat"]).copy()

    # sample GPs, keeping all divisions represented
    hier = hier.sample(n=min(N_GP_SAMPLE, len(hier)), random_state=SEED).reset_index(drop=True)

    # UDISE has no Cluster field, so invent clusters: ~5 GPs per cluster within a block
    hier = hier.sort_values(["district", "block", "gram_panchayat"]).reset_index(drop=True)
    hier["_i"] = hier.groupby(["district", "block"]).cumcount()
    hier["Cluster"] = (hier["block"].astype(str) + "-CL" +
                       (hier["_i"] // 5 + 1).astype(str).str.zfill(2))

    # district effect anchored to real teacher availability so cross-dataset joins find signal
    dis = pd.read_csv(os.path.join(EXT, "udise_karnataka_district_covariates.csv"))
    dis = dis[dis["academic_year"] == "2024-25"][["district", "ptr_govt"]]
    hier = hier.merge(dis, on="district", how="left")
    ptr = hier["ptr_govt"].fillna(hier["ptr_govt"].median())
    dis_eff = -0.9 * (ptr - ptr.mean()) / ptr.std()          # high PTR -> lower ability
    gp_eff  = rng.normal(0, 0.45, len(hier))                  # GP random effect
    hier["_ability"] = dis_eff.to_numpy() + gp_eff

    rows = []
    item_names = ["Q%d" % i for i in range(1, 21)]
    for yi, year in enumerate(YEARS):
        year_eff = 0.10 * yi                                  # slow improvement over time
        for grade in GRADES:
            grade_eff = 0.28 * (grade - 5)
            for _, gpr in hier.iterrows():
                n = STUDENTS_PER_CELL
                gender = rng.choice(["F", "M"], size=n, p=[0.49, 0.51])
                theta = (gpr["_ability"] + year_eff + grade_eff + rng.normal(0, 0.85, n))
                # girls slightly ahead on foundational, behind on higher-order
                is_f = (gender == "F").astype(float)
                block = {"Year": year, "Grade": grade,
                         "Division": gpr["division"], "District": gpr["district"],
                         "Block": gpr["block"], "Cluster": gpr["Cluster"],
                         "GP": gpr["gram_panchayat"], "Gender": gender}
                resp = {}
                for ci, (code, _label, rank) in enumerate(COMPETENCIES):
                    diff = -1.15 + 0.30 * rank                # item difficulty ladder
                    gender_shift = 0.14 - 0.032 * rank        # +ve early, -ve late
                    for k in (0, 1):
                        d = diff + (0.12 if k else -0.12)
                        p = 1.0 / (1.0 + np.exp(-(theta - d + gender_shift * is_f)))
                        resp["Q%d" % (2 * ci + k + 1)] = (rng.random(n) < p).astype(int)
                df = pd.DataFrame({**block, **resp})
                rows.append(df)

    out = pd.concat(rows, ignore_index=True)
    out["Score"] = out[item_names].sum(axis=1)
    cols = ["Year","Grade","Division","District","Block","Cluster","GP","Gender"] + item_names + ["Score"]
    out = out[cols]

    # inject the kind of mess a real file has, so the QA module has something to catch
    n = len(out)
    idx = rng.choice(n, size=int(0.004 * n), replace=False)
    out.loc[idx, "Gender"] = rng.choice(["f", "m", "Male", "Female", ""], size=len(idx))
    idx2 = rng.choice(n, size=int(0.002 * n), replace=False)
    out.loc[idx2, "Q7"] = np.nan
    dupes = out.sample(n=int(0.001 * n), random_state=SEED)

    out = pd.concat([out, dupes], ignore_index=True)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    out.to_csv(OUT, index=False)

    cmap = pd.DataFrame([{"item": "Q%d" % (2*i+k+1), "competency_code": c,
                          "competency_label": l, "difficulty_rank": r}
                         for i, (c, l, r) in enumerate(COMPETENCIES) for k in (0, 1)])
    cmap.to_csv(os.path.join(EXT, "SAMPLE_competency_map.csv"), index=False)

    print("Wrote %s" % OUT)
    print("  rows=%d  districts=%d  blocks=%d  clusters=%d  GPs=%d"
          % (len(out), out.District.nunique(), out.Block.nunique(),
             out.Cluster.nunique(), out.GP.nunique()))
    print("  mean score=%.2f / 20" % out.Score.mean())
    print("Wrote external_data/SAMPLE_competency_map.csv (template - replace with the real mapping)")

if __name__ == "__main__":
    main()
