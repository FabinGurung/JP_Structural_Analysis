#!/usr/bin/env python3
"""G15 Gate21: run real OpenSees and export an inspectable non-approved SAR.

Not an original ETABS reproduction or construction-approved RC design. Every
missing input is classified as an assumption or source-bounded inference.
"""
from __future__ import annotations
import argparse,csv,hashlib,html,json,math,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.run_g15_open_3d import SAMPLE,validate,solve,source
from scripts.build_g15_gate18_mass_f3 import build as gate18
from scripts.build_g15_gate20_crosswalk import build as gate20

PDF_SHA="f122904444a2e2f75230d9d4e41da0093d050da25c6e8140c86d466b7e37cc52"
PDF_ID="1TpWUmOdrcQqOpkN6qvmhZ12KrYaNABBM"
DOCX_ID="19q3h_rBHMP14fbkVcZ424iNJpomR7Wyz"
PARTS=("Ni","Vyi","Vzi","Ti","Myi","Mzi","Nj","Vyj","Vzj","Tj","Myj","Mzj")
PFX="g15-gate21"

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def fmt(x):return format(float(x),".6f")
def default():
    inp=dict(SAMPLE)
    inp["floor_weights_kN"]=[q["conditional_seismic_W_kN"] for q in gate18()["source_floor_conditional_weights"]]
    return validate(inp)

def get_inputs(path=None):
    inp=default()
    ref={
      "floor_weights_kN":("CONDITIONAL_SOURCE","Original revised PDF physical p34 story mass table; Gate18 source masses; standard gravity 9.80665m/s2","Mass unit kg not printed; not verified true gravity/mass source"),
      "beam_width_mm":("ASSUMED","G15 source-derived public working grid Gate03 BEAM section","Individual source beam sections not verified"),
      "concrete_E_MPa":("ASSUMED","G15 public grid working M20 modulus 22360.6798MPa","Native ETABS concrete material and density conflict unresolved"),
      "C_design":("ASSUMED","Existing G15 OpenSees SAMPLE Cd 0.131; NBC105:2025 6.2 formula","Not calibrated to authentic municipality, site hazard, soil or spectrum"),
      "T_seconds":("ASSUMED","Existing G15 OpenSees SAMPLE 0.493s; Gate17 source modal-period conflict","Original source period and eigenanalysis not verified"),
      "stiffness":("ASSUMED","G15 OpenSees ULS beam 0.35/column 0.70 EI modifier numerical hypothesis","Not member-specific source stiffness or independently code-accepted"),
      "bridges":("ASSUMED","G15 Gate03 grid two unverified connectors indices 30,31","Not verified physical beam spans/repetition")
    }
    if path:
        incoming=json.loads(Path(path).read_text(encoding="utf-8"))
        if set(incoming)!={"solver_request","provenance"}:raise ValueError("Require solver_request and provenance")
        inp=validate(incoming["solver_request"])
        p=incoming["provenance"]
        if not isinstance(p,dict) or set(p)!=set(ref):raise ValueError("Require all input provenance")
        for key,item in p.items():
            if not isinstance(item,dict) or set(item)!={"class","citation","uncertainty"}:raise ValueError("Invalid parameter provenance")
            if item["class"] not in ("ASSUMED","CONDITIONAL_SOURCE","SOURCE_REPORTED_UNVERIFIED"):raise ValueError("Cannot assert verified physical source")
            if not all(isinstance(item[k],str) and len(item[k].strip())>=8 for k in item):raise ValueError("Empty citation/uncertainty")
        ref={k:(v["class"],v["citation"],v["uncertainty"]) for k,v in p.items()}
    return inp,[{"id":k,"value":inp[k],"class":v[0],"citation":v[1],"uncertainty":v[2]} for k,v in ref.items()]

def calculate(input_path=None):
    inp,refs=get_inputs(input_path)
    src=source()
    original=gate18();g=gate20()
    assert original["source_report_sha256"]==g["source_report_sha256"]==PDF_SHA
    assert g["accepted_gate_count"]==0
    numerical=solve(inp)  # ACTUAL OpenSees elasticBeamColumn 3D solver
    assert len(numerical["cases"])==5
    assert numerical["model_counts"]["members"] in (159,165)
    levels=src["floor_levels_mm"]
    floors=[{"story":i+1,"height_m":(levels[i+1]-levels[i])/1000,
             "elevation_m":levels[i+1]/1000,
             "Wi_kN":inp["floor_weights_kN"][i],
             "Fi_kN":numerical["esm"]["floor_forces_kN"][i]} for i in range(3)]
    cases=[];forces=[]
    for c in numerical["cases"]:
        assert c["equilibrium_residual_kN"]<.001
        assert c["equilibrium_moment_residual_kNm"]<.001
        disp={(d["node"],d["level"]):d for d in c["node_displacements"]}
        chords=[]
        for level in (1,2,3):
            vals=[]
            for label,*_ in src["column_positions_mm"]:
                a=disp[(label,level)];b=disp.get((label,level-1),{"ux_mm":0,"uy_mm":0})
                vals.append(math.hypot(a["ux_mm"]-b["ux_mm"],a["uy_mm"]-b["uy_mm"]))
            delta=max(vals)
            chords.append({"story":level,"max_elastic_chord_mm":delta,
              "elastic_chord_ratio":delta/(floors[level-1]["height_m"]*1000),
              "NBC_drift_pass":False,"NBC_drift_evaluated":False})
        extreme=None
        for v in c["member_signed_local_end_forces"]:
            assert len(v["signed"])==12 and all(math.isfinite(z) for z in v["signed"])
            row=dict(case=c["case"],member=v["id"])
            row.update(zip(PARTS,v["signed"]))
            forces.append(row)
            for key in ("Mzi","Mzj"):
                if extreme is None or abs(row[key])>abs(extreme["signed_kNm"]):
                    extreme=dict(member=v["id"],component=key,signed_kNm=row[key])
        cases.append({"name":c["case"],"roof_max_mm":c["max_roof_horizontal_displacement_mm"],
           "reactions_kN_xyz":c["reaction_kN_xyz"],
           "force_residual_kN":c["equilibrium_residual_kN"],
           "moment_residual_kNm":c["equilibrium_moment_residual_kNm"],
           "max_signed_Mz":extreme,"story_chord_metrics":chords,
           "member_design_approved":False})
    assert len(forces)==len(cases)*numerical["model_counts"]["members"]
    total=sum(inp["floor_weights_kN"])
    r={
      "schema":"jp.structural.g15.gate21.open_reproducible_sar.v0.1",
      "source_pdf_id":PDF_ID,"source_pdf_sha256":PDF_SHA,"source_docx_id":DOCX_ID,
      "source_citations":[
       "Original revised report PDF physical pp9-11 floor plans and p42 column schedule",
       "Original revised report p25 ETABS seismic weight 6831.9109kN",
       "Original revised report p34 story mass values, kg inferred, not printed",
       "Original revised report p61 footing F3 NOT SAFE IN ONE WAY SHEAR",
       "NBC105:2025 equivalent-static distribution clauses 6.2 and 6.3"],
      "grid_file":"site/data/g15-working-grid.public.v0.1.json",
      "grid_SHA256":digest(ROOT/"site/data/g15-working-grid.public.v0.1.json"),
      "request_SHA256":hashlib.sha256(json.dumps(inp,sort_keys=True).encode()).hexdigest(),
      "inputs":inp,"provenance":refs,"solver":"OpenSeesPy elasticBeamColumn 3D, six DOFs/node",
      "model_state":"SOURCE_DERIVED_HYPOTHETICAL_UNVERIFIED","counts":numerical["model_counts"],
      "equations":{"W":"sum(Wi)","V":"Cd * sum(Wi)",
        "Fi":"V * Wi * hi^k / sum(Wj * hj^k)",
        "chord":"max at same column sqrt((delta Ux)^2+(delta Uy)^2)/storey height",
        "local_actions":"OpenSeesPy eleResponse(memberTag, localForce): 12 signed components",
        "force_balance":"sum(applied forces) + sum(support reactions) = 0",
        "moment_balance":"sum(global support moments + r cross support forces + applied moments) = 0"},
      "ESM":{"floor":floors,"W_kN":total,"W_reported_ETABS_kN":original["source_report_ETABS_seismic_W_kN"],
         "conditional_weight_gap_kN":original["source_report_ETABS_seismic_W_kN"]-total,
         "Cd":inp["C_design"],"period_s":inp["T_seconds"],"k":numerical["esm"]["distribution_exponent"],
         "V_kN":numerical["esm"]["base_shear_kN"]},
      "gravity_warning":"GRAVITY applies source-story equivalent seismic W equally to 23 column nodes, NOT reconstructed dead/live/slab/wall load assignments",
      "case_count":len(cases),"signed_end_action_count":len(forces),"cases":cases,
      "source_gates_open":g["gate_count"]-g["accepted_gate_count"],
      "source_actual_mass_composition_verified":False,
      "model_ETABS_source_verified":False,"real_slab_and_wall_assignments_verified":False,
      "modal_performed":False,"accidental_eccentricity_performed":False,
      "p_delta_performed":False,"member_rebar_design_performed":False,
      "ULS_SLS_design_combinations_performed":False,
      "F3_verdict":"NOT SAFE IN ONE WAY SHEAR",
      "engineering_approval":False,
      "scope":"Five real solved linear-elastic numerical frame cases; no completed building design report"
    }
    return r,forces

def table(headers,rows):
    def escape(x):return html.escape(str(x))
    return "<table><thead><tr>"+"".join("<th>"+escape(v)+"</th>" for v in headers)+"</tr></thead><tbody>"+"".join(
       "<tr>"+"".join("<td>"+escape(v)+"</td>" for v in row)+"</tr>" for row in rows)+"</tbody></table>"

def report_html(d):
    e=d["ESM"]
    refs=table(["Parameter","Input","Status","Citation","Uncertainty"],
      [(x["id"],json.dumps(x["value"]),x["class"],x["citation"],x["uncertainty"]) for x in d["provenance"]])
    floors=table(["Story","Height m","Conditional Wi kN","ESM Fi kN"],[
      (x["story"],fmt(x["elevation_m"]),fmt(x["Wi_kN"]),fmt(x["Fi_kN"])) for x in e["floor"]])
    cases=table(["OpenSees solved case","Roof mm","Reaction XYZ kN","Force err kN","Moment err kNm","Largest signed Mz kNm"],
      [(x["name"],fmt(x["roof_max_mm"]),",".join(fmt(v) for v in x["reactions_kN_xyz"]),
       fmt(x["force_residual_kN"]),fmt(x["moment_residual_kNm"]),fmt(x["max_signed_Mz"]["signed_kNm"])+" "+x["max_signed_Mz"]["member"]) for x in d["cases"]])
    chords=table(["Case","Story","Elastic chord mm","Chord/height","NBC compliance"],
       [(x["name"],s["story"],fmt(s["max_elastic_chord_mm"]),fmt(s["elastic_chord_ratio"]),"NOT EVALUATED")
         for x in d["cases"] for s in x["story_chord_metrics"]])
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>G15 OpenSees SAR numerical draft</title><style>
body{{margin:0 auto;max-width:1050px;padding:24px;color:#1e334b;background:white;font:14px/1.6 system-ui,Arial,sans-serif}}h1{{font-size:28px}}h2{{font-size:19px;border-bottom:2px solid #245e83;padding:5px 0;margin-top:30px}}
table{{border-collapse:collapse;width:100%;font-size:12px;margin:12px 0 22px}}th,td{{border:1px solid #cbd5df;padding:7px;text-align:left;vertical-align:top;overflow-wrap:anywhere}}thead{{background:#edf3f8}}
.alert{{border-left:4px solid #a43d31;background:#fff0ed;padding:12px}}.note{{border-left:4px solid #28618b;background:#edf4f9;padding:12px}}
nav{{display:flex;gap:9px;flex-wrap:wrap}}nav a,button{{border:1px solid #54758f;border-radius:5px;padding:9px;background:#fff;text-decoration:none;color:#13466b;cursor:pointer}}
code{{overflow-wrap:anywhere}}@media print{{nav{{display:none}}body{{padding:0}}tr{{break-inside:avoid}}h2{{break-after:avoid}}@page{{margin:16mm}}}}</style></head><body>
<small>JP STRUCTURAL ANALYSIS · GATE21 · REPRODUCIBLE OPEN NUMERICAL ENGINE</small>
<h1>G+1.5 Structural Analysis Report — OpenSees calculation draft</h1>
<p class="alert"><strong>NOT ENGINEERING APPROVED.</strong> Five actual OpenSees cases on a source-derived, hypothetical frame. Original PDF F3 footing: NOT SAFE IN ONE WAY SHEAR. No original ETABS model/source-complete design.</p>
<nav><button onclick="window.print()">Print / Save PDF</button><a href="g15-gate21-calculation-report.md" download>Markdown</a><a href="g15-gate21-signed-member-actions.csv" download>All signed CSV</a><a href="g15-gate21-report.v0.1.json" download>Open numerical JSON</a><a href="g15-gate21-manifest.json" download>SHA256 manifest</a><a href="../report.html">Report hub</a></nav>
<h2>1. Introduction and structural system</h2><p>Real OpenSeesPy 3D elasticBeamColumn with 6 DOF per node, {d['counts']['members']} working frame members and {d['counts']['nodes']} nodes. Five independently solved cases. {d['signed_end_action_count']} signed member/end result rows in downloadable CSV.</p>
<h2>2. Design basis, materials and input provenance</h2><p>Original revised report reference: private Drive PDF {PDF_ID}, SHA256 {PDF_SHA}; companion DOCX {DOCX_ID}. Source PDF physical pp9–11, p25, p34, p42 and p61. Source report calculations and model disagree on some concrete weights, live occupancy and actual slab extent; these are not concealed.</p>{refs}
<h2>3. Gravity, floor seismic weights and NBC105 equivalent-static actions</h2><div class="note">
Formula: Wi = Mi (inferred kg) × 9.80665 / 1000; W=sum Wi; V=Cd W; Fi=V Wi hi^k / sum(Wj hj^k). NBC105:2025 clauses 6.2–6.3 as implemented numerically. Coefficient Cd and T are working assumptions, NOT proven site values.</div>
<p>Source W = {fmt(e['W_reported_ETABS_kN'])} kN, conditional W = {fmt(e['W_kN'])} kN, assumed Cd = {e['Cd']}, assumed T = {e['period_s']} s, k = {fmt(e['k'])}, computed V = {fmt(e['V_kN'])} kN.</p>{floors}
<p class="alert"><b>Gravity load limitation:</b> {html.escape(d['gravity_warning'])}.</p>
<h2>4. OpenSees 3D structural model and equilibrium</h2><p>OpenSees linear elastic solves gravity and signed EQ±X/±Y; fixed columns, assumed beams and no physical shell diaphragm. Global force and moment equilibrium errors checked below 0.001. An equilibrium check does not authenticate the frame or loads.</p>
<h2>5. Storey displacement, elastic chord and member force diagrams data</h2>{cases}<p>These are computed elastic interstorey chord ratios at the same column; NOT accepted code drift. Member local axial/shear/torsion/moments Ni Vyi Vzi Ti Myi Mzi Nj Vyj Vzj Tj Myj Mzj are all in CSV, separately for each signed case; no non-concurrent force-envelope design claims.</p>{chords}
<h2>6. Structural members, slab and foundation checks</h2><p class="alert"><strong>F3 is NOT SAFE IN ONE WAY SHEAR</strong> (source PDF p61). Slab/beam/column reinforcement, concrete material source density, punching, bearing, settlement and actual signed load combinations have NOT been verified or approved. P-Delta, diaphragm eccentricity and modal responses have NOT been analyzed in this limited run.</p>
<h2>7. Reproducibility and engineering exclusions</h2><p>Rebuild via scripts/build_g15_gate21_report.py; OpenSees solver scripts/run_g15_open_3d.py. SHA256 grid: {d['grid_SHA256']}; request: {d['request_SHA256']}. Source acceptance gates outstanding: {d['source_gates_open']}. No signature, seal, certification or permit claim. All generated files have checksums in manifest.</p></body></html>"""

def report_md(d):
    p=["# G+1.5 OpenSees structural analysis numerical draft (NOT APPROVED)","",
       "## 1. Introduction and structural system",f"{d['case_count']} solved OpenSees cases; {d['counts']['members']} hypothetical members; {d['signed_end_action_count']} signed end-action records.",
       "## 2. Design basis and source provenance",
       "Original private PDF ID "+PDF_ID+" SHA256 "+PDF_SHA+"; original DOCX ID "+DOCX_ID]
    for x in d["provenance"]:
        p.append(x["id"]+" = "+json.dumps(x["value"])+": "+x["class"]+"; citation: "+x["citation"]+"; UNCERTAINTY: "+x["uncertainty"])
    q=d["ESM"]
    p.extend(["## 3. Gravity and seismic distribution","Wi=Mi(inferred kg)*9.80665/1000; W=sum Wi; V=Cd W; Fi=V Wi hi^k / sum(Wj hj^k).",
      "Source ETABS W="+fmt(q["W_reported_ETABS_kN"])+"kN; report-conditional W="+fmt(q["W_kN"])+"kN; OpenSees V="+fmt(q["V_kN"])+"kN.",
      "GRAVITY limitation: "+d["gravity_warning"],"## 4. OpenSees static 3D analysis","Source-derived hypothetical frame: six DOFs per node; independently verified force/moment equilibrium.",
      "## 5. Signed forces and elastic displacements"])
    for c in d["cases"]:
        p.append(c["name"]+": roof displacement "+fmt(c["roof_max_mm"])+"mm, force error "+fmt(c["force_residual_kN"])+"kN, moment error "+fmt(c["moment_residual_kNm"])+"kNm.")
        for s in c["story_chord_metrics"]:
            p.append("Story "+str(s["story"])+": max elastic chord "+fmt(s["max_elastic_chord_mm"])+"mm, ratio "+fmt(s["elastic_chord_ratio"])+"; NOT evaluated for NBC compliance.")
    p.extend(["Full signed 12-component member-end force CSV supplied with report.","## 6. Foundation F3 and design",
      "NOT SAFE IN ONE WAY SHEAR. Original F3 details, geotechnical evidence, design checks and structural approval pending.",
      "## 7. Validation and reproducibility","Open source scripts/build_g15_gate21_report.py + scripts/run_g15_open_3d.py; grid SHA256 "+d["grid_SHA256"]+".",
      "No original ETABS mass composition, diaphragm, torsion, P-Delta, modal, RC member design or statutory approval.",""])
    return "\n\n".join(p)

def export(directory,request_file=None):
    d,forces=calculate(request_file);root=Path(directory);root.mkdir(parents=True,exist_ok=True)
    js=root/(PFX+"-report.v0.1.json");ht=root/(PFX+"-calculation-report.html")
    md=root/(PFX+"-calculation-report.md");csvpath=root/(PFX+"-signed-member-actions.csv")
    js.write_text(json.dumps(d,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    ht.write_text(report_html(d),encoding="utf-8");md.write_text(report_md(d),encoding="utf-8")
    with csvpath.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["case","member"]+PARTS)
        w.writeheader();w.writerows(forces)
    files={p.name:{"sha256":digest(p),"bytes":p.stat().st_size} for p in (js,ht,md,csvpath)}
    manifest={"schema":"jp.structural.g15.gate21.manifest.v0.1","files":files,
       "source_pdf_sha256":PDF_SHA,"grid_SHA256":d["grid_SHA256"],"request_SHA256":d["request_SHA256"],
       "solved_cases":d["case_count"],"signed_end_actions":d["signed_end_action_count"],
       "F3_verdict":"NOT SAFE IN ONE WAY SHEAR","engineering_approval":False}
    (root/(PFX+"-manifest.json")).write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
    return d,manifest

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--output-dir",type=Path,required=True)
    p.add_argument("--request-json",type=Path)
    a=p.parse_args()
    r,_=export(a.output_dir,a.request_json)
    print("GATE21_OPENSEES_NUMERICAL_REPORT_READY_NOT_APPROVED",r["case_count"],r["signed_end_action_count"])
