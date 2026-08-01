"""
Karnataka district choropleth of assessment coverage.

Coverage = students assessed (all grades 4-6, all three years pooled)
         / UDISE+ grade 4-6 enrolment in State Government schools (same three years).

Geometry: Census-2011 district boundaries (30 districts), simplified and committed to
external_data/karnataka_districts.geojson so the run stays offline.

Two known geometry caveats, both handled and labelled on the map:
  - Vijayanagara was carved out of Ballari in 2021 and has no 2011 polygon. Its assessed
    and enrolled counts are POOLED INTO BALLARI so no child is dropped.
  - Bengaluru Urban and Shivamogga have zero contest rows. They are drawn in grey as
    "no contest data", never as 0% coverage.
"""
import json, os
import numpy as np, pandas as pd
import config

MERGE_INTO = {"Vijayanagara": "Ballari"}

def build(cov_long=None):
    geo_p = os.path.join(config.EXTERNAL, "karnataka_districts.geojson")
    if not os.path.exists(geo_p):
        print("      no geojson at %s - skipping choropleth" % geo_p); return None
    if cov_long is None:
        p = os.path.join(config.TABLES, "coverage_district_grade_year.csv")
        if not os.path.exists(p):
            print("      coverage table missing - skipping choropleth"); return None
        cov_long = pd.read_csv(p)

    d = cov_long[cov_long.basis == "rural"].copy()
    d["geo_district"] = d["canonical_district"].replace(MERGE_INTO)
    agg = d.groupby("geo_district")[["assessed", "enrolled"]].sum().reset_index()
    agg["coverage_pct"] = (100 * agg.assessed / agg.enrolled).round(1)
    agg.to_csv(os.path.join(config.TABLES, "coverage_district_overall.csv"), index=False)

    gj = json.load(open(geo_p))
    names = [f["properties"]["district"] for f in gj["features"]]
    frame = pd.DataFrame({"geo_district": names}).merge(agg, on="geo_district", how="left")
    frame["label"] = np.where(frame.coverage_pct.notna(),
                              frame.geo_district + "<br>" + frame.coverage_pct.astype(str) + "%",
                              frame.geo_district + "<br>no contest data")
    try:
        import plotly.graph_objects as go
    except Exception as e:
        print("      plotly unavailable (%s)" % e); return None

    have = frame.dropna(subset=["coverage_pct"])
    miss = frame[frame.coverage_pct.isna()]
    # green = better covered, red = worse. White near the state figure.
    scale = [[0, "#B2182B"], [0.25, "#EF8A62"], [0.45, "#FDDBC7"], [0.55, "#FFFFFF"],
             [0.7, "#D9F0D3"], [0.85, "#7FBF7B"], [1, "#1B7837"]]
    state = 100 * agg.assessed.sum() / agg.enrolled.sum()

    fig = go.Figure()
    if len(miss):
        fig.add_choropleth(geojson=gj, locations=miss.geo_district, featureidkey="properties.district",
                           z=[0]*len(miss), colorscale=[[0, "#E0E0E0"], [1, "#E0E0E0"]],
                           showscale=False, marker_line_color="white", marker_line_width=0.8,
                           hovertext=miss.label, hoverinfo="text")
    fig.add_choropleth(
        geojson=gj, locations=have.geo_district, featureidkey="properties.district",
        z=have.coverage_pct, colorscale=scale, zmin=0, zmax=70,
        marker_line_color="white", marker_line_width=0.8,
        hovertext=have.label, hoverinfo="text",
        colorbar=dict(title="% of enrolled<br>children assessed", ticksuffix="%", len=0.75))
    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_layout(
        title=dict(text="<b>The GP Maths Contest is not a census</b><br>"
                        "<sup>Students assessed as a share of UDISE grade 4-6 State Government "
                        "enrolment, 2022-23 to 2024-25 pooled. Statewide: %.1f%%. "
                        "Grey = no contest data.</sup>" % state, x=0.02, xanchor="left"),
        margin=dict(l=0, r=0, t=80, b=0), height=760, paper_bgcolor="white")
    os.makedirs(config.FIGURES, exist_ok=True)
    out = os.path.join(config.FIGURES, "coverage_choropleth.html")
    fig.write_html(out, include_plotlyjs=True, config={"displaylogo": False})
    print("      -> figures/coverage_choropleth.html (%.1f%% statewide, %d districts drawn)"
          % (state, len(have)))
    _png(gj, frame, state)
    return out


def _png(gj, frame, state):
    """Static PNG via matplotlib. No kaleido, no Chrome, no network - works anywhere."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon as MplPoly
    from matplotlib.collections import PatchCollection
    from matplotlib.colors import LinearSegmentedColormap, Normalize
    from matplotlib.cm import ScalarMappable

    cmap = LinearSegmentedColormap.from_list(
        "cov", ["#B2182B", "#EF8A62", "#FDDBC7", "#FFFFFF", "#D9F0D3", "#7FBF7B", "#1B7837"])
    norm = Normalize(vmin=0, vmax=70)
    lut = dict(zip(frame.geo_district, frame.coverage_pct))

    fig, ax = plt.subplots(figsize=(10, 11.2))
    fig.subplots_adjust(top=0.895)
    patches, colours = [], []
    for f in gj["features"]:
        nm = f["properties"]["district"]
        ring = f["geometry"]["coordinates"][0]
        poly = MplPoly(np.array(ring), closed=True)
        v = lut.get(nm)
        patches.append(poly)
        colours.append(cmap(norm(v)) if pd.notna(v) else "#E0E0E0")
        cx = float(np.mean([p[0] for p in ring])); cy = float(np.mean([p[1] for p in ring]))
        txt = "%s\n%.0f%%" % (nm[:14], v) if pd.notna(v) else "%s\nn/a" % nm[:14]
        col = "#111111" if (pd.isna(v) or 12 < v < 58) else ("white" if pd.notna(v) and v <= 12 else "#111111")
        ax.annotate(txt, (cx, cy), ha="center", va="center", fontsize=6.4, color=col, linespacing=1.15)
    pc = PatchCollection(patches, facecolors=colours, edgecolors="white", linewidths=0.9)
    ax.add_collection(pc)
    ax.autoscale_view(); ax.set_aspect("equal"); ax.axis("off")
    fig.suptitle("The GP Maths Contest is not a census", fontsize=17, fontweight="bold",
                 x=0.06, ha="left", y=0.975)
    fig.text(0.06, 0.938, "Students assessed as a share of UDISE grade 4-6 State Government "
             "enrolment, 2022-23 to 2024-25 pooled.", fontsize=9.5, color="#444444", ha="left")
    fig.text(0.06, 0.918, "Statewide %.1f%%.  Grey = no contest data.  "
             "Vijayanagara pooled into Ballari (2011 boundaries)." % state,
             fontsize=9.5, color="#444444", ha="left")
    cb = fig.colorbar(ScalarMappable(norm=norm, cmap=cmap), ax=ax, fraction=0.03, pad=0.01)
    cb.set_label("% of enrolled children assessed", fontsize=9)
    p = os.path.join(config.FIGURES, "coverage_choropleth.png")
    fig.savefig(p, dpi=200, facecolor="white")
    plt.close(fig)
    print("      -> figures/coverage_choropleth.png (matplotlib, no external deps)")
