"""
Self-contained interactive dashboard (single HTML file, no internet needed to view).
Code-based, as the rules require. Plotly is embedded, not linked.
"""
import os, json
import numpy as np, pandas as pd
import config

def _fig_html(fig, first):
    import plotly.io as pio
    return pio.to_html(fig, include_plotlyjs=(True if first else False),
                       full_html=False, config={"displaylogo": False,
                       "modeBarButtonsToRemove": ["lasso2d", "select2d"]})

def _scale():
    return [[i/(len(config.DIVERGING)-1), c] for i, c in enumerate(config.DIVERGING)]

def build(ctx):
    try:
        import plotly.graph_objects as go
    except Exception as e:
        print("      plotly unavailable (%s) - skipping dashboard" % e)
        return None

    blocks, first = [], True
    def add(title, note, fig):
        nonlocal first
        blocks.append((title, note, _fig_html(fig, first)))
        first = False

    df   = ctx["df"]
    n_items = ctx["meta"]["n_items"]

    # ---- KPI strip
    kpis = [("Students", "{:,}".format(len(df))),
            ("Mean score", "%.1f / %d" % (df["score"].mean(), n_items)),
            ("Mean %% correct", "%.1f%%" % df["pct"].mean()),
            ("Districts", "%d" % df["district"].nunique()),
            ("Blocks", "%d" % df["block"].nunique()),
            ("Gram Panchayats", "%d" % df["gp"].nunique()),
            ("Years", "%d" % df["year"].nunique())]
    if df["gender"].notna().any():
        g = df.groupby("gender")["pct"].mean()
        if {"F","M"}.issubset(g.index):
            kpis.append(("Gender gap (F-M)", "%+.1f pp" % (g["F"] - g["M"])))

    # ---- variance signature
    vd = ctx.get("variance")
    if vd is not None and not vd.empty:
        fig = go.Figure()
        fig.add_bar(y=vd["level"], x=vd["share_of_total_variation_pct"], orientation="h",
                    name="share of total variation", marker_color="#9ecae1")
        fig.add_bar(y=vd["level"], x=vd["share_adjusted_pct"], orientation="h",
                    name="df-adjusted component", marker_color=config.GREEN, width=0.42)
        fig.update_layout(barmode="overlay", height=340, template="simple_white",
                          xaxis_title="% of variation in student scores",
                          yaxis=dict(autorange="reversed"),
                          legend=dict(orientation="h", y=-0.25))
        add("Where learning variation actually lives",
            "If the within-Gram-Panchayat share dominates, targeting districts cannot reach "
            "most of the gap however well it is executed.", fig)

    # ---- district ranking
    du = ctx.get("unit_district")
    if du is not None and not du.empty:
        d = du.dropna(subset=["pct_mean"]).sort_values("pct_mean")
        med = float(d["pct_mean"].median())
        fig = go.Figure(go.Bar(
            x=d["pct_mean"], y=d["district"], orientation="h",
            marker=dict(color=d["pct_mean"], colorscale=_scale(), cmid=med,
                        colorbar=dict(title="% correct")),
            customdata=np.stack([d["n_students"], d.get("pct_floor", d["pct_mean"])], axis=-1),
            hovertemplate="<b>%{y}</b><br>mean %{x:.1f}%<br>students %{customdata[0]:,}"
                          "<br>floor p10 %{customdata[1]:.1f}%<extra></extra>"))
        fig.add_vline(x=med, line_dash="dash", line_color=config.INK)
        fig.update_layout(height=max(420, 20*len(d)), template="simple_white",
                          xaxis_title="mean % correct", margin=dict(l=140))
        add("District performance", "Dashed line is the state median. Hover for the floor "
            "(p10) as well as the mean.", fig)

    # ---- competency ladder
    bn = ctx.get("bottleneck")
    if bn is not None and not bn.empty:
        d = bn.sort_values("mastery_rate_pct", ascending=False)
        fig = go.Figure()
        fig.add_bar(x=d["competency_label"], y=d["mastery_rate_pct"], name="mastery %",
                    marker=dict(color=d["mastery_rate_pct"], colorscale=_scale(),
                                cmid=float(d["mastery_rate_pct"].median())))
        fig.add_scatter(x=d["competency_label"], y=d["gate_lift_pp"], name="gate lift (pp)",
                        mode="lines+markers", yaxis="y2", line=dict(color=config.INK))
        fig.update_layout(height=430, template="simple_white",
                          yaxis_title="% mastering", xaxis_tickangle=-32,
                          yaxis2=dict(title="gate lift (pp)", overlaying="y", side="right"),
                          legend=dict(orientation="h", y=-0.45), margin=dict(b=150))
        add("Competency ladder and bottlenecks",
            "Bars = how many children have it. Line = how strongly it gates harder "
            "competencies. Low bar plus high line is the binding constraint.", fig)

    # ---- gender by competency
    gb = ctx.get("gender_by_competency")
    if gb is not None and not gb.empty and "gap_pp_F_minus_M" in gb.columns:
        d = gb.sort_values("overall_mastery_pct", ascending=False)
        fig = go.Figure(go.Bar(x=d["competency_label"], y=d["gap_pp_F_minus_M"],
                marker=dict(color=d["gap_pp_F_minus_M"], colorscale=_scale(), cmid=0)))
        fig.add_hline(y=0, line_color=config.INK)
        fig.update_layout(height=400, template="simple_white", xaxis_tickangle=-32,
                          yaxis_title="girls minus boys (pp)", margin=dict(b=150))
        add("Gender gap by competency", "Ordered easiest to hardest. A gap that flips sign "
            "across the ladder means one story for foundational skills and another for "
            "higher-order ones.", fig)

    # ---- floor vs mean
    fl = ctx.get("floor")
    if fl is not None and not fl.empty and "floor_change_pp" in fl.columns:
        lvl = "district" if "district" in fl.columns else fl.columns[0]
        fig = go.Figure(go.Scatter(
            x=fl["mean_change_pp"], y=fl["floor_change_pp"], mode="markers+text",
            text=fl[lvl], textposition="top center", textfont=dict(size=8),
            marker=dict(size=11, color=fl["floor_minus_mean_divergence_pp"],
                        colorscale=_scale(), cmid=0, colorbar=dict(title="floor − mean"))))
        lo = float(min(fl.mean_change_pp.min(), fl.floor_change_pp.min())) - 1
        hi = float(max(fl.mean_change_pp.max(), fl.floor_change_pp.max())) + 1
        fig.add_shape(type="line", x0=lo, y0=lo, x1=hi, y1=hi, line=dict(dash="dash", color=config.GREY))
        fig.update_layout(height=520, template="simple_white",
                          xaxis_title="change in mean (pp)",
                          yaxis_title="change in floor p%d (pp)" % config.FLOOR_PERCENTILE)
        add("Did the average move, or did the weakest children move?",
            "Points below the diagonal grew on average while the bottom decile was left behind.", fig)

    # ---- bright spots
    sar = ctx.get("sar")
    if sar is not None and not sar.empty:
        lvl = ctx.get("sar_level", "block")
        d = sar.dropna(subset=["predicted_pct","pct_mean"])
        fig = go.Figure(go.Scatter(
            x=d["predicted_pct"], y=d["pct_mean"], mode="markers",
            marker=dict(size=8, color=d["residual_pp"], colorscale=_scale(), cmid=0,
                        colorbar=dict(title="residual pp")),
            text=d[lvl], hovertemplate="<b>%{text}</b><br>predicted %{x:.1f}%"
                                       "<br>actual %{y:.1f}%<extra></extra>"))
        lo = float(min(d.predicted_pct.min(), d.pct_mean.min())) - 1
        hi = float(max(d.predicted_pct.max(), d.pct_mean.max())) + 1
        fig.add_shape(type="line", x0=lo, y0=lo, x1=hi, y1=hi, line=dict(dash="dash", color=config.INK))
        fig.update_layout(height=520, template="simple_white",
                          xaxis_title="predicted from socio-economic + school-system conditions (%)",
                          yaxis_title="actual mean (%)")
        add("Bright spots: doing better than circumstances predict",
            "Above the line means the place outperforms its structural conditions. These are "
            "the practices worth visiting, and the honest answer to 'correlation is not causation'.", fig)

    # ---- tables
    tables = []
    for label, key, note in [
        ("Triage priority list", "triage",
         "Ranked action list: learning gap x children affected x tractability."),
        ("Early-warning watch list", "watch",
         "Units the model expects in the bottom quartile. Precision and recall are in the model card."),
        ("Data quality flags", "qa_flags",
         "Everything we found wrong with the data before drawing conclusions."),
    ]:
        t = ctx.get(key)
        if t is not None and len(t):
            tt = t.head(60).copy()
            tables.append((label, note, tt.to_html(index=False, border=0,
                           classes="tbl", float_format=lambda x: "%.2f" % x)))

    kpi_html = "".join(
        '<div class="kpi"><div class="kpi-v">%s</div><div class="kpi-l">%s</div></div>' % (v, k)
        for k, v in kpis)
    sec_html = "".join(
        '<section><h2>%s</h2><p class="note">%s</p>%s</section>' % (t, n, h)
        for t, n, h in blocks)
    tab_html = "".join(
        '<section><h2>%s</h2><p class="note">%s</p><div class="tw">%s</div></section>' % (t, n, h)
        for t, n, h in tables)

    css = """
    :root{--ink:#222;--mut:#6b6b6b;--line:#e6e6e6;--bg:#fbfbfa;--grn:#1B7837}
    *{box-sizing:border-box} body{margin:0;font:15px/1.55 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
      color:var(--ink);background:var(--bg)}
    header{padding:28px 34px 18px;border-bottom:1px solid var(--line);background:#fff}
    h1{margin:0 0 6px;font-size:24px;letter-spacing:-.3px}
    .sub{color:var(--mut);font-size:13px}
    .kpis{display:flex;flex-wrap:wrap;gap:12px;padding:20px 34px}
    .kpi{background:#fff;border:1px solid var(--line);border-radius:10px;padding:12px 16px;min-width:130px}
    .kpi-v{font-size:20px;font-weight:650} .kpi-l{font-size:11px;color:var(--mut);text-transform:uppercase;letter-spacing:.5px}
    section{background:#fff;border:1px solid var(--line);border-radius:12px;margin:14px 34px;padding:20px 24px}
    h2{margin:0 0 4px;font-size:17px} .note{margin:0 0 14px;color:var(--mut);font-size:13px;max-width:80ch}
    .tw{overflow:auto;max-height:520px;border:1px solid var(--line);border-radius:8px}
    table.tbl{border-collapse:collapse;width:100%;font-size:12.5px}
    table.tbl th{position:sticky;top:0;background:#f3f3f1;text-align:left;padding:8px 10px;
      border-bottom:1px solid var(--line);white-space:nowrap}
    table.tbl td{padding:6px 10px;border-bottom:1px solid #f2f2f2;white-space:nowrap}
    table.tbl tr:hover td{background:#fafaf7}
    footer{padding:22px 34px 40px;color:var(--mut);font-size:12px}
    """
    html = ("<!doctype html><html><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<title>%s</title><style>%s</style></head><body>"
            "<header><h1>%s</h1><div class='sub'>%s</div></header>"
            "<div class='kpis'>%s</div>%s%s"
            "<footer>%s</footer></body></html>") % (
        ctx.get("title", "Learning Analytics"), css,
        ctx.get("title", "Learning Analytics"), ctx.get("subtitle", ""),
        kpi_html, sec_html, tab_html, ctx.get("footer", ""))

    os.makedirs(config.OUTPUTS, exist_ok=True)
    os.makedirs(config.FIGURES, exist_ok=True)
    p = os.path.join(config.FIGURES, "dashboard.html")
    with open(p, "w", encoding="utf-8") as f:
        f.write(html)
    print("      dashboard: %s (%.1f MB)" % (os.path.basename(p), os.path.getsize(p)/1e6))
    return p
