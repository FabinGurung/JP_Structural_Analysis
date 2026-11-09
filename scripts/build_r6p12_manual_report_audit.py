#!/usr/bin/env python3
"""R6.12 manual arithmetic comparison, NOT a new ETABS or structural approval."""
from __future__ import annotations
import json, math, hashlib
from pathlib import Path
from collections import Counter
from html import escape

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/"site"
SHA="f122904444a2e2f75230d9d4e41da0093d050da25c6e8140c86d466b7e37cc52"
REPORT=ROOT/"registry/r6p6_reported_structural_results.v0.1.json"
SEIS=ROOT/"registry/g15-chapter02-seismic-facts.v0.1.json"
F3=ROOT/"registry/g15-gate18-report-mass-f3-source.v0.1.json"
MODEL=ROOT/"registry/r6p5_etabs21_governing_pair.v0.1.json"
OUT=SITE/"data/r6p12-manual-report-audit.json"
PAGE=SITE/"projects/pokhara-g15/manual-verification.html"
PROJECT=SITE/"projects/pokhara-g15/report.html"

def load(path): return json.loads(path.read_text(encoding="utf-8"))
def steel(d,space): return math.pi*d*d/4*1000/space

def calculate():
    r,s,f3,m=[load(p) for p in (REPORT,SEIS,F3,MODEL)]
    assert r["source"]["report_sha256"]==s["source"]["sha256"]==f3["source_pdf"]["sha256"]==SHA
    assert m["decision"]["state"]=="USER_CONFIRMED_CURRENT_GOVERNING_ETABS21_ULS_SLS"
    assert not m["admission_gates"]["engineering_approval"]
    assert r["foundation"]["report_status"]=="NOT SAFE IN ONE WAY SHEAR"
    checks=[]
    def add(chapter,subject,equation,calculated,printed,status,scope):
        checks.append({"chapter":chapter,"subject":subject,"equation":equation,
            "calculated":calculated,"historical_report":printed,"status":status,
            "scope":scope,"current_etabs21_solver_result":False})
    h=s["seismic"]["height_m"]
    mass=r["original_mass"]["source_masses"][:3]
    g=r["original_mass"]["conditional_g_m_per_s2"]
    weights=[z["value"]*g/1000 for z in mass]
    W=sum(weights)
    coeff=.35*2.25/(4*1.5)
    ULS=.131*W
    SLS=.126*W
    add("2.1","M20 concrete modulus","5000*sqrt(20) MPa",round(5000*math.sqrt(20),3),25000,
        "CONFLICT","The 25,000 MPa report material table differs from its own 22,360.68 MPa ETABS member excerpt.")
    add("2.6","Empirical period","1.25*0.075*(9.144**0.75) s",round(1.25*.075*h**.75,6),.493,
        "REPRODUCED","Only the empirical worksheet calculation; not modal solution.")
    add("2.6","ULS coefficient","0.35*2.25/(4*1.5)",coeff,.131,"CONFLICT",
        "Rounded 0.131 is used in report base-shear table; full coefficient is 0.13125.")
    add("2.6","SLS coefficient","0.2*0.35*2.25/1.25",.126,.126,"REPRODUCED",
        "Depends on historical site and spectral coefficients.")
    add("5.10","Seismic weight from three printed mass entries","696661.02*9.80665/1000 kN",
        round(W,6),6831.9109,"CONDITIONAL",
        "kg is an inference because the original story mass table does not print its unit; base mass is omitted.")
    add("5.1/5.12","ULS static base shear with printed rounded coefficient","0.131*W kN",
        round(ULS,6),894.9803,"REPRODUCED","Historical static coefficient arithmetic, not actual ETABS21 reactions.")
    add("5.1/5.12","SLS static base shear","0.126*W kN",round(SLS,6),860.8208,
        "REPRODUCED","Historical static coefficient arithmetic, not actual ETABS21 reactions.")
    add("5.1","ULS base-shear rounding sensitivity","(0.13125-0.131)*W kN",
        round((coeff-.131)*W,6),0,"CONFLICT",
        "Unrounded worksheet coefficient increases historical ULS force by 1.708 kN.")
    H=[3.048,6.096,9.144]
    den=sum(w*hi for w,hi in zip(weights,H))
    distributed=[ULS*w*hi/den for w,hi in zip(weights,H)]
    add("5.1","Conditional three-level equivalent static loads","Fi=V*Wi*hi/sum(Wj*hj), k=1",
        [round(x,4) for x in distributed],round(ULS,4),"CONDITIONAL",
        "Three computed level forces sum to the ULS total; not source ETABS floor forces.")
    rows=r["modal"]["source_rows"]
    first=next(x["mode"] for x in rows if x["sum_ux"]>=.9 and x["sum_uy"]>=.9)
    add("5.5","First mode achieving 90% in both axes","min(mode: sumUX>=.9 and sumUY>=.9)",
        first,6,"CONFLICT","At mode 5 both source cumulative ratios already exceed 0.90.")
    add("5.5","Narrative frequency","1/0.185 Hz",round(1/.185,6),5.405,"REPRODUCED",
        "0.185 s does not appear as an exact printed modal period; source mode 6 is 0.187 s.")
    add("5.5","Fundamental mode period","first source modal row",rows[0]["period_s"],.185,
        "CONFLICT","The first printed modal period is 0.618 s; 0.185 s is not the fundamental.")
    du=.025/4*h*1000
    ds=.006*h*1000
    v=r["reported_serviceability"]
    add("5.6","ULS displacement bound","0.025/4*9144 mm",round(du,4),57.15,"REPRODUCED",
        "Printed actual displacement 22.9069 mm not independently recomputed.")
    add("5.6","SLS displacement bound","0.006*9144 mm",round(ds,4),54.864,"REPRODUCED",
        "Printed actual displacement 12.846306 mm not independently recomputed.")
    add("5.6","ULS reported displacement utilization","22.9069/57.15",
        round(v["uls_max_displacement_mm"]/du,6),"source SAFE","CONDITIONAL",
        "Compares source numbers only; no complete lateral response recreation.")
    add("5.6","SLS reported displacement utilization","12.846306/54.864",
        round(v["sls_max_displacement_mm"]/ds,6),"source SAFE","CONDITIONAL",
        "Compares source numbers only.")
    add("5.7","ULS reported drift utilization","0.00288/0.00625",
        round(v["uls_max_storey_drift_ratio"]/.00625,6),"source SAFE","CONDITIONAL",
        "Reported maximum drift has not been independently solved.")
    add("5.7","SLS reported drift utilization","0.002174/0.006",
        round(v["sls_max_storey_drift_ratio"]/.006,6),"source SAFE","CONDITIONAL",
        "Reported maximum drift has not been independently solved.")
    add("5.8","ULS story-3 torsion X and Y ratios","18.765/17.779; 22.907/19.146",
        [round(18.765/17.779,5),round(22.907/19.146,5)],[1.06,1.20],
        "CONDITIONAL","Arithmetic matches rounded report table; native displacements are not verified.")
    add("5.9","X adjacent-storey stiffness ratios","K1/K2; K2/K3",
        [round(210766.538/105412.441,5),round(105412.441/58488.585,5)],
        "source no soft storey","CONDITIONAL","Printed stiffness comparisons, not current ETABS21 stiffness.")
    add("5.9","Y adjacent-storey stiffness ratios","K1/K2; K2/K3",
        [round(164985.671/93272.914,5),round(93272.914/61139.877,5)],
        "source no soft storey","CONDITIONAL","Printed stiffness comparisons, not current ETABS21 stiffness.")
    add("5.10","Top-storey mass decrease relative to second","(274062.74-152521.81)/274062.74",
        round((274062.74-152521.81)/274062.74,6),"source mass irregularity OK",
        "CONDITIONAL","Whether the light-roof/exemption rule applies is unverified.")
    add("5.15","Ground-floor X/Y centre eccentricities","100*abs(CM-CR)/L",
        [round(100*abs(9.9295-10.0517)/19.9,3),round(100*abs(5.2078-4.9616)/11.1,3)],
        [.61,2.22],"CONDITIONAL","Matches source rounding; not an accidental-eccentricity FE calculation.")
    add("6.1","C1 scheduled steel ratio","100*(8*pi*16**2/4)/(400*400)",
        round(100*(8*math.pi*16**2/4)/160000,5),1.00,"REPRODUCED",
        "Nominal area check only; P-M capacity remains unverified.")
    add("6.2","GF B46 reported negative design moment","-99.4853-14.7682 kN*m",
        round(-99.4853-14.7682,5),-114.2535,"REPRODUCED",
        "Printed sample calculation only; not independently solved FEM demand.")
    add("6.2","GF B19 reported negative design moment","-60.1122-19.4579 kN*m",
        round(-60.1122-19.4579,5),-79.5701,"REPRODUCED",
        "Printed sample calculation only.")
    add("6.3","Slab self-weight at 125 mm and 25 kN/m3","0.125*25 kPa",3.125,3.13,
        "REPRODUCED","120 mm general schedule vs 125 mm worked sample remains unresolved.")
    add("6.3","Sample slab ultimate load","1.5*(3.125+1+1+2) kPa",10.6875,10.69,
        "REPRODUCED","Only sample load arithmetic, not slab strength/deflection.")
    add("6.3","Sample slab provided steel","pi*8**2/4*1000/150 mm2/m",
        round(steel(8,150),4),"8 mm at 150 mm","REPRODUCED","Area arithmetic only.")
    add("6.4","F3 factored upward pressure from column","1.5*571/(2.1*2.1) kPa",
        round(1.5*571/(2.1**2),6),194.22,"REPRODUCED","F3 remains NOT SAFE IN ONE WAY SHEAR.")
    add("6.4","F3 if reported total 600 kN were factored","1.5*600/(2.1*2.1) kPa",
        round(1.5*600/(2.1**2),6),194.22,"CONFLICT",
        "Worksheet's 194.22 follows 571 kN not its own 600 kN including selfweight.")
    add("6.4","F3 average service bearing","600/(2.1*2.1) kPa",
        round(600/(2.1**2),6),160,"CONDITIONAL",
        "160 kPa is printed allowable SBC, not independently reviewed soil capacity.")
    add("6.4","F3 cover-based effective depth scenario","450-50-12/2 mm",
        394,f3["f3_source"]["sheet_effective_depth_d_mm"],"CONFLICT",
        "Reported d=423.46278 mm conflicts with cited 50 mm cover scenario.")
    add("6.4","F3 nominal steel area per metre","pi*12**2/4*1000/150",
        round(steel(12,150),4),"12 mm at 150 mm","REPRODUCED",
        "Does not clear F3 one-way shear.")
    add("6.4","CF1 average service bearing","501/(4*1.5) kPa",83.5,160,
        "CONDITIONAL","Average only. Eccentricity, bearing variation and settlement unverified.")
    add("6.5","Stair factored flight load","1.5*11.41 kPa",17.115,17.11,
        "REPRODUCED","Printed figure rounded; 150 vs 127 mm waist is unresolved.")
    add("6.5","Stair factored line load (report-rounded)","17.11*1.2 kN/m",
        round(17.11*1.2,5),20.53,"REPRODUCED","No independent bending-moment solution.")
    add("6.5","Stair 12 mm at 127 mm provided steel","pi*12**2/4*1000/127 mm2/m",
        round(steel(12,127),4),995.26,"CONFLICT",
        "Actual nominal area 890.53 mm2/m differs from worksheet provided steel.")
    add("6.5","Stair general/worksheet depth","150-127 mm",23,0,"CONFLICT",
        "Original general waist slab 150 mm, worksheet adopts 127 mm.")
    for part,subject in [
        ("5.2-5.4","Complete signed axial/shear/moment member results"),
        ("5.5","Native modal eigenvectors and participation"),
        ("5.6-5.9","Native drift/displacement/torsional output"),
        ("5.12-5.14","Exact ULS/SLS support reactions and footing shear"),
        ("6.1-6.5","Full reinforcement capacity and complete project design")]:
        add(part,subject,"Requires matched physical-source analysis",None,
            "archived report only","NOT_REPRODUCED",
            "No claim of matching current ETABS21 source solver or independent design acceptance.")
    add("6.4","F3 one-way shear status","Preserve original adverse verdict",
        "NOT SAFE IN ONE WAY SHEAR","NOT SAFE IN ONE WAY SHEAR","ENGINEERING_HOLD",
        "Neither rounded printed shear stresses nor other arithmetic allows this warning to be cleared.")
    assert len(checks)>=40
    assert not r["readiness"]["professional_engineering_approval"]
    return {"schema":"jp.structural.r6p12.manual_historical_report_audit.v0.1",
        "historical_report_drive_id":r["source"]["report_drive_id"],
        "historical_report_sha256":SHA,"current_etabs21_source_registry":str(MODEL.relative_to(ROOT)),
        "source_model_solver_reproduced":False,"checks":checks,
        "counts":dict(Counter(x["status"] for x in checks)),
        "unsupported_source_shells_excluded":12,"F3_one_way_shear_unsafe":True,
        "full_seismic_mass_verified":False,"engineering_approval":False}

def render(data):
    statuses={"REPRODUCED":"Arithmetic matched","CONFLICT":"Source conflict",
              "CONDITIONAL":"Conditional only","NOT_REPRODUCED":"Unverified solver result",
              "ENGINEERING_HOLD":"Engineering HOLD"}
    cards=[]
    for idx,row in enumerate(data["checks"]):
        def val(x): return escape(json.dumps(x,ensure_ascii=False) if isinstance(x,list) else str(x))
        cards.append(f'<article class="item" id="check-{idx+1}"><div class="top"><h3>{val(row["chapter"])} · {val(row["subject"])}</h3>'
             f'<span>{statuses[row["status"]]}</span></div><p><b>Working:</b> <code>{val(row["equation"])}</code></p>'
             f'<p><b>Our result:</b> {val(row["calculated"])}</p>'
             f'<p><b>Archived report:</b> {val(row["historical_report"])}</p>'
             f'<p>{val(row["scope"])}</p></article>')
    counters=" · ".join(f"{statuses[k]}: {n}" for k,n in data["counts"].items())
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>R6.12 manual verification · Pokhara G+1.5</title>
<link rel="stylesheet" href="../../styles.css">
<style>body{{background:#f6f8f7;color:#1c3948}}main{{max-width:1080px;margin:auto;padding:22px 13px 60px}}
.hero{{background:#194b64;color:white;padding:25px;border-radius:13px}}.hero p{{color:#ecf4f8;line-height:1.5}}
.hero a{{color:#cfeeff}}.hold{{border:1px solid #bc9e76;background:#fff1db;padding:16px;border-radius:9px;margin:16px 0}}
.item{{border:1px solid #d4e0e5;background:white;padding:17px;margin:11px 0;border-radius:9px}}
.item h3{{margin:0;font-size:1rem}}.item p{{font-size:.87rem;line-height:1.55;overflow-wrap:anywhere}}
.top{{display:flex;align-items:start;justify-content:space-between;gap:15px;flex-wrap:wrap}}
.top span{{font-size:.73rem;border:1px solid #bacdd5;padding:4px 7px;border-radius:6px}}
.item code{{white-space:normal}}@media(max-width:550px){{.hero{{padding:17px}}.item{{padding:12px}}}}</style>
</head><body><main><div class="hero"><small>R6.12 · report arithmetic review</small>
<h1>Manual verification of the archived structural report</h1>
<p>Source values vs hand arithmetic, including mismatches and missing structural analysis evidence.</p>
<p><a href="report.html">Back to project report</a> ·
<a href="../../worked-calculations.html">Earlier worked calculations</a> ·
<a href="../../data/r6p12-manual-report-audit.json">Calculation JSON</a></p></div>
<div class="hold"><strong>Engineering HOLD:</strong> Original ULS/SLS ETABS21 inputs have not been re-solved.
The older PDF mixes ETABS20 and ETABS21 reporting. Twelve shells remain unsupported;
F3 remains NOT SAFE IN ONE WAY SHEAR. None of these arithmetic checks approves construction.</div>
<p>{escape(counters)} · {len(data["checks"])} source comparisons</p>
{''.join(cards)}
<p>Provenance: governed original report PDF SHA-256 {SHA}.
This is a de-identified derivative of reported quantities, not a copy of the original PDF.</p>
</main></body></html>'''

def export():
    data=calculate()
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(data,indent=2,ensure_ascii=False,sort_keys=True)+"\n",encoding="utf-8")
    PAGE.parent.mkdir(parents=True,exist_ok=True)
    PAGE.write_text(render(data),encoding="utf-8")
    if PROJECT.exists():
        body=PROJECT.read_text(encoding="utf-8")
        anchor='<section class="rb-card project-tools" id="project-hand-calculations"'
        injected=('<section class="rb-card project-tools" id="project-r6p12-manual">'
             '<h2>Archived report: manual verification</h2>'
             '<p>Independent arithmetic, discrepancies, missing model evidence and engineering holds.</p>'
             '<p><a href="projects/pokhara-g15/manual-verification.html">Open R6.12 manual verification</a></p></section>\n')
        if 'id="project-r6p12-manual"' not in body:
            if anchor not in body: raise ValueError("Project report hand-calculation anchor missing")
            PROJECT.write_text(body.replace(anchor,injected+anchor,1),encoding="utf-8")
    return data

if __name__=="__main__":
    d=export()
    print(f"R6.12: {len(d['checks'])} manual source comparisons; F3 and engineering HOLD retained.")
