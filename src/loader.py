"""Load, clean and enrich the primary assessment file."""
import glob, os
import numpy as np
import pandas as pd
import config, schema


def _clean_geo_fast(s):
    """Uppercase/strip via the unique values, not the 4M rows. 30x faster at census scale."""
    codes, uniq = pd.factorize(s, use_na_sentinel=True)
    u = pd.Index(uniq.astype(str)).str.strip().str.upper()
    u = u.to_series(index=range(len(u))).replace({"NAN": np.nan, "NONE": np.nan, "": np.nan})
    arr = u.to_numpy(dtype=object)
    out = np.full(len(s), np.nan, dtype=object)
    m = codes >= 0
    out[m] = arr[codes[m]]
    return pd.Series(out, index=s.index, dtype=object)

GEO_ORDER = ["division", "district", "block", "cluster", "gp"]

IGNORE = ("PUT_THE_DATASET_HERE", "README", "NOTES", "INSTRUCTIONS", "LICENSE",
          "CROSSWALK", "NOTE ON DATA", "~$")

def candidate_files():
    """Every plausible data file in ./data and ./data/primary, best guess first.
    Judges drop the organiser workbooks straight into ./data; we also keep std CSVs
    in data/primary locally. Both work through the same code path."""
    pats = ["*.csv","*.CSV","*.xlsx","*.xls","*.tsv","*.txt"]
    files = []
    for base in (config.PRIMARY, config.DATA):
        for p in pats:
            files += glob.glob(os.path.join(base, p))
    out = []
    for f in files:
        b = os.path.basename(f)
        if b.startswith(("~", ".")):
            continue
        if any(k in b.upper() for k in IGNORE):
            continue
        out.append(f)
    out = sorted(set(out))
    # real files before rehearsal files, then biggest first
    out.sort(key=lambda f: ("SYNTHETIC" in os.path.basename(f).upper(),
                            -os.path.getsize(f)))
    return out

def find_primary_file():
    c = candidate_files()
    return c[0] if c else None

CANON_COMPETENCIES = ["addition","subtraction","multiplication","division","number sense",
    "place value","fraction","measurement","mensuration","shapes","data handling"]

def _read_excel_fast(path, **kw):
    try:
        return pd.read_excel(path, engine="calamine", **kw)
    except Exception:
        return pd.read_excel(path, **kw)

def _year_grade_from_name(path):
    import re
    m = re.search(r"[Gg]rade[_ ]?(\d+).*?(\d{4}-\d{2})", os.path.basename(path))
    return (int(m.group(1)), m.group(2)) if m else (None, None)

def _mapping_for(path, grade, year):
    """Per-file item->competency map: from the workbook's own sheet, or the extracted
    external_data/competency_map_by_file.csv for std CSVs."""
    if str(path).lower().endswith((".xlsx", ".xls")):
        try:
            raw = _read_excel_fast(path, sheet_name="Competency Mapping", header=None)
            raw = raw.dropna(how="all").dropna(axis=1, how="all")
            raw.columns = range(raw.shape[1])
            rows = []
            for _, r in raw.iterrows():
                vals = [str(v).strip() for v in r.tolist()]
                q = next((v for v in vals if v.startswith("Q") and v[1:].isdigit()), None)
                comp = next((v for v in vals if v.lower() in CANON_COMPETENCIES), None)
                if q and comp:
                    rows.append((q, comp.lower()))
            if rows:
                return dict(rows)
        except Exception:
            pass
    p = os.path.join(config.EXTERNAL, "competency_map_by_file.csv")
    if os.path.exists(p) and grade is not None:
        m = pd.read_csv(p)
        m = m[(m.grade == grade) & (m.year == year)]
        if len(m):
            return dict(zip(m["item"], m["competency"]))
    return None

def read_any(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in (".xlsx", ".xls"):
        try:
            return _read_excel_fast(path, sheet_name="Assessment Data")
        except Exception:
            return _read_excel_fast(path)
    # fast path first: C engine, comma. The python-engine sniffing fallback is
    # far too slow for a multi-hundred-MB census file.
    try:
        df = pd.read_csv(path, low_memory=False)
        if df.shape[1] > 1:
            return df
    except Exception:
        pass
    for sep in ["\t", ";", "|", None]:
        try:
            df = pd.read_csv(path, sep=sep, engine="python", low_memory=False)
            if df.shape[1] > 1:
                return df
        except Exception:
            continue
    return pd.read_csv(path, low_memory=False)

def _build_out(df, roles, items):
    """Turn one raw file into the lean analysis frame."""
    out = pd.DataFrame(index=df.index)
    for role in GEO_ORDER:
        c = roles.get(role)
        # Deliberately NOT category dtype: grouping on several category columns
        # makes pandas build the full cartesian product of levels and blows memory.
        out[role] = _clean_geo_fast(df[c]) if c else np.nan
    out["year"]  = _clean_geo_fast(df[roles["year"]]).str.title() if roles.get("year") else "ALL"
    out["grade"] = pd.to_numeric(df[roles["grade"]], errors="coerce") if roles.get("grade") else np.nan
    out["gender"] = schema.harmonise_gender(df[roles["gender"]]) if roles.get("gender") else np.nan

    # single-block numpy path: 10x faster than 20 per-column passes at census scale
    try:
        A = df[items].to_numpy(dtype="float32", na_value=np.nan)
    except Exception:
        A = np.column_stack([pd.to_numeric(df[c], errors="coerce").astype("float32") for c in items])
    if not A.flags.writeable:
        A = A.copy()
    A[(A != 0) & (A != 1)] = np.nan
    finite = np.isfinite(A)
    out["n_attempted"] = finite.sum(axis=1).astype("int16")
    with np.errstate(invalid="ignore"):
        ssum = np.nansum(A, axis=1)
    ssum[~finite.any(axis=1)] = np.nan
    out["score_items"] = ssum.astype("float32")
    for j, c in enumerate(items):
        out[c] = A[:, j]
    del A, finite
    if roles.get("score"):
        out["score_given"] = pd.to_numeric(df[roles["score"]], errors="coerce")
    else:
        out["score_given"] = np.nan
    return out


def load():
    """Load EVERY usable data file in data/primary/ and stack them.
    The organisers hand out one file per year; this reads all three (or one, or five)."""
    import gc
    cands = candidate_files()
    if not cands:
        raise FileNotFoundError(
            "No data file found in data/primary/.\n"
            "Put the Akshara CSV(s) in that folder and run again.")
    roles, items, notes = None, None, None
    parts, used, skipped = [], [], []
    for c in cands:
        try:
            d = read_any(c)
            d.columns = [str(x).strip() for x in d.columns]
            g_f, y_f = _year_grade_from_name(c)
            if "Year" not in d.columns and y_f:
                d.insert(0, "Year", y_f)
            if "Grade" not in d.columns and g_f is not None:
                d.insert(1, "Grade", g_f)
            if roles is None:
                r, n = schema.detect(d)
                if len(r.get("items") or []) < 5:
                    skipped.append("%s (only %d item columns)" % (os.path.basename(c),
                                   len(r.get("items") or []))); continue
                roles, items, notes = r, r["items"], n
            else:
                missing = [x for x in items if x not in d.columns]
                if missing:
                    skipped.append("%s (item columns differ: missing %s)"
                                   % (os.path.basename(c), ", ".join(map(str, missing[:4]))))
                    continue
            out_part = _build_out(d, roles, items)
            # GP ID: mandated join/group key. Carry it, and disambiguate name collisions.
            idcol = next((x for x in d.columns if x.strip().lower().replace(" ", "_") in
                          ("gp_id", "gpid")), None)
            if idcol:
                out_part["gp_id"] = pd.to_numeric(d[idcol], errors="coerce")
                key = out_part.groupby(["district", "block", "gp"], dropna=False)["gp_id"].transform("nunique")
                dup = key > 1
                if dup.any():
                    out_part.loc[dup, "gp"] = (out_part.loc[dup, "gp"].astype(str) + " [" +
                                               out_part.loc[dup, "gp_id"].astype("Int64").astype(str) + "]")
            else:
                out_part["gp_id"] = np.nan
            # ---- stable ID keys (GP ID canonical; block/cluster IDs derived from GP-ID overlap)
            gmp = os.path.join(config.EXTERNAL, "geo_id_map.csv")
            if os.path.exists(gmp) and out_part["gp_id"].notna().any():
                gm = pd.read_csv(gmp)
                gm["Year"] = gm["Year"].astype(str)
                key = out_part[["year", "gp_id"]].copy()
                key["Year"] = key["year"].astype(str)
                key["GP_ID"] = key["gp_id"]
                j = key.merge(gm[["Year","GP_ID","canonical_district","block_id","cluster_id",
                                  "block_name","cluster_name","gp_name"]].drop_duplicates(["Year","GP_ID"]),
                              on=["Year","GP_ID"], how="left")
                out_part["district"] = j["canonical_district"].fillna(out_part["district"]).values
                out_part["block"]    = (j["block_id"].fillna("") + " " + j["block_name"].fillna("")).str.strip().replace("", np.nan).values
                out_part["cluster"]  = (j["cluster_id"].fillna("") + " " + j["cluster_name"].fillna("")).str.strip().replace("", np.nan).values
                out_part["gp"]       = (out_part["gp_id"].astype("Int64").astype(str) + " " +
                                        j["gp_name"].fillna("").values).str.strip()
            # per-file competency share-correct columns (equated across years per organisers)
            g_cur = g_f if g_f is not None else (pd.to_numeric(d["Grade"], errors="coerce").iloc[0] if "Grade" in d.columns else None)
            y_cur = y_f if y_f else (str(d["Year"].iloc[0]) if "Year" in d.columns else None)
            mp = _mapping_for(c, g_cur, y_cur)
            if mp:
                for comp in CANON_COMPETENCIES:
                    its = [q for q, cc in mp.items() if cc == comp and q in out_part.columns]
                    col = "C_" + comp.replace(" ", "_")
                    out_part[col] = out_part[its].mean(axis=1).astype("float32") if its else np.nan
            parts.append(out_part)
            used.append("%s (%d rows, %.0f MB)" % (os.path.basename(c), len(d),
                        os.path.getsize(c)/1e6))
            del d; gc.collect()
        except Exception as e:
            skipped.append("%s (%s: %s)" % (os.path.basename(c), type(e).__name__, e))
    if not parts:
        raise ValueError(
            "None of the files in data/primary/ produced usable question columns.\n"
            "Tried:\n   " + "\n   ".join(skipped) +
            "\nSet config.MANUAL_ITEM_COLUMNS to the exact question column names and re-run.")
    ccols = sorted({c for p_ in parts for c in p_.columns if c.startswith("C_")})
    print("   files stacked: %d | competency columns built: %d" % (len(parts), len(ccols)))
    for u in used:
        print("      + " + u)
    for sk in skipped:
        print("      - skipped " + sk)
    print("\n   --- column detection (from first file) ---")
    for n in notes:
        print("   " + n)
    print("   ------------------------\n")
    out = parts[0] if len(parts) == 1 else pd.concat(parts, ignore_index=True)
    del parts; gc.collect()

    out["year_n"] = schema.year_order(out["year"])
    out["score"] = out["score_items"].astype("float32")
    out["pct"]   = (100.0 * out["score"] / len(items)).astype("float32")
    out["grade"] = pd.to_numeric(out["grade"], errors="coerce").astype("float32")
    frac = getattr(config, "SAMPLE_FRACTION", None)
    if frac and 0 < frac < 1:
        out = out.sample(frac=frac, random_state=config.SEED).reset_index(drop=True)
        print("   *** SAMPLED to %.0f%% (%d rows). Set SAMPLE_FRACTION = None in config.py "
              "before your final run. ***" % (100 * frac, len(out)))
    mb = out.memory_usage(deep=True).sum() / 1e6
    print("   in-memory size: %.0f MB" % mb)
    if len(out) > 2_000_000 and not frac:
        print("   NOTE: %.1fM rows. If this run is slow or runs out of memory, set"
              % (len(out) / 1e6))
        print("         SAMPLE_FRACTION = 0.25 in src/config.py for a fast first pass.")
    meta = {"path": " + ".join(u.split(" (")[0] for u in used), "roles": roles, "items": items,
            "n_items": len(items), "raw_shape": out.shape}
    return out, meta


def load_competency_map(items):
    """Real mapping if provided, else infer 2-items-per-competency groups by correlation."""
    p = os.path.join(config.EXTERNAL, config.COMPETENCY_MAP_FILE)
    if os.path.exists(p):
        m = pd.read_csv(p)
        m.columns = [c.strip().lower() for c in m.columns]
        if {"item", "competency_code"}.issubset(m.columns):
            m = m[m["item"].isin(items)]
            if len(m) >= len(items) * 0.8:
                if "competency_label" not in m.columns:
                    m["competency_label"] = m["competency_code"]
                print("   competency map: loaded %s (%d items mapped)" % (config.COMPETENCY_MAP_FILE, len(m)))
                return m[["item","competency_code","competency_label"]], True
    print("   competency map: NOT FOUND -> inferring pairs from response correlation")
    return None, False

def infer_competency_map(df, items, k=None):
    """Group items into competencies using hierarchical clustering on item correlations."""
    from scipy.cluster.hierarchy import linkage, fcluster
    from scipy.spatial.distance import squareform
    k = k or max(2, len(items) // 2)
    corr = df[items].corr().fillna(0.0).to_numpy(copy=True)   # copy: newer pandas returns read-only
    np.fill_diagonal(corr, 1.0)
    d = 1.0 - corr
    d = (d + d.T) / 2.0
    np.fill_diagonal(d, 0.0)
    lab = fcluster(linkage(squareform(d, checks=False), method="average"), k, criterion="maxclust")
    diff = df[items].mean()
    order = (pd.Series(lab, index=items).groupby(lambda i: None).apply(lambda s: s))
    m = pd.DataFrame({"item": items, "grp": lab})
    rank = m.assign(d=diff.reindex(m["item"]).values).groupby("grp")["d"].mean().rank(ascending=False)
    m["competency_code"]  = m["grp"].map(lambda g: "INF%02d" % int(rank[g]))
    m["competency_label"] = m["competency_code"] + " (inferred group)"
    return m[["item","competency_code","competency_label"]]
