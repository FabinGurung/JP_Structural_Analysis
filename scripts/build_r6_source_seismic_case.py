#!/usr/bin/env python3
"""R6.1 governed SYNTHETIC seismic reference from source-audited R5 masses.

This stage uses the already tested independent canonical OpenSees 3D frame
seismic engine for modal participation, explicit CQC MRSM, storey drift,
transverse 2-node torsion probes and an explicit orthogonal factor. It does
NOT compute eigenmodes of the R5.6 connected shell model. An independent
3D elastic cantilever tests the OpenSees PDelta transformation under three
compressive loads and is NOT a project-building P-Delta acceptability check.

All inputs named SYNTHETIC require caller-supplied provenance and units.
No NBC-specified site spectrum, risk factors or building-source acceptance
may be inferred from these calculations.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import html
import io
import json
import csv
import math
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from jp_structural.solvers.native.geometry_load_intake import assemble_geometry_source_loads
from jp_structural.solvers.opensees.load_mass_adapter import bind_assembly_to_canonical_model
from jp_structural.solvers.opensees.canonical_seismic import (
    run_canonical_response_spectrum,combine_orthogonal_direction_results,
    cqc_correlation_coefficient,normalize_response_spectrum,
)
from scripts.build_r5_generic_frame_case import DEFAULT
from scripts.build_structural_template_engine import CONTRACT,COVERAGE

SETTINGS=ROOT/"examples/sanitized/r6_source_audited_synthetic_spectrum.v0.1.json"
PFX="r6-synthetic-seismic-source"
SCHEMA="jp.structural.r6.source_mass_mrsm_drift_torsion_pdelta_reference.v0.1"

class R6ReferenceError(ValueError):pass

def _hash(x):
    return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8")).hexdigest()

def _number(x,label,positive=False):
    if isinstance(x,bool) or not isinstance(x,(float,int)) or not math.isfinite(x) or (positive and x<=0):
        raise R6ReferenceError(f"{label} requires finite "+("positive" if positive else "numeric")+" value")
    return float(x)

def pdelta_cantilever(p:dict):
    """Independent 3D same-element linear vs PDelta benchmark (not design)."""
    import openseespy.opensees as ops
    if p.get("id")!="INDEPENDENT_ELASTIC_3D_CANTILEVER_STABILITY_BENCHMARK":
        raise R6ReferenceError("independent PDelta synthetic benchmark provenance absent")
    if not isinstance(p.get("source_reference"),str) or not p["source_reference"]:
        raise R6ReferenceError("PDelta benchmark source_reference required")
    length=_number(p["length_m"],"length",True)
    b=_number(p["width_m"],"width",True)
    d=_number(p["depth_m"],"depth",True)
    E=_number(p["E_kN_m2"],"E",True)
    poisson=_number(p["poisson"],"poisson")
    F=_number(p["lateral_Fx_kN"],"lateral",True)
    if not 0<poisson<.49 or length>12 or b>2 or d>2:
        raise R6ReferenceError("bounded synthetic elastic beam properties invalid")
    loads=p.get("axial_compression_kN")
    if not isinstance(loads,list) or len(loads)!=3:
        raise R6ReferenceError("three explicit PDelta axial loads required")
    P=[_number(x,"axial compression") for x in loads]
    if not (P[0]==0 and 0<P[1]<P[2]):
        raise R6ReferenceError("PDelta axial loads require 0 and two increasing compressions")
    A=b*d;Iy=b*d**3/12;Iz=d*b**3/12
    short,long=sorted((b,d))
    J=long*short**3*(1/3-.21*short/long*(1-short**4/(12*long**4)))
    G=E/(2*(1+poisson))
    Euler=math.pi**2*E*Iy/(4*length*length)
    if P[-1]>=.5*Euler:raise R6ReferenceError("bounded PDelta reference exceeds half analytical Euler load")
    def solve(kind,load):
        ops.wipe();ops.model("basic","-ndm",3,"-ndf",6)
        ops.node(1,0.,0.,0.);ops.node(2,0.,0.,length)
        ops.fix(1,1,1,1,1,1,1)
        ops.geomTransf(kind,1,1.,0.,0.)
        ops.element("elasticBeamColumn",1,1,2,A,E,G,J,Iy,Iz,1)
        ops.timeSeries("Linear",1);ops.pattern("Plain",1,1)
        ops.load(2,0.,0.,-load,0.,0.,0.)
        ops.constraints("Plain");ops.numberer("RCM");ops.system("BandGeneral")
        ops.test("NormDispIncr",1e-11,30,0);ops.algorithm("Newton")
        ops.integrator("LoadControl",.2);ops.analysis("Static")
        if ops.analyze(5)!=0:raise R6ReferenceError("synthetic PDelta axial preload failed")
        ops.loadConst("-time",0.)
        ops.timeSeries("Linear",2);ops.pattern("Plain",2,2)
        ops.load(2,F,0.,0.,0.,0.,0.)
        ops.wipeAnalysis()
        ops.constraints("Plain");ops.numberer("RCM");ops.system("BandGeneral")
        ops.test("NormDispIncr",1e-11,50,0);ops.algorithm("Newton")
        ops.integrator("LoadControl",.2);ops.analysis("Static")
        if ops.analyze(5)!=0:raise R6ReferenceError("synthetic PDelta lateral analysis failed")
        disp=float(ops.nodeDisp(2,1))
        ops.reactions()
        rx=float(ops.nodeReaction(1,1));rz=float(ops.nodeReaction(1,3))
        if not all(math.isfinite(v) for v in (disp,rx,rz)) or disp<=0:
            raise R6ReferenceError("PDelta benchmark invalid deformation/reaction")
        if not math.isclose(rx,-F,abs_tol=1e-5) or not math.isclose(rz,load,abs_tol=1e-5):
            raise R6ReferenceError("PDelta synthetic external force equilibrium failed")
        return {"tip_Ux_m":disp,"base_Rx_kN":rx,"base_Rz_kN":rz}
    rows=[]
    for load in P:
        linear=solve("Linear",load)
        second=solve("PDelta",load)
        rows.append({"axial_compression_kN":load,
             "linear":linear,"PDelta":second,
             "displacement_amplification":second["tip_Ux_m"]/linear["tip_Ux_m"],
             "first_order_synthetic_stability_index":load*linear["tip_Ux_m"]/(F*length),
             "not_code_stability_approval":True})
    hand=F*length**3/(3*E*Iy)
    if not math.isclose(rows[0]["linear"]["tip_Ux_m"],hand,rel_tol=1e-5,abs_tol=1e-9):
        raise R6ReferenceError("independent first-order cantilever analytic displacement mismatch")
    if not math.isclose(rows[0]["PDelta"]["tip_Ux_m"],hand,rel_tol=1e-5,abs_tol=1e-9):
        raise R6ReferenceError("PDelta at zero compression differs from hand benchmark")
    amp=[x["displacement_amplification"] for x in rows]
    if not (math.isclose(amp[0],1.,rel_tol=1e-5)
            and 1<amp[1]<amp[2]<3):
        raise R6ReferenceError("PDelta displacement must amplify under rising axial compression")
    return {"schema":"jp.structural.r6.pdelta_3d_cantilever_benchmark.v0.1",
        "source_benchmark_id":p["id"],"source_reference":p["source_reference"],
        "analytical_zero_compression_Ux_m":hand,
        "analytical_Euler_cantilever_cr_kN":Euler,
        "rows":rows,"zero_compression_analytic_agreement":True,
        "monotone_PDelta_amplification":True,
        "applied_first_order_stability_screen_only":True,
        "whole_building_PDelta_verified":False,"engineering_approval":False}

def build(source=None,settings=None):
    if source is None:source=json.loads(DEFAULT.read_text(encoding="utf-8"))
    if settings is None:settings=json.loads(SETTINGS.read_text(encoding="utf-8"))
    if settings.get("schema")!="jp.structural.r6.synthetic_seismic_inputs.v0.1":
        raise R6ReferenceError("explicit R6 seismic source-input schema required")
    if source.get("classification")!="SYNTHETIC_REFERENCE_NOT_A_BUILDING" or source.get("case_id")!=settings.get("source_case_id"):
        raise R6ReferenceError("source synthetic building/model identity mismatch")
    audited=assemble_geometry_source_loads(model=source["model"],
        loads=source["source_loads"],gravity_m_s2=source["gravity_m_s2"])
    masses=audited["audited_assembly"]
    canonical=bind_assembly_to_canonical_model(source["model"],masses)
    n=settings.get("number_modes")
    if isinstance(n,bool) or not isinstance(n,int) or not 1<=n<=9:
        raise R6ReferenceError("R6 bounded mode count 1..9 required")
    spectrum=settings.get("response_spectrum")
    if not isinstance(spectrum,dict) or "SYNTHETIC" not in str(spectrum.get("id","")):
        raise R6ReferenceError("unverified site spectrum cannot enter synthetic-only milestone")
    normalized=normalize_response_spectrum(spectrum,model_units=canonical["units"])
    if normalized["source_reference"]!="SYNTHETIC_TEST_ORDINATES_NOT_NBC_105_2025_DESIGN_SPECTRUM":
        raise R6ReferenceError("explicit synthetic spectrum source provenance required")
    if normalized["units"]["spectral_acceleration"]!="m/s^2":
        raise R6ReferenceError("synthetic source spectrum acceleration unit must be exactly m/s^2")
    if normalized["units"]["period"]!="s" or normalized["units"]["base_shear"]!="kN":
        raise R6ReferenceError("synthetic source spectrum time/force units invalid")
    if settings.get("modal_combination") not in ("CQC","SRSS"):
        raise R6ReferenceError("explicit SRSS/CQC modal method required")
    probes=settings.get("torsion_probes")
    if not isinstance(probes,dict) or set(probes)!={"X","Y"}:
        raise R6ReferenceError("two explicit physical torsion probe directions required")
    response_points=settings.get("response_points")
    if response_points!=[{"storey_id":"BASE","node_id":"B1"},{"storey_id":"ROOF","node_id":"R1"}]:
        raise R6ReferenceError("R6 reference requires exact bounded source storey response point mapping")
    total_mass=math.fsum(float(row["mx"]) for row in masses["nodal_masses"])
    g=_number(source["gravity_m_s2"],"source gravity",True)
    if not math.isclose(total_mass*g,masses["total_seismic_weight_kN"],rel_tol=1e-10,abs_tol=1e-8):
        raise R6ReferenceError("source seismic mass fails physical weight conversion")
    all_rows=[]
    for axis in ("X","Y"):
        response=run_canonical_response_spectrum(
            canonical,spectrum,n,direction=axis,
            modal_combination=settings["modal_combination"],
            response_points=response_points,
            torsion_points=probes[axis],
            eigen_solver="fullGenLapack")
        c=response["case_results"][0]
        if c["num_modes"]!=n or len(c["modes"])!=n:
            raise R6ReferenceError("incomplete OpenSees modal eigensolution")
        if not math.isclose(c["total_translational_mass"],total_mass,rel_tol=1e-8,abs_tol=1e-8):
            raise R6ReferenceError("OpenSees mass differs from signed audit")
        cum=[float(x["cumulative_participation_ratio"]) for x in c["modes"]]
        if not all(0<=x<=1.000001 for x in cum) or any(b<a-1e-7 for a,b in zip(cum,cum[1:])):
            raise R6ReferenceError("modal effective mass fractions inconsistent")
        shear=c["combined"]["base_shear"]
        if not math.isfinite(shear) or shear<=0:
            raise R6ReferenceError("MRSM base shear missing")
        drift=c["combined"]["interstorey_drift"]
        if len(drift)!=1 or drift[0]["drift_ratio"]<0:
            raise R6ReferenceError("explicit interstorey drift not calculated")
        tor=c["combined"]["torsional_rotation"]
        if len(tor)!=1 or not math.isfinite(tor[0]["rotation"]):
            raise R6ReferenceError("explicit source-geometry torsion probe missing")
        # Flat source spectrum: each modal base shear is Meff * 2m/s².
        # The SRSS/CQC sum is not necessarily W*Sa/g (it is a modal envelope).
        for mode in c["modes"]:
            if not math.isclose(mode["base_shear"],
                abs(mode["effective_modal_mass"]*mode["spectral_acceleration"]),
                rel_tol=1e-8,abs_tol=1e-7):
                raise R6ReferenceError("modal force does not equal effective mass times explicit spectrum Sa")
        all_rows.append({"axis":axis,"case":response})
    factor=_number(settings.get("orthogonal_factor"),"orthogonal factor")
    if factor<0 or factor>1:raise R6ReferenceError("orthogonal factor out of bounds")
    orth=combine_orthogonal_direction_results(
        all_rows[0]["case"],all_rows[1]["case"],orthogonal_factor=factor)
    pdelta=pdelta_cantilever(settings["pdelta"])
    from jp_structural.solvers.native.response_spectrum import srss
    if not math.isclose(srss((3,4)),5,rel_tol=0,abs_tol=1e-12):
        raise R6ReferenceError("independent SRSS Pythagorean benchmark failed")
    if not math.isclose(cqc_correlation_coefficient(5,5,.05),1,abs_tol=1e-12):
        raise R6ReferenceError("independent CQC equal frequency correlation failed")
    coverage={r["id"]:r for r in json.loads(COVERAGE.read_text(encoding="utf-8"))["requirements"]}
    contract=json.loads(CONTRACT.read_text(encoding="utf-8"))
    scopes={"M02":"AUDITED_R5_SEISMIC_ELIGIBLE_SOURCE_MASS_AND_EXPLICIT_SYNTHETIC_ACCELERATION_SPECTRUM",
            "M04":"3D_ELASTIC_CANONICAL_FRAME_MODAL_EIGEN_WITHOUT_CONNECTED_SHELL",
            "M05":"EXPLICIT_CQC_OR_SRSS_MRSM_BASE_SHEAR_STOREY_DRIFT_TORSION_PROBES",
            "M06":"PDELTA_INDEPENDENT_3D_CANTILEVER_TRANSFORM_SCREEN_ONLY",
            "S17":"SPECTRUM_MASS_UNITS_PARTICIPATION_AND_FIRST_ORDER_ANALYTIC_PDELTA_BENCHMARK"}
    chapters=[{"id":c["id"],"title":c["title"],
               "modules":[{"id":mid,"title":coverage[mid]["title"],
                  "status":scopes.get(mid,"NOT_EVALUATED_IN_BOUNDED_R6P1")}
                  for mid in c["requirement_ids"]]} for c in contract["chapters"]]
    if len(chapters)!=7 or {x["id"] for ch in chapters for x in ch["modules"]}!=set(coverage):
        raise R6ReferenceError("7 chapters and 18 requirements not conserved")
    return {
        "schema":SCHEMA,"source_case_id":source["case_id"],
        "source_input_SHA256":_hash(source),"r6_settings_SHA256":_hash(settings),
        "source_assembly_SHA256":canonical["provenance"]["load_mass_assembly_sha256"],
        "audited_seismic_weight_kN":masses["total_seismic_weight_kN"],
        "audited_gravity_kN":masses["total_gravity_load_kN"],
        "gravity_m_s2":g,
        "audited_seismic_mass_kN_s2_m":total_mass,
        "source_nodal_mass_rows":masses["nodal_masses"],
        "seismic_mass_source_conservation":True,
        "explicit_spectrum":normalized,
        "source_modal_results":all_rows,
        "orthogonal_source_factor_envelope":orth,
        "pdelta_independent_3d_benchmark":pdelta,
        "dynamic_response_axes":["X","Y"],
        "modal_mode_count_per_axis":n,
        "reference_source_not_site_spectrum":True,
        "pdelta_not_full_building":True,
        "connected_shell_modal_mass_verified":False,
        "original_building_sources_accepted":0,
        "original_F3_failure":"NOT SAFE IN ONE WAY SHEAR",
        "engineering_approval":False,"permit_eligible":False,
        "nbc105_2025_compliance_approved":False,
        "qa":{"source_mass_conserved":True,"modal_results_nonzero":True,
              "torsion_probes_explicit":True,"interstory_drift_explicit":True,
              "cqc_srss_benchmarks_pass":True,"independent_PDelta_three_load_benchmark":True,
              "original_F3_not_overwritten":True},
        "chapters":chapters,
        "remaining":[
            "Actual G+1.5 source model cannot be inferred from the synthetic 4-column frame.",
            "Modal and MRSM results here use the canonical 3D elastic FRAME only; connected ShellMITC4 model dynamic eigen modes are not yet included.",
            "Explicit source acceleration 2m/s2 flat spectrum and orthogonal factor 0.30 are synthetic illustrative values, not NBC 105:2025 design parameters.",
            "No approved code spectral factor, soil Vs30, risk, ductility, accidental eccentricity, effective cracked stiffness or full mass-source verification from drawings.",
            "No actual site building PDelta; only a different independently controlled 3D cantilever numerical stability benchmark.",
            "No verified RC member or foundation capacity, slab reinforcement, section detailing or permit approval.",
            "Original report retains 0/15 source building acceptance and unsafe F3."
        ],
        "official_reference_urls":[
          "https://ebps.kathmandu.gov.np/UploadFiles/NBC_105_2025_Sesmic_Design.pdf",
          "https://opensees.github.io/OpenSeesDocumentation/user/manual/analysis/responseSpectrumAnalysis.html",
          "https://opensees.github.io/OpenSeesDocumentation/user/manual/model/geomTransf/PDelta.html"
        ]
    }

def _csv(rows,cols):
    out=io.StringIO();w=csv.writer(out,lineterminator="\n");w.writerow(cols)
    for row in rows:w.writerow([row.get(k) for k in cols])
    return out.getvalue()

def render_html(r):
    e=lambda x:html.escape(str(x),quote=True)
    rows=[]
    for response in r["source_modal_results"]:
        axis=response["axis"];s=response["case"]["case_results"][0]
        drift=s["combined"]["interstorey_drift"][0]
        torsion=s["combined"]["torsional_rotation"][0]
        rows.append(f'<tr><td>{axis}</td><td>{s["modal_combination"]}</td><td>{s["combined"]["base_shear"]:.5f}</td><td>{drift["drift_ratio"]:.8g}</td><td>{torsion["rotation"]:.8g}</td><td>{s["modes"][-1]["cumulative_participation_ratio"]:.5f}</td></tr>')
    modes="".join(f'<tr><td>{x["axis"]}</td><td>{item["mode"]}</td><td>{item["period"]:.6g}</td><td>{item["effective_modal_mass"]:.6g}</td><td>{item["participation_ratio"]:.5f}</td></tr>' for x in r["source_modal_results"] for item in x["case"]["case_results"][0]["modes"])
    pd="".join(f'<tr><td>{x["axial_compression_kN"]:.0f}</td><td>{x["linear"]["tip_Ux_m"]:.8g}</td><td>{x["PDelta"]["tip_Ux_m"]:.8g}</td><td>{x["displacement_amplification"]:.5f}</td></tr>' for x in r["pdelta_independent_3d_benchmark"]["rows"])
    pages=[]
    for c in r["chapters"]:
        table="".join(f'<tr><td>{e(a["id"])}</td><td>{e(a["title"])}</td><td>{e(a["status"])}</td></tr>' for a in c["modules"])
        pages.append(f'<section id="chapter-{c["id"]}"><h2>Chapter {c["id"]} — {e(c["title"])}</h2><div class="scroll"><table><tr><th>Module</th><th>Requirement</th><th>Scope</th></tr>{table}</table></div></section>')
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>R6.1 Source-audited synthetic MRSM and PDelta</title>
<style>body{{font:14px/1.55 system-ui;max-width:1100px;margin:auto;padding:18px;background:#f6f8fb;color:#273c53}}header,section{{background:#fff;border:1px solid #d7dfeb;border-radius:11px;padding:20px;margin:15px 0}}.hold{{background:#fff1eb;border-left:5px solid #b45648;padding:11px}}table{{width:100%;border-collapse:collapse;min-width:560px}}td,th{{border:1px solid #d2dce8;padding:8px;font-size:12px;text-align:left}}th{{background:#edf2f8}}.scroll{{overflow-x:auto}}@media print{{body{{background:white}}}}</style></head><body><header>
<h1>R6.1 · Seismic source mass, MRSM, drift, torsion and P–Delta benchmark</h1><p class="hold"><strong>SYNTHETIC FRAME REFERENCE ONLY — NOT CODE APPROVED / NOT FOR CONSTRUCTION.</strong> Original footing F3 is NOT SAFE IN ONE WAY SHEAR.</p><p>Audited R5 source seismic weight {r["audited_seismic_weight_kN"]:.3f} kN and source mass {r["audited_seismic_mass_kN_s2_m"]:.5f} kN·s²/m. Explicit flat 2 m/s² synthetic response spectrum, 5% damping, no site-specific code inputs.</p>
<p><a href="{PFX}.json">Full numerical and source SHA data</a> · <a href="{PFX}-modes.csv">Modal data CSV</a> · <a href="{PFX}-pdelta.csv">PDelta comparison CSV</a> · <a href="{PFX}-manifest.json">SHA-256 manifest</a></p></header>
<section><h2>Source spectrum — X/Y modal results</h2><div class="scroll"><table><tr><th>Axis</th><th>Method</th><th>Base shear kN</th><th>Drift ratio</th><th>Roof torsion rad</th><th>Cumulative effective mass</th></tr>{''.join(rows)}</table></div>
<p>These are elastic response-spectrum envelopes. Modal peak signs cannot be interpreted as concurrent signed member force vectors; no professional code drift limit has been applied.</p>
<div class="scroll"><table><tr><th>Axis</th><th>Mode</th><th>Period s</th><th>Effective mass</th><th>Modal mass fraction</th></tr>{modes}</table></div></section>
<section><h2>Separate 3D cantilever P–Delta screen</h2><p>The same elastic column is solved under zero, low and higher explicitly assigned axial compression using both Linear and PDelta transformations. No transfer of these synthetic forces to the original building is claimed.</p>
<div class="scroll"><table><tr><th>Axial kN</th><th>Linear Ux m</th><th>PDelta Ux m</th><th>Amplification</th></tr>{pd}</table></div></section>{''.join(pages)}
<section><h2>Annex — unresolved physical/source debt</h2><ul>{''.join("<li>"+e(a)+"</li>" for a in r["remaining"])}</ul></section></body></html>"""

def emit(source_path:Path,settings_path:Path,folder:Path):
    spec=json.loads(source_path.read_text(encoding="utf-8"))
    settings=json.loads(settings_path.read_text(encoding="utf-8"))
    r=build(spec,settings);folder.mkdir(parents=True,exist_ok=True)
    mod=[]
    for z in r["source_modal_results"]:
        c=z["case"]["case_results"][0]
        for m in c["modes"]:
            mod.append({"axis":z["axis"],"mode":m["mode"],"period_s":m["period"],
              "Sa_m_s2":m["spectral_acceleration"],"effective_modal_mass":m["effective_modal_mass"],
              "participation_ratio":m["participation_ratio"],
              "cumulative_participation_ratio":m["cumulative_participation_ratio"],
              "modal_base_shear_kN":m["base_shear"]})
    pd=[{"axial_kN":x["axial_compression_kN"],
         "linear_Ux_m":x["linear"]["tip_Ux_m"],"PDelta_Ux_m":x["PDelta"]["tip_Ux_m"],
         "amplification":x["displacement_amplification"],
         "stability_index_screen":x["first_order_synthetic_stability_index"]}
        for x in r["pdelta_independent_3d_benchmark"]["rows"]]
    objs={
       PFX+".json":json.dumps(r,sort_keys=True,indent=2,allow_nan=False)+"\n",
       PFX+".html":render_html(r),
       PFX+"-modes.csv":_csv(mod,["axis","mode","period_s","Sa_m_s2","effective_modal_mass","participation_ratio","cumulative_participation_ratio","modal_base_shear_kN"]),
       PFX+"-pdelta.csv":_csv(pd,["axial_kN","linear_Ux_m","PDelta_Ux_m","amplification","stability_index_screen"])}
    for name,value in objs.items():(folder/name).write_text(value,encoding="utf-8")
    manifest={"schema":"jp.structural.r6.source_seismic_manifest.v0.1",
         "source_input_SHA256":r["source_input_SHA256"],"settings_SHA256":r["r6_settings_SHA256"],
         "files":{name:hashlib.sha256(data.encode("utf-8")).hexdigest() for name,data in objs.items()},
         "engineering_approval":False}
    (folder/(PFX+"-manifest.json")).write_text(json.dumps(manifest,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    return r

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",type=Path,default=DEFAULT)
    p.add_argument("--settings",type=Path,default=SETTINGS)
    p.add_argument("--output-dir",type=Path,required=True)
    a=p.parse_args();r=emit(a.input,a.settings,a.output_dir)
    print("R6P1_SOURCE_MASS_111P2_KN_2AXES_6MODES_PDELTA_3LOADS_NOT_NBC_APPROVED")
if __name__=="__main__":main()
