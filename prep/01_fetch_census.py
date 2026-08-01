"""
Fetch Census 2011 Primary Census Abstract for Karnataka from data.gov.in
and write clean DISTRICT-level and CD-BLOCK-level covariate CSVs.

RUN THIS ONCE, ON FRIDAY, WITH INTERNET. It writes into external_data/.
After that the whole pipeline runs fully offline.

Usage (from the datathon2026 folder):
    python prep/01_fetch_census.py
"""
import json, os, sys, time, urllib.request, urllib.error, csv

API_KEY   = "579b464db66ec23bdd000001b20993086f6644587841961ffa44a078"
RESOURCE  = "6648c520-365c-4b1a-a7f1-e821de172c1d"
BASE      = "https://api.data.gov.in/resource/" + RESOURCE
PAGE      = 1000
HERE      = os.path.dirname(os.path.abspath(__file__))
OUTDIR    = os.path.join(HERE, "..", "external_data")

KEEP = [
    "district_code","district_name","cd_block_code","level","name","total_rural_urban",
    "no_of_households","total_population_person","total_population_male","total_population_female",
    "population_in_the_age_group_0_6_person",
    "scheduled_castes_population_person","scheduled_tribes_population_person",
    "literates_population_person","literates_population_male","literates_population_female",
    "total_worker_population_person","main_cultivator_population_person",
    "main_agricultural_labourers_population_person","marginal_worker_population_person",
]

def fetch(offset):
    url = "%s?api-key=%s&format=json&limit=%d&offset=%d" % (BASE, API_KEY, PAGE, offset)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=90) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            print("   retry %d after error: %s" % (attempt + 1, e))
            time.sleep(3 * (attempt + 1))
    raise SystemExit("FAILED to fetch offset %d. Check internet / API key." % offset)

def main():
    os.makedirs(OUTDIR, exist_ok=True)
    print("Fetching Karnataka Census 2011 PCA from data.gov.in ...")
    first = fetch(0)
    total = int(first.get("total", 0))
    print("   total records reported: %d" % total)
    rows, offset = list(first.get("records", [])), PAGE
    while offset < total:
        print("   ... %d / %d" % (offset, total))
        rows.extend(fetch(offset).get("records", []))
        offset += PAGE
    print("   pulled %d records" % len(rows))

    def norm(r):
        out = {}
        for k in KEEP:
            v = r.get(k, "")
            out[k] = "" if v is None else v
        return out

    def derive(r):
        def f(k):
            try: return float(r.get(k) or 0)
            except Exception: return 0.0
        pop, p06 = f("total_population_person"), f("population_in_the_age_group_0_6_person")
        den = pop - p06
        lit, litm, litf = f("literates_population_person"), f("literates_population_male"), f("literates_population_female")
        m, fm = f("total_population_male"), f("total_population_female")
        m06 = 0.0
        denm = m - m06
        r["literacy_rate_7plus"]        = round(100.0 * lit / den, 2) if den > 0 else ""
        r["female_literacy_share"]      = round(100.0 * litf / lit, 2) if lit > 0 else ""
        r["male_female_literacy_gap_pp"]= round(100.0*(litm-litf)/max(lit,1), 2) if lit > 0 else ""
        r["sex_ratio"]                  = round(1000.0 * fm / m, 1) if m > 0 else ""
        r["sc_pct"]                     = round(100.0 * f("scheduled_castes_population_person") / pop, 2) if pop > 0 else ""
        r["st_pct"]                     = round(100.0 * f("scheduled_tribes_population_person") / pop, 2) if pop > 0 else ""
        r["child_0_6_pct"]              = round(100.0 * p06 / pop, 2) if pop > 0 else ""
        r["work_participation_rate"]    = round(100.0 * f("total_worker_population_person") / pop, 2) if pop > 0 else ""
        r["agri_labour_share_of_workers"]= round(100.0*(f("main_agricultural_labourers_population_person")
                                            + f("main_cultivator_population_person"))
                                            / max(f("total_worker_population_person"),1), 2)
        r["marginal_worker_share"]      = round(100.0 * f("marginal_worker_population_person")
                                            / max(f("total_worker_population_person"),1), 2)
        return r

    derived_cols = ["literacy_rate_7plus","female_literacy_share","male_female_literacy_gap_pp",
                    "sex_ratio","sc_pct","st_pct","child_0_6_pct","work_participation_rate",
                    "agri_labour_share_of_workers","marginal_worker_share"]

    def write(level_value, filename):
        sel = [derive(norm(r)) for r in rows
               if str(r.get("level","")).strip().upper() == level_value
               and str(r.get("total_rural_urban","")).strip().lower() == "total"]
        path = os.path.join(OUTDIR, filename)
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=KEEP + derived_cols)
            w.writeheader()
            for r in sel: w.writerow(r)
        print("   wrote %-42s %d rows" % (filename, len(sel)))
        return len(sel)

    levels = sorted({str(r.get("level","")).strip().upper() for r in rows})
    print("   levels present in data: %s" % levels)
    n_d = write("DISTRICT",  "census2011_karnataka_district.csv")
    n_b = write("CD BLOCK",  "census2011_karnataka_block.csv")
    if n_d == 0 or n_b == 0:
        print("\n   WARNING: one of the levels came back empty. Levels seen above.")
        print("   Open the CSVs and check before relying on them.")
    print("\nDone. Census files are in external_data/.")

if __name__ == "__main__":
    main()
