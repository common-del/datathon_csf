"""
Run this FIRST, tonight. It tells you exactly what is missing and what to type.
It does not change anything on your machine.
"""
import importlib, os, platform, sys

NEED = [("pandas","pandas"),("numpy","numpy"),("scipy","scipy"),
        ("sklearn","scikit-learn"),("matplotlib","matplotlib"),("plotly","plotly"),
        ("openpyxl","openpyxl"),("pptx","python-pptx"),("pyarrow","pyarrow")]

def main():
    print("=" * 66)
    print("ENVIRONMENT CHECK")
    print("=" * 66)
    print("Python  : %s" % sys.version.split()[0])
    print("Location: %s" % sys.executable)
    print("OS      : %s %s" % (platform.system(), platform.release()))
    ok = True
    if sys.version_info < (3, 9):
        print("\n!! Python is too old. Install Python 3.11 or 3.12."); ok = False

    print("\nPackages")
    missing = []
    for mod, pipname in NEED:
        try:
            m = importlib.import_module(mod)
            v = getattr(m, "__version__", "?")
            print("  OK      %-14s %s" % (pipname, v))
        except Exception as e:
            print("  MISSING %-14s (%s)" % (pipname, type(e).__name__))
            missing.append(pipname)
    if missing:
        ok = False
        print("\nTo fix, copy this line into the same terminal and press Enter:")
        print("\n    python -m pip install " + " ".join(missing) + "\n")

    print("Folders")
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.abspath(os.path.join(here, ".."))
    for rel in ["data/primary","external_data","src","outputs","docs","playbook"]:
        p = os.path.join(root, rel)
        print("  %-16s %s" % (rel, "OK" if os.path.isdir(p) else "MISSING"))
        if not os.path.isdir(p):
            os.makedirs(p, exist_ok=True); print("                   created it")

    ext = os.path.join(root, "external_data")
    files = sorted(f for f in os.listdir(ext) if f.endswith(".csv")) if os.path.isdir(ext) else []
    print("\nExternal datasets present: %d" % len(files))
    for f in files:
        print("  - %s (%.0f KB)" % (f, os.path.getsize(os.path.join(ext, f)) / 1024))
    need = ["karnataka_district_crosswalk.csv","nfhs5_karnataka_districts.csv",
            "aser2024_karnataka_districts.csv","pgid_2025_26_karnataka.csv",
            "udise_karnataka_district_covariates.csv","udise_karnataka_block_covariates.csv",
            "udise_karnataka_gp_covariates.csv","karnataka_geography_hierarchy.csv"]
    gone = [f for f in need if f not in files]
    if gone:
        ok = False
        print("\n!! MISSING core external files: %s" % ", ".join(gone))
    if "census2011_karnataka_district.csv" not in files:
        print("\nNOTE: Census files absent. With internet, run:  python prep\\01_fetch_census.py")

    prim = os.path.join(root, "data", "primary")
    csvs = [f for f in os.listdir(prim) if f.lower().endswith((".csv",".xlsx"))] if os.path.isdir(prim) else []
    print("\nFiles in data/primary: %s" % (", ".join(csvs) if csvs else "NONE"))
    if not csvs:
        print("  Run: python prep\\03_make_synthetic.py   to create rehearsal data")

    print("\n" + "=" * 66)
    print("READY TO RUN" if ok else "FIX THE ITEMS MARKED !! ABOVE, THEN RUN THIS AGAIN")
    print("=" * 66)

if __name__ == "__main__":
    main()
