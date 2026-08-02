"""
extract_model_importance.py
Pulls the skill-importance results out of the executed notebook into a tidy table.

Why parse the notebook instead of recomputing. The linear model and the forest both run on the
full 13,79,087-row frame inside jupyter_notebook.ipynb, and that notebook has already been run
with outputs saved. Recomputing here would need the 181 MB master file and a second forest fit,
and would risk drifting from what the notebook actually printed. Parsing the saved output means
the table can never disagree with the notebook, which is the whole point.

Writes outputs/tables/model_competency_importance.csv. Fails loudly if the cell has no saved output,
which is the correct behaviour: a deck should not be built from a notebook nobody has run.
"""
import os, sys, json, re
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NB = os.path.join(ROOT, "jupyter_notebook.ipynb")
OUT = os.path.join(ROOT, "outputs", "tables", "model_competency_importance.csv")
META = os.path.join(ROOT, "outputs", "tables", "model_competency_importance_meta.json")

ROW = re.compile(r"^\s*([A-Za-z][A-Za-z /]+?)\s+(-?\d+\.\d+)\s*$")


def cell_text(cell):
    out = []
    for o in cell.get("outputs", []):
        if o.get("text"):
            out.append("".join(o["text"]))
        elif "data" in o and "text/plain" in o["data"]:
            out.append("".join(o["data"]["text/plain"]))
    return "\n".join(out)


def parse_block(text, start_marker, value_name):
    """Read the ' Skill   value' rows that follow a marker line."""
    i = text.find(start_marker)
    if i < 0:
        sys.exit("marker not found in notebook output: %r" % start_marker)
    rows = []
    for line in text[i:].split("\n")[1:]:
        if not line.strip():
            if rows:
                break
            continue
        m = ROW.match(line)
        if m:
            rows.append((m.group(1).strip(), float(m.group(2))))
        elif rows:
            break
    if not rows:
        sys.exit("no rows parsed after %r" % start_marker)
    return pd.DataFrame(rows, columns=["competency", value_name])


def main():
    nb = json.load(open(NB, encoding="utf-8"))
    cell = next((c for c in nb["cells"]
                 if c["cell_type"] == "code" and "RandomForestRegressor" in "".join(c["source"])),
                None)
    if cell is None:
        sys.exit("no RandomForestRegressor cell in %s" % os.path.basename(NB))
    txt = cell_text(cell)
    if not txt.strip():
        sys.exit("the forest cell has no saved output. Run the notebook and save it first.")

    lin = parse_block(txt, "Standardised coefficient", "standardised_coefficient")
    rf = parse_block(txt, "Random-forest importance", "rf_importance")
    df = lin.merge(rf, on="competency", how="outer")
    df["rf_rank"] = df["rf_importance"].rank(ascending=False, method="min").astype(int)
    df["lin_rank"] = df["standardised_coefficient"].rank(ascending=False, method="min").astype(int)
    df["rank_gap"] = df["lin_rank"] - df["rf_rank"]
    df = df.sort_values("rf_importance", ascending=False).reset_index(drop=True)

    meta = {}
    for key, pat in (("linear_r2", r"regression, R2 = ([\d.]+)"),
                     ("rf_r2_in_sample", r"R2 \(in-sample\) = ([\d.]+)"),
                     ("rf_subsample_rows", r"forest on a ([\d,]+)-row subsample")):
        m = re.search(pat, txt)
        if not m:
            sys.exit("could not read %s from the notebook output" % key)
        meta[key] = m.group(1)
    meta["rf_zero_importance_competencies"] = sorted(df.loc[df.rf_importance == 0, "competency"])
    meta["rf_top2_share"] = round(float(df["rf_importance"].nlargest(2).sum()), 3)
    meta["source"] = "jupyter_notebook.ipynb, executed cell containing RandomForestRegressor"

    df.to_csv(OUT, index=False)
    json.dump(meta, open(META, "w"), indent=1)
    print(df.round(3).to_string(index=False))
    print("\nlinear R2 %s   forest in-sample R2 %s on %s rows"
          % (meta["linear_r2"], meta["rf_r2_in_sample"], meta["rf_subsample_rows"]))
    print("forest gives 0.000 importance to: %s" % ", ".join(meta["rf_zero_importance_competencies"]))
    print("top 2 competencies carry %.1f%% of forest importance" % (meta["rf_top2_share"] * 100))
    print("\n-> %s" % os.path.relpath(OUT, ROOT))


if __name__ == "__main__":
    main()
