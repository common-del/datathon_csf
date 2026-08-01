"""Work out which column is which, without assuming exact names."""
import re
import numpy as np
import pandas as pd
import config

SYNONYMS = {
    "year":     ["year","academic_year","acad_year","yr","assessment_year","session"],
    "grade":    ["grade","class","std","standard","grade_level","classe"],
    "division": ["division","div","educational_division","edu_division","region"],
    "district": ["district","dist","district_name","dt"],
    "block":    ["block","taluk","taluka","tehsil","block_name","edu_block"],
    "cluster":  ["cluster","crc","cluster_name","cluster_resource_centre"],
    "gp":       ["gp","gram_panchayat","grampanchayat","panchayat","gramapanchayat",
                 "gp_name","village_panchayat","gram_panchayath"],
    "gender":   ["gender","sex","student_gender","g"],
    "score":    ["score","total","total_score","marks","total_marks","obtained",
                 "raw_score","sum"],
}

def _clean(s):
    return re.sub(r"[^a-z0-9]", "", str(s).strip().lower())

def _find(cols, keys):
    norm = {c: _clean(c) for c in cols}
    for k in keys:                                    # exact normalised match first
        kk = _clean(k)
        for c, n in norm.items():
            if n == kk:
                return c
    for k in keys:                                    # then substring
        kk = _clean(k)
        if len(kk) < 3:
            continue
        for c, n in norm.items():
            if kk in n:
                return c
    return None

def detect_items(df, exclude):
    """Find the binary question columns."""
    if config.MANUAL_ITEM_COLUMNS:
        found = [c for c in config.MANUAL_ITEM_COLUMNS if c in df.columns]
        if found:
            return found, "manual override"

    cand = [c for c in df.columns if c not in exclude]

    def is_binary(c):
        s = pd.to_numeric(df[c], errors="coerce").dropna()
        if len(s) == 0:
            return False
        u = set(np.unique(s.values))
        return u.issubset({0.0, 1.0}) and len(u) >= 1

    pat = re.compile(r"^(q|que|ques|question|item|i|it)[\s_\-]?0*(\d{1,2})$", re.I)
    named = [c for c in cand if pat.match(str(c).strip())]
    named = [c for c in named if is_binary(c)]
    if len(named) >= 5:
        named.sort(key=lambda c: int(pat.match(str(c).strip()).group(2)))
        return named, "name pattern + binary check"

    binary = [c for c in cand if is_binary(c)]
    if len(binary) >= 5:
        return binary, "binary-values scan (names did not match a Q pattern)"
    return named or binary, "WEAK - only %d candidate(s) found" % len(named or binary)

def detect(df):
    cols = list(df.columns)
    roles, notes = {}, []
    for role, keys in SYNONYMS.items():
        ov = config.MANUAL_OVERRIDES.get(role)
        if ov and ov in cols:
            roles[role] = ov; notes.append("%-9s <- %-28s (manual override)" % (role, ov)); continue
        hit = _find(cols, keys)
        roles[role] = hit
        notes.append("%-9s <- %-28s %s" % (role, hit if hit else "NOT FOUND",
                                           "" if hit else "  <-- check config.MANUAL_OVERRIDES"))
    meta = {v for v in roles.values() if v}
    items, how = detect_items(df, meta)
    roles["items"] = items
    notes.append("items     <- %d columns via %s" % (len(items), how))
    if items:
        notes.append("            %s" % (", ".join(map(str, items[:6])) +
                                         (" ... " + str(items[-1]) if len(items) > 6 else "")))
    return roles, notes

GENDER_MAP = {"f":"F","female":"F","girl":"F","g":"F","1":"F",
              "m":"M","male":"M","boy":"M","b":"M","2":"M"}

def harmonise_gender(s):
    codes, uniq = pd.factorize(s, use_na_sentinel=True)
    u = pd.Index(uniq.astype(str)).str.strip().str.lower()
    mapped = np.array([GENDER_MAP.get(v, None) for v in u], dtype=object)
    out = np.full(len(s), None, dtype=object)
    m = codes >= 0
    out[m] = mapped[codes[m]]
    r = pd.Series(out, index=s.index, dtype=object)
    return r.where(r.isin(["F", "M"]))

def year_order(s):
    """'2024-25' -> 2024 ; '2024' -> 2024 ; anything else -> NaN, then rank alphabetically."""
    y = s.astype(str).str.extract(r"(\d{4})")[0]
    y = pd.to_numeric(y, errors="coerce")
    if y.notna().mean() < 0.5:
        codes = pd.Categorical(s.astype(str)).codes
        return pd.Series(codes, index=s.index).astype(float)
    return y
