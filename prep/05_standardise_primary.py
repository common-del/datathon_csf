"""
Convert the organiser GPContest workbooks into standardised CSVs the pipeline reads.

Run once (takes a few minutes with openpyxl, seconds with python-calamine):
    python prep/05_standardise_primary.py

Per workbook GPContest_Grade_<g>_<year>.xlsx it writes std_grade<g>_<year>.csv into
data/primary/ with added Year and Grade columns (from the filename), plus once only:
    external_data/competency_map.csv          (from the Competency Mapping sheet)
    external_data/organiser_district_crosswalk.csv  (from district_crosswalk.xlsx)
    external_data/gp_id_lookup.csv            (district|block|cluster|gp -> GP ID)
The original .xlsx files are left untouched; the loader ignores .xlsx when std CSVs exist?
No - the loader reads every csv/xlsx. To avoid double-loading, this script renames each
processed workbook to .xlsx.done (rename it back any time).
"""
import glob, os, re, sys
import pandas as pd

HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.abspath(os.path.join(HERE,".."))
PRI=os.path.join(ROOT,"data","primary"); EXT=os.path.join(ROOT,"external_data")

def reader(path, **kw):
    try:
        return pd.read_excel(path, engine="calamine", **kw)
    except Exception:
        return pd.read_excel(path, **kw)

def all_mappings(wbs):
    rows=[]
    for w in wbs:
        m=re.search(r"Grade[_ ]?(\d+)[_ ]?(\d{4}-\d{2})",os.path.basename(w))
        raw=reader(w, sheet_name="Competency Mapping", header=None)
        raw=raw.dropna(how="all").dropna(axis=1,how="all"); raw.columns=range(raw.shape[1])
        for _,r in raw.iterrows():
            vals=[str(v).strip() for v in r.tolist()]
            q=next((v for v in vals if v.startswith("Q") and v[1:].isdigit()),None)
            comp=next((v for v in vals if v.lower() in ("addition","subtraction","multiplication",
                 "division","number sense","place value","fraction","measurement","mensuration",
                 "shapes","data handling")),None)
            name=next((v for v in vals if "_" in v and not v.startswith("Q")),"")
            if q and comp:
                rows.append({"grade":int(m.group(1)),"year":m.group(2),"item":q,
                             "competency":comp.lower(),"question_name":name})
    out=pd.DataFrame(rows)
    out.to_csv(os.path.join(EXT,"competency_map_by_file.csv"),index=False)
    print("competency_map_by_file.csv: %d rows | competencies: %s"%(len(out),sorted(out.competency.unique())))

def do_mappings(sample_wb):
    # competency map (same in every workbook; header junk in first rows)
    raw=reader(sample_wb, sheet_name="Competency Mapping", header=None)
    raw=raw.dropna(how="all").dropna(axis=1,how="all")
    raw.columns=range(raw.shape[1])
    hdr=raw[raw.apply(lambda r: r.astype(str).str.contains("Questions",case=False).any(),axis=1)].index
    body=raw.loc[hdr[0]+1:] if len(hdr) else raw
    body=body.iloc[:,:3]; body.columns=["item","question_name","competency"]
    body=body.dropna(subset=["item"])
    body["item"]=body["item"].astype(str).str.strip()
    body=body[body["item"].str.match(r"^Q\d+$")]
    out=pd.DataFrame({"item":body["item"],
        "competency_code":body["competency"].astype(str).str.strip().str.lower().str.replace(r"[^a-z0-9]+","_",regex=True),
        "competency_label":body["competency"].astype(str).str.strip(),
        "question_name":body["question_name"].astype(str).str.strip()})
    out.to_csv(os.path.join(EXT,"competency_map.csv"),index=False)
    print("competency_map.csv: %d items, %d competencies"%(len(out),out.competency_code.nunique()))

    cw=os.path.join(PRI,"district_crosswalk.xlsx")
    if os.path.exists(cw):
        d=reader(cw, sheet_name="District Crosswalk")
        d.to_csv(os.path.join(EXT,"organiser_district_crosswalk.csv"),index=False)
        print("organiser_district_crosswalk.csv: %d rows"%len(d))

def one(path):
    m=re.search(r"Grade[_ ]?(\d+)[_ ]?(\d{4}-\d{2})",os.path.basename(path))
    grade,year=int(m.group(1)),m.group(2)
    d=reader(path, sheet_name="Assessment Data")
    d.columns=[str(c).strip() for c in d.columns]
    d=d.rename(columns={"GP Name":"GP","GP ID":"GP_ID"})
    d.insert(0,"Year",year); d.insert(1,"Grade",grade)
    out=os.path.join(PRI,"std_grade%d_%s.csv"%(grade,year))
    d.to_csv(out,index=False)
    # GP lookup rows
    look=d[["District","Block","Cluster","GP","GP_ID"]].drop_duplicates()
    os.rename(path, path+".done")
    print("%-38s -> %-28s rows=%6d dist=%2d gp=%4d"%(os.path.basename(path),os.path.basename(out),len(d),d.District.nunique(),d.GP.nunique()))
    return look

def main():
    wbs=sorted(glob.glob(os.path.join(PRI,"GPContest_*.xlsx")))
    done=sorted(glob.glob(os.path.join(PRI,"GPContest_*.xlsx.done")))
    if not wbs and done:
        print("all workbooks already processed"); return
    src=[w[:-5] if w.endswith(".done") else w for w in wbs]
    allw=wbs+[w for w in done]
    if allw and not os.path.exists(os.path.join(EXT,"competency_map_by_file.csv")):
        all_mappings([w if os.path.exists(w) else w for w in (wbs or done)])
        cw=os.path.join(PRI,"district_crosswalk.xlsx")
        if os.path.exists(cw):
            d=reader(cw, sheet_name="District Crosswalk")
            d.to_csv(os.path.join(EXT,"organiser_district_crosswalk.csv"),index=False)
    looks=[]
    for w in wbs:
        looks.append(one(w))
    if looks:
        gl=pd.concat(looks,ignore_index=True).drop_duplicates()
        gl.to_csv(os.path.join(EXT,"gp_id_lookup.csv"),index=False)
        print("gp_id_lookup.csv: %d unique geography rows"%len(gl))

if __name__=="__main__":
    main()
