"""
Build STABLE geography IDs anchored on GP ID, the only canonical key in the dataset.

Why: District and Block labels above a GP get redrawn between years, and Cluster does not
nest under GP at all. Any composite name key (district+block, block+cluster, block+gp)
therefore splits one real unit into several, or merges two real ones. GP ID never moves.

Method, stated so a judge can check it:
  - GP        : GP ID as given. That is the key. Full stop.
  - BLOCK     : each (year, block name) instance carries a set of GP IDs. Two instances of
                the SAME NAME are the same block when their GP-ID sets overlap; disjoint sets
                mean two genuinely different blocks that share a name. Union-find over the
                overlap graph gives block_id. Representative district/block name = modal.
  - CLUSTER   : same construction on cluster names. GP and Cluster are independent
                hierarchies, so overlap is evidence of identity, never of nesting.
  - DISTRICT  : canonical_district from the organisers' crosswalk, taken from that row's own
                year (the instructions say a GP's district can legitimately change).

Writes external_data/geo_id_map.csv  (one row per GP ID x year) and geo_id_summary.csv.
"""
import glob, os, sys
import pandas as pd

HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.abspath(os.path.join(HERE,".."))
PRI=os.path.join(ROOT,"data","primary"); EXT=os.path.join(ROOT,"external_data")

class UF:
    def __init__(s): s.p={}
    def find(s,x):
        s.p.setdefault(x,x)
        while s.p[x]!=x: s.p[x]=s.p[s.p[x]]; x=s.p[x]
        return x
    def union(s,a,b):
        ra,rb=s.find(a),s.find(b)
        if ra!=rb: s.p[rb]=ra

def stable_ids(df, name_col, prefix):
    """Same-name instances that share GP IDs are one unit."""
    inst = df.groupby(["Year", name_col])["GP_ID"].apply(set)
    uf = UF()
    by_name = {}
    for (yr, nm), gps in inst.items():
        uf.find((yr, nm)); by_name.setdefault(nm, []).append(((yr, nm), gps))
    for nm, lst in by_name.items():
        for i in range(len(lst)):
            for j in range(i+1, len(lst)):
                if lst[i][1] & lst[j][1]:
                    uf.union(lst[i][0], lst[j][0])
    root = {k: uf.find(k) for k in uf.p}
    codes = {r: i+1 for i, r in enumerate(sorted({v for v in root.values()}, key=str))}
    out = {k: "%s%04d" % (prefix, codes[r]) for k, r in root.items()}
    return df.set_index(["Year", name_col]).index.map(out)

def main():
    files = sorted(glob.glob(os.path.join(PRI, "std_*.csv")))
    if not files:
        sys.exit("No std_*.csv in data/primary. Run prep/05_standardise_primary.py first.")
    d = pd.concat([pd.read_csv(f, usecols=["Year","District","Block","Cluster","GP","GP_ID"],
                               low_memory=False) for f in files], ignore_index=True)
    for c in ["District","Block","Cluster","GP"]:
        d[c] = d[c].astype(str).str.strip().str.lower()
    d = d.dropna(subset=["GP_ID"]).drop_duplicates()

    d["block_id"]   = stable_ids(d, "Block", "B")
    d["cluster_id"] = stable_ids(d, "Cluster", "C")

    cw = os.path.join(EXT, "organiser_district_crosswalk.csv")
    if os.path.exists(cw):
        x = pd.read_csv(cw)
        m = dict(zip(x["contest_district_value"].astype(str).str.strip().str.lower(),
                     x["standard_district"].astype(str).str.strip()))
        d["canonical_district"] = d["District"].map(m).fillna(d["District"].str.title())
    else:
        d["canonical_district"] = d["District"].str.title()

    def modal(g): return g.mode().iloc[0] if len(g.mode()) else g.iloc[0]
    brep = d.groupby("block_id").agg(block_name=("Block", modal),
                                     block_district=("canonical_district", modal)).reset_index()
    crep = d.groupby("cluster_id").agg(cluster_name=("Cluster", modal)).reset_index()
    grep = d.groupby("GP_ID").agg(gp_name=("GP", modal)).reset_index()

    out = (d[["Year","GP_ID","canonical_district","block_id","cluster_id","District","Block","Cluster","GP"]]
           .merge(brep, on="block_id", how="left").merge(crep, on="cluster_id", how="left")
           .merge(grep, on="GP_ID", how="left").drop_duplicates())
    out.to_csv(os.path.join(EXT, "geo_id_map.csv"), index=False)

    summ = pd.DataFrame([{
        "gp_ids": d.GP_ID.nunique(), "gp_names": d.GP.nunique(),
        "block_ids": d.block_id.nunique(), "block_names": d.Block.nunique(),
        "cluster_ids": d.cluster_id.nunique(), "cluster_names": d.Cluster.nunique(),
        "districts_canonical": d.canonical_district.nunique(),
        "gp_ids_changing_district": int((d.groupby("GP_ID").canonical_district.nunique()>1).sum()),
        "gp_ids_changing_block_id": int((d.groupby("GP_ID").block_id.nunique()>1).sum()),
        "block_names_split_into_2plus_ids": int((d.groupby("Block").block_id.nunique()>1).sum()),
        "cluster_names_split_into_2plus_ids": int((d.groupby("Cluster").cluster_id.nunique()>1).sum()),
    }])
    summ.to_csv(os.path.join(EXT, "geo_id_summary.csv"), index=False)
    print(summ.T.to_string(header=False))
    print("\nwrote external_data/geo_id_map.csv (%d rows) and geo_id_summary.csv" % len(out))

if __name__ == "__main__":
    main()
