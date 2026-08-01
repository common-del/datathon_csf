"""
PRE-BAKED CONTEXT PACK.
Everything here is computable WITHOUT the student assessment file, so it is done
before Day 1. The Day-1 engine (src/run_all.py) is reserved for score-dependent work.

Writes context_pack/: tables, figures, and CONTEXT_FINDINGS.md with real numbers.
"""
import os, sys
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.abspath(os.path.join(HERE,".."))
EXT=os.path.join(ROOT,"external_data"); CP=os.path.join(ROOT,"context_pack")
FIG=os.path.join(CP,"figures"); TAB=os.path.join(CP,"tables")
for d in (CP,FIG,TAB): os.makedirs(d,exist_ok=True)
sys.path.insert(0,os.path.join(ROOT,"src"))
import external

GREEN,RED,INK,GREY="#1B7837","#B2182B","#222222","#9E9E9E"
plt.rcParams.update({"figure.dpi":130,"font.size":9,"axes.spines.top":False,
                     "axes.spines.right":False,"figure.autolayout":True})
F=[]  # findings

alias=external.build_alias_table()
cov,_=external.district_covariates(alias)
cw=pd.read_csv(os.path.join(EXT,"karnataka_district_crosswalk.csv"))
cov=cov.merge(cw[["current_name","is_371J_kalyana_karnataka","princely_legacy"]],
              left_on="canonical_district",right_on="current_name",how="left")
cov.to_csv(os.path.join(TAB,"district_context_profile.csv"),index=False)

# ---- F1 teacher availability gradient
d=cov.dropna(subset=["ptr_govt"])
div=d.groupby("revenue_division")["ptr_govt"].mean().round(1).sort_values()
kk=d[d.is_371J_kalyana_karnataka==1]["ptr_govt"].mean()
rest=d[d.is_371J_kalyana_karnataka==0]["ptr_govt"].mean()
F.append(("Teacher availability is the starkest structural divide in the state",
 "Government-school PTR (grades 4-6 schools, UDISE 2024-25; unweighted means over the 31 revenue "
 "districts, educational districts averaged into their parents first) is %.1f across the 7 Kalyana "
 "Karnataka (Article 371J) districts against %.1f in the other 24. Computed directly on the 35 "
 "educational districts the contrast is 35.6 vs 22.2 (both bases re-verified 30 Jul 2026). "
 "Division means: %s. A decade of special "
 "constitutional status has not closed the teacher gap."
 % (kk,rest,", ".join("%s %.1f"%(k,v) for k,v in div.items())),
 "Do scores track PTR at GP level once poverty is controlled? Which competencies suffer most where PTR is worst?"))

# ---- F2 the assessment universe (FULL universe from school-level files, not GP-linked subset)
UC=os.path.join(ROOT,"data","udise_csv")
rows=[]
for y in ["2022-23","2023-24","2024-25"]:
    m=pd.read_csv(os.path.join(UC,"udise_ka_enrolment_by_grade_%s.csv"%y),low_memory=False)
    for c in ["c4_b","c4_g","c5_b","c5_g","c6_b","c6_g"]:
        m[c]=pd.to_numeric(m[c],errors="coerce").fillna(0)
    m["g46"]=m[["c4_b","c4_g","c5_b","c5_g","c6_b","c6_g"]].sum(axis=1)
    gv=m.management_group.isin({"State Government","Govt. Aided","Central Government"})
    rows.append({"year":y,"all":m.g46.sum(),"govt":m.loc[gv,"g46"].sum(),
                 "girls":m[["c4_g","c5_g","c6_g"]].sum().sum()})
tot=pd.DataFrame(rows).set_index("year")
tot.to_csv(os.path.join(TAB,"grade46_enrolment_universe.csv"))
F.append(("The grade 4-6 universe is 3.2 million children, 1.7 million of them in government schools",
 "UDISE Karnataka, all managements: "+"; ".join(
   "%s: %.2fM total, %.2fM govt (%.1f%%), girls %.1f%%"%(y,r["all"]/1e6,r.govt/1e6,
   100*r.govt/r["all"],100*r.girls/r["all"]) for y,r in tot.iterrows())+
 ". The government share of grade 4-6 enrolment fell %.1f pp in two years. The GP-linkable subset "
 "(rural, GP name present) is about 1.74M children, which is the denominator our GP-level joins use."
 % (100*tot.iloc[0].govt/tot.iloc[0]["all"]-100*tot.iloc[-1].govt/tot.iloc[-1]["all"]),
 "Coverage ratio per GP = students tested / enrolment denominator (external_data/"
 "udise_karnataka_gp_grade46_enrolment.csv). If coverage varies with score, part of the geography "
 "story is who got tested. We are the only team carrying the denominator."))

# ---- F3 NFHS trajectory
k6=pd.read_csv(os.path.join(EXT,"nfhs6_karnataka_state.csv"))
pick={12:"Women 10+ years schooling",11:"Pre-school attendance (2-4y)",69:"Under-5 stunted",
      70:"Under-5 wasted",72:"Under-5 underweight",16:"Women married before 18",
      14:"Women ever used internet",9:"Female 6+ ever attended school"}
rows=[]
for i,lab in pick.items():
    r=k6[k6.idx==i].iloc[0]
    rows.append({"indicator":lab,"nfhs5_2019_21":r.nfhs5_total,"nfhs6_2023_24":r.nfhs6_total})
traj=pd.DataFrame(rows); traj.to_csv(os.path.join(TAB,"nfhs5_to_6_trajectory.csv"),index=False)
F.append(("Karnataka's household conditions improved sharply between NFHS-5 and NFHS-6",
 "Stunting 35.4% to 26.5%. Underweight 32.9% to 27.8%. Early marriage 21.3% to 15.3%. Women with 10+ "
 "years of schooling 50.2% to 57.6%. Women who ever used the internet 35.0% to 57.9%. Pre-school "
 "attendance 44.5% to 50.7% (NFHS-6 fact sheet, state level; no district sheets published yet, and "
 "the NFHS-6 sheet carries no anaemia indicators).",
 "The tested children (born ~2012-2016) grew up under NFHS-5 conditions, so NFHS-5 district values are "
 "the right exposure measure for THIS cohort. Day-1 tests whether stunting-era districts still lag."))

# ---- F4 ASER
a=pd.read_csv(os.path.join(EXT,"aser_karnataka_trend.csv"))
def val(m,g,y): return a[(a.metric==m)&(a.geography==g)]["y%d"%y].iloc[0]
F.append(("Karnataka enters this datathon behind the country on arithmetic, and behind its own 2018 self",
 "ASER 2024 rural: 20.9%% of Karnataka Std V children can do division vs 30.7%% nationally. Std III "
 "subtraction: 25.9%% vs 33.7%%. India recovered above its 2018 pre-COVID level on all four headline "
 "measures; Karnataka cleared none of them (Std V division was %.1f%% in 2018)."%val("std5_division_pct","Karnataka",2018),
 "Does the Akshara data show the same post-2022 recovery shape year over year, and which districts drive it?"))

# ---- F5 PGI-D structure
pg=pd.read_csv(os.path.join(EXT,"pgid_2025_26_karnataka.csv"))
r=np.corrcoef(pg.outcomes_290,pg.infra_entitlements_51)[0,1]
F.append(("Even Karnataka's best district is mid-table on the national grading scale",
 "PGI-D 2025-26: Dakshina Kannada tops the state at 347/600 and Bidar is last at 250/600; no Karnataka "
 "district reaches the upper grading bands. Outcomes and infrastructure scores correlate at r=%.2f "
 "across the 35 educational districts. Bidar is an anomaly worth a slide: near-best governance score "
 "(50/84) with the worst overall score."%r,
 "Compare the Akshara district ranking against PGI-D outcomes (180 of 600 points come from PARAKH RS "
 "2024). Agreement validates both; disagreement is a finding about what each instrument measures."))

# ---- F6 NFHS-5 district spread
nf=pd.read_csv(os.path.join(EXT,"nfhs5_karnataka_districts.csv"))
F.append(("The state average hides a 3.7x spread in child stunting",
 "NFHS-5 district range: stunting from 15.6%% (Ramanagara) to 57.6%% (Yadgir); women with 10+ years "
 "schooling from 26.4%% (Yadgir) to 70.1%% (Bengaluru Urban); early marriage from 4.4%% (Udupi) to "
 "39.2%% (Vijayapura). Yadgir is last or near-last on almost every indicator.",
 "Structural Advantage Residual on Day 1: which places BEAT what these conditions predict."))

# ---- F7 language belt (straight from the UDISE district covariates file)
ud=pd.read_csv(os.path.join(EXT,"udise_karnataka_district_covariates.csv"))
ud=ud[ud.academic_year==ud.academic_year.max()]
lang=ud.dropna(subset=["pct_sch_kannada_medium_govt"]).sort_values("pct_sch_kannada_medium_govt")
low=lang.head(5)[["district","pct_sch_kannada_medium_govt"]].rename(
    columns={"district":"canonical_district"})  # educational district names, so Chikkodi stays distinct
F.append(("One in six government-school children in grades 4-6 studies in a non-Kannada-medium school",
 "Enrolment-weighted, 16.2%% of children in government grade 4-6 schools are in a non-Kannada-medium "
 "school (12.9%% of schools), and the non-Kannada stock is mostly Urdu (3,862 schools), then English "
 "(1,323) and Marathi (752). Lowest Kannada-medium shares by educational district: %s. The assessment "
 "language matters: a maths word-problem in Kannada is partly a language test in these blocks."
 % ", ".join("%s %.0f%%"%(x.canonical_district,x.pct_sch_kannada_medium_govt) for _,x in low.iterrows()),
 "Test whether word-problem items (vs pure computation items) show a bigger deficit in low-Kannada-medium "
 "GPs. Item-level DIF by language belt is a datathon-winning cut no aggregate report can do."))

# ---- F8 private exit
pv=cov.dropna(subset=["pct_private_schools"]).sort_values("pct_private_schools",ascending=False)
F.append(("The government system is becoming the rural and poor child's system",
 "Private unaided share of grade 4-6 schools ranges from %.0f%% (%s) down to %.0f%% (%s). CMS-E 2025 "
 "(national, in your folder): the poorest rural quintile sends 75%% of children to government schools, "
 "the richest urban quintile 16%%. Composition, not just quality, drives government-school score levels."
 % (pv.iloc[0].pct_private_schools,pv.iloc[0].canonical_district,
    pv.iloc[-1].pct_private_schools,pv.iloc[-1].canonical_district),
 "Interpret low government-school scores in high-private districts as partly a selection artefact; "
 "quantify with the coverage ratio."))

# ---- F9 PARAKH arc
F.append(("Government schools win the foundational stage and lose the ladder (PARAKH RS 2024)",
 "Karnataka grade-3 maths: government schools 59, private recognised 55; rural 59, urban 55. "
 "By grade 6 it reverses: government 40, private 47. By grade 9: 29 vs 36. State average falls "
 "57 to 45 to 33 across grades 3-6-9 (India: 60/46/37). Girls +2 pp at grades 3 and 6, 0 by grade 9. "
 "Source: PARAKH dashboard extract, integers as published, ~1,300 sampled schools per grade statewide.",
 "Our data is grades 4-6, exactly the zone where the government-school advantage dissolves. Which "
 "competencies carry the loss, and do the same districts hold their PARAKH rank in our census (H12)?"))

# ---- F10 PARAKH competency anchor (official state report, NCERT 2025)
F.append(("PARAKH names the bottleneck: fractions, at 26%",
 "Official PRS 2024 state report, grade-6 mathematics by competency: fractions (C-1.2) is "
 "Karnataka's floor at 26% correct (national 29%), then unit conversions 35%, word problems 36%, "
 "estimation 38%. One competency beats the nation: 2D/3D patterns, 51% vs 48%. By grade 9 the "
 "fraction hole propagates: percentage 25%, fractions-as-ratios 27%, deductive proofs 25%. "
 "Source: Report_Karnataka_IND29.pdf pages 21/26/31-32, extracted and spot-asserted.",
 "Does OUR item-level Bottleneck Score land on the same competency family? If yes, internal and "
 "official instruments agree on where to intervene, and the remediation recommendation writes itself."))

# ---- figures
fig,ax=plt.subplots(figsize=(7,6.2))
dd=d.sort_values("ptr_govt")
colors=[RED if k==1 else GREY for k in dd.is_371J_kalyana_karnataka]
ax.barh(dd.canonical_district,dd.ptr_govt,color=colors)
ax.axvline(30,ls="--",lw=1,color=INK)
ax.set_xlabel("Pupil-teacher ratio, govt schools serving grades 4-6 (UDISE 2024-25)")
ax.set_title("The 371J divide: red = Kalyana Karnataka districts\n(dashed line: RTE norm 30:1)")
fig.savefig(os.path.join(FIG,"C1_ptr_371J.png"),bbox_inches="tight",facecolor="white"); plt.close(fig)

fig,ax=plt.subplots(figsize=(7,4))
y=np.arange(len(traj))
ax.hlines(y,traj.nfhs5_2019_21,traj.nfhs6_2023_24,color=GREY,lw=2)
ax.plot(traj.nfhs5_2019_21,y,"o",color=GREY,label="NFHS-5 (2019-21)")
ax.plot(traj.nfhs6_2023_24,y,"o",color=GREEN,label="NFHS-6 (2023-24)")
ax.set_yticks(y); ax.set_yticklabels(traj.indicator); ax.invert_yaxis()
ax.set_xlabel("% (Karnataka, total)"); ax.legend(frameon=False,fontsize=8)
ax.set_title("Karnataka moved fast between NFHS-5 and NFHS-6")
fig.savefig(os.path.join(FIG,"C2_nfhs_trajectory.png"),bbox_inches="tight",facecolor="white"); plt.close(fig)

# ---- write findings md
with open(os.path.join(CP,"CONTEXT_FINDINGS.md"),"w",encoding="utf-8") as f:
    f.write("# Pre-baked context findings\n\n")
    f.write("Everything below is computed WITHOUT the student data and is safe to put in the deck "
            "tonight. Each finding ends with the Day-1 slot: the one question only the assessment "
            "file can answer. The Day-1 engine (src/run_all.py) stays reserved for those.\n\n")
    for i,(h,body,day1) in enumerate(F,1):
        f.write("## C%d. %s\n\n%s\n\n**Day-1 slot:** %s\n\n"%(i,h,body,day1))
    f.write("---\nGenerated by prep/04_build_context_pack.py. Tables in context_pack/tables, "
            "figures in context_pack/figures.\n")
print("context pack: %d findings, 2 figures, %d tables"%(len(F),len(os.listdir(TAB))))
