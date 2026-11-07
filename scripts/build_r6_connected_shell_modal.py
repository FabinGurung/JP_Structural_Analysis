#!/usr/bin/env python3
"""R6.2 same R5.6 3D connected ShellMITC4/frame mesh: modal CQC MRSM.

Same assembly entry point as R5.5/R5.6, including unchanged corner source
masses and optional in-plane rigidDiaphragm(3) MPC. A modal inertia force
F_j = M_j * phi_j * Gamma_axis * Sa(T) is applied and statically solved on
that SAME native connected shell/beam/column FE mesh for each mode. Local
I/J member end actions, foundation reactions, displacement and torsion
probes are therefore true FEM modal responses, not a proxy from another
canonical frame or an independently selected envelope. CQC component
results are NONNEGATIVE ENVELOPES, not concurrent signed force vectors.

Scope is deliberately 2x2 and 4x4 synthetic shell/frame meshes, 4 modal
eigenpairs per direction, 2 diaphragm constraints and 2 horizontal axes.
No verified code spectrum, no actual building, no code-compliant design.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import html
import io
import json
import math
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.build_r5_connected_shell_frame import (
    DEFAULT,exact_reference,solve_mesh,ShellBridgeError,sha)
from scripts.build_r5_shell_diaphragm_signed import MODES,COMPONENTS
SETTINGS=ROOT/"examples/sanitized/r6p2_connected_shell_modal_source.v0.1.json"
from scripts.build_structural_template_engine import CONTRACT,COVERAGE
from jp_structural.solvers.opensees.canonical_seismic import (
    normalize_response_spectrum,interpolate_spectral_acceleration,
    cqc_correlation_coefficient,
)

PFX="r6-connected-shell-modal"
SCHEMA="jp.structural.r6.connected_shell_modal_mrsm.v0.1"
MESHES=(2,4)
AXES=("X","Y")
NMODES=4
DIRS={"X":0,"Y":1}
DOFS=("Ux","Uy","Uz","Rx","Ry","Rz")
CASE_ID="HX" # placeholder for original R5 shared mesh builder ONLY

class ShellModalError(ValueError):pass

def _close(actual,expected,field,rel=3e-5,absolute=1e-7):
    if not (math.isfinite(float(actual)) and
            math.isclose(float(actual),float(expected),rel_tol=rel,abs_tol=absolute)):
        raise ShellModalError(f"{field}: expected {expected:.12g}, calculated {actual:.12g}")

def _finite(x,label):
    if isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x):
        raise ShellModalError(label+" must be a finite number")
    return float(x)

def _cqc(vals,omegas,zeta):
    if len(vals)!=len(omegas) or not vals:raise ShellModalError("CQC response/frequency alignment missing")
    total=0.
    for i,u in enumerate(vals):
        for j,v in enumerate(vals):
            total+=u*v*cqc_correlation_coefficient(omegas[i],omegas[j],zeta)
    tolerance=1e-10*max(1.,math.fsum(abs(v) for v in vals)**2)
    if total< -tolerance:raise ShellModalError("CQC response quadratic form negative")
    return math.sqrt(max(total,0.))

def _meta_handler(*,mode_index,excitation_axis,spec,settings):
    """Callback called INSIDE actual R5.6 FE assembly; no new model geometry."""
    def handler(*,ops,ref,n,diaphragm_mode,tag,positions,corner_ix,base,columns,
                segment_register,master_tag,source_mass_rows):
        eigen_count=settings["number_modes"]
        if not isinstance(eigen_count,int) or isinstance(eigen_count,bool) or eigen_count!=NMODES:
            raise ShellModalError("bounded connected modal benchmark requires four eigenmodes")
        if mode_index not in range(1,eigen_count+1):
            raise ShellModalError("invalid mode number")
        ops.constraints("Transformation" if master_tag is not None else "Plain")
        ops.numberer("RCM");ops.system("BandGeneral")
        ops.algorithm("Linear");ops.integrator("LoadControl",1.)
        ops.analysis("Static")
        # The full generalized eigen formulation keeps zero-density shell
        # interior nodes statically coupled; only the 4 original R5 corner
        # masses provide the kinetic M. No shell mass is fabricated.
        try:
            eigen_raw=ops.eigen("-fullGenLapack",eigen_count)
        except Exception as exc:
            raise ShellModalError("OpenSees connected-shell full generalized eigen failed") from exc
        eig=[float(x) for x in eigen_raw]
        if len(eig)!=eigen_count or any(not math.isfinite(v) or v<=0 for v in eig):
            raise ShellModalError("invalid connected-shell eigenvalues or missing modes")
        lam=eig[mode_index-1]
        omega=math.sqrt(lam)
        period=2*math.pi/omega
        spectrum=settings["response_spectrum"]
        norm=normalize_response_spectrum(spectrum,model_units=ref["model"]["units"])
        acceleration=interpolate_spectral_acceleration(norm,period)
        src_by_id={row["node_id"]:row for row in source_mass_rows}
        if len(src_by_id)!=4 or set(src_by_id)!={"R1","R2","R3","R4"}:
            raise ShellModalError("explicit four original seismic mass source corners required")
        physical=[]
        masses=[]
        vectors={}
        for index,ij in enumerate(corner_ix,1):
            nid=f"R{index}"
            node_tag=tag(*ij)
            a=src_by_id[nid]
            v=[float(a[k]) for k in ("mx","my","mz","mrx","mry","mrz")]
            if any(not math.isfinite(m) or m<0 for m in v) or any(v[3:]):
                raise ShellModalError("R6.2 refuses non-source rotational mass or invalid weight")
            if not (math.isclose(v[0],v[1],rel_tol=0,abs_tol=1e-10) and
                    math.isclose(v[1],v[2],rel_tol=0,abs_tol=1e-10)):
                raise ShellModalError("source X/Y/Z masses must match")
            solver_m=[float(ops.nodeMass(node_tag,d)) for d in range(1,7)]
            for i in range(6):_close(solver_m[i],v[i],"actual OpenSees mass",rel=1e-8,absolute=1e-9)
            phi=[float(ops.nodeEigenvector(node_tag,mode_index,d)) for d in range(1,7)]
            if not all(math.isfinite(q) for q in phi):
                raise ShellModalError("nonfinite shell-frame eigenvector")
            vectors[nid]=phi
            masses.append((nid,node_tag,v,phi))
            physical.append({"node_id":nid,"node_tag":node_tag,"mass_xyz":v[:3],"phi":phi})
        modal_mass=math.fsum(v[d]*phi[d]**2 for _,_,v,phi in masses for d in range(3))
        if modal_mass<=1e-15 or not math.isfinite(modal_mass):
            raise ShellModalError("source-mapped generalized modal mass is zero/invalid")
        axis_index=DIRS[excitation_axis]
        numerator=math.fsum(v[axis_index]*phi[axis_index] for _,_,v,phi in masses)
        gamma=numerator/modal_mass
        effective_mass=numerator**2/modal_mass
        total_mass=math.fsum(v[axis_index] for _,_,v,_ in masses)
        if total_mass<=0 or effective_mass>total_mass*(1+1e-5):
            raise ShellModalError("effective modal mass violates physical mass")
        modal_inertia=[]
        for nid,node_tag,physical_mass,phi in masses:
            F=[physical_mass[d]*phi[d]*gamma*acceleration for d in range(3)]
            modal_inertia.append({"node_id":nid,"node_tag":node_tag,
                                  "forces_kN":F})
        applied_axis=math.fsum(row["forces_kN"][axis_index] for row in modal_inertia)
        _close(applied_axis,effective_mass*acceleration,
               "modal mass×Sa source force",rel=1e-7,absolute=1e-8)
        ops.wipeAnalysis()
        ops.timeSeries("Linear",101)
        ops.pattern("Plain",101,101)
        for x in modal_inertia:
            ops.load(x["node_tag"],*x["forces_kN"],0.,0.,0.)
        ops.constraints("Transformation" if master_tag is not None else "Plain")
        ops.numberer("RCM");ops.system("BandGeneral")
        ops.algorithm("Linear");ops.integrator("LoadControl",1.)
        ops.analysis("Static")
        if ops.analyze(1)!=0:
            raise ShellModalError("same connected FE modal inertia force analysis failed")
        ops.reactions()
        rec=[]
        for base_id in base:
            vals=[float(ops.nodeReaction(base_id,d)) for d in range(1,7)]
            rec.append({"node_id":f"B{base_id}","xyz":[float(ref["model"]["nodes"][base_id-1][k]) for k in ("x","y","z")],
                        "R":vals})
        resultant=[0.]*6
        def add(x,y,z,fx,fy,fz,mx,my,mz):
            for i,v in enumerate((fx,fy,fz,mx+y*fz-z*fy,my+z*fx-x*fz,mz+x*fy-y*fx)):
                resultant[i]+=v
        for row,ij in zip(modal_inertia,corner_ix):
            x,y,z=positions[ij];fx,fy,fz=row["forces_kN"]
            add(x,y,z,fx,fy,fz,0.,0.,0.)
        for row in rec:
            add(*row["xyz"],*row["R"])
        if max(abs(x) for x in resultant)>1e-4:
            raise ShellModalError("modal inertia 6DOF support force/moment residual too high")
        roof=[]
        for idx,ij in enumerate(corner_ix,1):
            nid=f"R{idx}";nd=tag(*ij)
            actual=[float(ops.nodeDisp(nd,d)) for d in range(1,7)]
            expected=[vectors[nid][d]*gamma*acceleration/lam for d in range(6)]
            for d in range(3):
                _close(actual[d],expected[d],f"modal {excitation_axis}/{mode_index} eigen to static deflection {nid}/{DOFS[d]}",
                       rel=3e-4,absolute=2e-7)
            roof.append({"node_id":nid,"displacement":actual,"eigen_prediction":expected})
        # The 6DOF beam/column element responses are solved under EXACT
        # modal forces, not approximated from separate project members.
        elements={}
        for mid,segs in segment_register.items():
            elements[mid]=[]
            for e in segs:
                f=ops.eleResponse(e,"localForce")
                if f is None or len(f)!=12:raise ShellModalError("missing connected beam modal end action")
                elements[mid].append({"tag":e,"I":dict(zip(COMPONENTS,map(float,f[:6]))),
                                      "J":dict(zip(COMPONENTS,map(float,f[6:])))})
        for i,e in enumerate(columns,1):
            f=ops.eleResponse(e,"localForce")
            if f is None or len(f)!=12:raise ShellModalError("missing connected column modal end action")
            elements[f"COL{i}"]=[{"tag":e,"I":dict(zip(COMPONENTS,map(float,f[:6]))),
                                 "J":dict(zip(COMPONENTS,map(float,f[6:]))) }]
        first=roof[0]["displacement"][axis_index]
        rmap={x["node_id"]:x for x in roof}
        if excitation_axis=="X":
            dr=(rmap["R4"]["displacement"][0]-rmap["R1"]["displacement"][0])/3.
            rotation=-dr
        else:
            rotation=(rmap["R2"]["displacement"][1]-rmap["R1"]["displacement"][1])/4.
        drift=first/(ref["corners"][4]-float(ref["model"]["nodes"][0]["z"]))
        return {
          "mesh":n,"diaphragm_mode":diaphragm_mode,
          "axis":excitation_axis,"mode":mode_index,
          "eigenvalue_1_s2":lam,"omega_rad_s":omega,"period_s":period,
          "source_Sa_m_s2":acceleration,
          "modal_mass_kN_s2_m":modal_mass,"source_total_mass_kN_s2_m":total_mass,
          "participation_factor":gamma,
          "effective_modal_mass_kN_s2_m":effective_mass,
          "modal_mass_participation_fraction":effective_mass/total_mass,
          "source_modal_base_shear_kN":abs(effective_mass*acceleration),
          "roof_R1_displacement_m":first,
          "interstory_drift_ratio_signed":drift,
          "roof_torsion_rotation_rad_signed":rotation,
          "corner_modal_displacements":roof,
          "source_inertia_forces":modal_inertia,
          "base_reactions":rec,"global_force_moment_residual":resultant,
          "six_component_support_balance_pass":True,
          "eigen_displacement_vs_modal_force_static_pass":True,
          "native_IJ_member_actions":elements,
          "source_mass_allocation_unchanged":True,
          "synthetic_not_engineer_approved":True,
        }
    return handler

def _modal_run(ref,spec,settings,mesh,mode,axis,mode_index):
    h=_meta_handler(mode_index=mode_index,excitation_axis=axis,spec=spec,settings=settings)
    # no R6 frame-only model is ever built: R5.6 shared shell/frame FE
    # builder is used directly before adding any load cases.
    return solve_mesh(ref,mesh,CASE_ID,diaphragm_mode=mode,modal_handler=h)

def _serialize_modes(modes,settings,axis):
    series=sorted(modes,key=lambda m:m["mode"])
    if [m["mode"] for m in series]!=list(range(1,len(modes)+1)):
        raise ShellModalError("missing connected model mode ordinal")
    cm=0.;period=[];rows=[]
    for x in series:
        cm+=x["modal_mass_participation_fraction"]
        if cm>1+5e-4 or cm<0:raise ShellModalError("cumulative participation greater than source mass")
        rows.append({"mode":x["mode"],"period_s":x["period_s"],"omega_rad_s":x["omega_rad_s"],
          "effective_modal_mass":x["effective_modal_mass_kN_s2_m"],
          "participation_fraction":x["modal_mass_participation_fraction"],
          "cumulative_participation_fraction":cm,
          "base_shear_kN":x["source_modal_base_shear_kN"],
          "roof_R1_m":x["roof_R1_displacement_m"],
          "drift_ratio":x["interstory_drift_ratio_signed"],
          "torsion_rad":x["roof_torsion_rotation_rad_signed"]})
        period.append(x["omega_rad_s"])
    zeta=_finite(settings["response_spectrum"]["damping_ratio"],"damping")
    combined_shear=_cqc([x["source_modal_base_shear_kN"] for x in series],period,zeta)
    combined_drift=_cqc([x["interstory_drift_ratio_signed"] for x in series],period,zeta)
    combined_torsion=_cqc([x["roof_torsion_rotation_rad_signed"] for x in series],period,zeta)
    envelopes=[]
    first=series[0]["native_IJ_member_actions"]
    for member in sorted(first):
        for i,segment in enumerate(first[member]):
            for end in ("I","J"):
                result={}
                for c in COMPONENTS:
                    vals=[mode_result["native_IJ_member_actions"][member][i][end][c]
                          for mode_result in series]
                    result[c]=_cqc(vals,period,zeta)
                    if result[c]<0 or not math.isfinite(result[c]):
                        raise ShellModalError("invalid CQC scalar member envelope")
                envelopes.append({"member_id":member,"segment_tag":segment["tag"],
                    "end":end,"CQC_magnitude":result,
                    "concurrent_signed_combination":False})
    return {"axis":axis,"modes":rows,"combined_base_shear_kN":combined_shear,
        "combined_drift_ratio":combined_drift,
        "combined_roof_torsion_rad":combined_torsion,
        "member_CQC_envelopes":envelopes,
        "cumulative_modal_participation_fraction":cm,
        "unrepresented_modal_mass_fraction":max(0,1-cm),
        "cqc_signed_concurrent_vector":False,
        "mode_count":len(series)}

def build(spec=None,settings=None,meshes=MESHES):
    if spec is None:spec=json.loads(DEFAULT.read_text(encoding="utf-8"))
    if settings is None:settings=json.loads(SETTINGS.read_text(encoding="utf-8"))
    if tuple(meshes) not in ((2,),(2,4)):
        raise ShellModalError("bounded connected shell R6.2 mesh selections 2 or 2+4 only")
    if settings.get("schema")!="jp.structural.r6.synthetic_seismic_inputs.v0.1" or settings.get("source_case_id")!=spec.get("case_id"):
        raise ShellModalError("R6.2 requires exact R6.1 source-matched synthetic spectrum")
    if settings.get("modal_combination")!="CQC":
        raise ShellModalError("source-matched CQC modal combination only for this bounded reference")
    if settings.get("number_modes")!=NMODES:
        raise ShellModalError("R6.2 explicit number_modes must equal four for modal action QA")
    spectrum=normalize_response_spectrum(settings["response_spectrum"],model_units=spec["model"]["units"])
    if spectrum["units"]["spectral_acceleration"]!="m/s^2" or "SYNTHETIC" not in spectrum["id"] or spectrum["source_reference"]!="SYNTHETIC_TEST_ORDINATES_NOT_NBC_105_2025_DESIGN_SPECTRUM":
        raise ShellModalError("unverified site spectrum units or provenance forbidden")
    ref=exact_reference(spec)
    original=ref["audit"]["audited_assembly"]
    source_rows=original["nodal_masses"]
    if len(source_rows)!=4:
        raise ShellModalError("source four-corner seismic mass required")
    g=spec["gravity_m_s2"]
    source_weight=original["total_seismic_weight_kN"]
    mass=sum(float(r["mx"]) for r in source_rows)
    _close(source_weight,mass*g,"audited source mass W/g",rel=1e-9,absolute=1e-8)
    # 4x4 shell has no automatically invented interior mass. The modal
    # participation denominator must always be the original 4 roof masses.
    runs=[];summaries=[]
    for mesh in meshes:
        for mode in MODES:
            for axis in AXES:
                vals=[_modal_run(ref,spec,settings,mesh,mode,axis,k)
                     for k in range(1,NMODES+1)]
                for x in vals:
                    _close(x["source_total_mass_kN_s2_m"],mass,
                           "source mass identical across modes/mesh/MPC")
                    if max(abs(v) for v in x["global_force_moment_residual"])>1e-4:
                        raise ShellModalError("native member dynamic source equilibrium mismatch")
                summaries.append({"mesh":mesh,"diaphragm_mode":mode,**_serialize_modes(vals,settings,axis)})
                runs.extend(vals)
    if len(runs)!=len(meshes)*len(MODES)*len(AXES)*NMODES:
        raise ShellModalError("missing actual connected shell modal inertia analyses")
    coverage={r["id"]:r for r in json.loads(COVERAGE.read_text(encoding="utf-8"))["requirements"]}
    template=json.loads(CONTRACT.read_text(encoding="utf-8"))
    scope={"M02":"ORIGINAL_SOURCE_AUDITED_CORNER_MASSES_NO_INTERIOR_MASS_INVENTED",
           "M04":"ACTUAL_SAME_R5P6_SHELLMITC4_BEAM_COLUMN_FRAME_MODAL_FE",
           "M05":"CONNECTED_SHELL_MODAL_CQC_MRSM_DRIFT_AND_TORSION",
           "M08":"MODAL_EQUIVALENT_NATIVE_BEAM_IJ_END_ACTION_MAGNITUDE_ONLY",
           "M09":"MODAL_EQUIVALENT_NATIVE_COLUMN_IJ_END_ACTION_MAGNITUDE_ONLY",
           "S17":"MODAL_INERTIA_LOAD_STATIC_EIGENVECTOR_DISPLACEMENT_SOURCE_EQUILIBRIUM"}
    chapters=[{"id":c["id"],"title":c["title"],
       "modules":[{"id":m,"title":coverage[m]["title"],
                   "status":scope.get(m,"NOT_VERIFIED_IN_R6P2_SYNTHETIC_REFERENCE")}
                  for m in c["requirement_ids"]]} for c in template["chapters"]]
    if len(chapters)!=7 or {x["id"] for c in chapters for x in c["modules"]}!=set(coverage):
        raise ShellModalError("7 chapters/18 module report contract mismatch")
    return {"schema":SCHEMA,"case_id":spec["case_id"],
      "source_sha256":sha(spec),"settings_sha256":sha(settings),
      "source_mass_SHA256":ref["explicit_original_mass_SHA256"],
      "audited_seismic_weight_kN":source_weight,
      "source_total_gravity_kN":original["total_gravity_load_kN"],
      "audited_seismic_mass_kN_s2_m":mass,
      "mesh_divisions":list(meshes),"diaphragm_modes":list(MODES),
      "axes":list(AXES),"modes_per_axis":NMODES,
      "native_modal_static_run_count":len(runs),
      "modal_eigensolution_count":len(runs),
      "participation_summaries":summaries,
      "raw_modal_static_results":runs,
      "same_R5p6_connected_shell_FE":True,
      "original_source_seismic_corner_mass_unchanged":True,
      "real_frame_and_shell_modal_member_actions":True,
      "CQC_individual_components_not_concurrent_signed_vectors":True,
      "mesh_2_and_4_modal_sensitivity_not_convergence_certification":True,
      "R6p1_canonical_frame_model_not_used_for_R6p2":True,
      "accidental_eccentricity_completed":False,
      "code_spectrum_verified":False,
      "original_building_model_verified":False,
      "original_building_accepted_evidence_gates":0,
      "original_F3_failure":"NOT SAFE IN ONE WAY SHEAR",
      "engineering_approval":False,"permit_eligible":False,
      "chapters":chapters,
      "remaining":[
        "This is a bounded synthetic one-bay connected shell/frame reference, not the actual G+1.5 site building.",
        "Only 2x2 and 4x4 shell meshes and first four finite eigenmodes; missing effective mass participation must be recorded, not invented.",
        "CQC is an unsigned component magnitude combination, NOT a concurrent signed vector for RC design.",
        "Only source corners carry inertia: shell density/beam self-mass and validated floor inertia are not automatically inferred.",
        "The flat 2 m/s2 spectrum is synthetic; NBC105:2025 site seismic parameters and MRSM scaling have not been approved.",
        "Accidental eccentricity, cracked RC, multistorey instability, full-building P-Delta, slab reinforcement and foundation checks are OPEN.",
        "Original physical engineering evidence 0/15 and footing F3 NOT SAFE IN ONE WAY SHEAR remain unchanged.",
      ]}

def _csv(rows,keys):
    out=io.StringIO();w=csv.writer(out,lineterminator="\n");w.writerow(keys)
    for row in rows:w.writerow([row.get(k) for k in keys])
    return out.getvalue()

def render_html(r):
    e=lambda x:html.escape(str(x),quote=True)
    headers=["mesh","diaphragm_mode","axis","combined_base_shear_kN",
             "combined_drift_ratio","combined_roof_torsion_rad",
             "cumulative_modal_participation_fraction"]
    tab="".join("<tr>"+"".join(f'<td>{e(s.get(k))}</td>' for k in headers)+"</tr>" for s in r["participation_summaries"])
    ch="".join(f'<section><h2>Chapter {e(c["id"])} — {e(c["title"])}</h2><div class="scroll"><table><tr><th>Module</th><th>Calculation scope</th></tr>'+
        "".join(f'<tr><td>{e(m["id"])}</td><td>{e(m["status"])}</td></tr>' for m in c["modules"])+
        '</table></div></section>' for c in r["chapters"])
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>R6.2 same connected shell modal CQC</title><style>body{{font:14px/1.5 system-ui;max-width:1120px;margin:auto;padding:16px;background:#f4f7fb;color:#253952}}header,section{{border:1px solid #d8e1ed;border-radius:11px;background:white;padding:19px;margin:14px 0}}.hold{{border-left:5px solid #b55245;background:#fff1eb;padding:10px}}.scroll{{overflow:auto}}table{{border-collapse:collapse;width:100%;min-width:680px}}td,th{{border:1px solid #d8e1ed;padding:8px;text-align:left;font-size:12px}}th{{background:#f0f3f8}}@media print{{body{{background:white}}}}</style></head><body><header>
<h1>R6.2 Connected ShellMITC4 modal analysis and MRSM actions</h1>
<p class="hold"><strong>NOT ENGINEER APPROVED — NOT FOR CONSTRUCTION OR PERMITS.</strong> Original project footing F3 remains NOT SAFE IN ONE WAY SHEAR.</p>
<p>Source audited seismic weight {r["audited_seismic_weight_kN"]:.2f} kN, mass {r["audited_seismic_mass_kN_s2_m"]:.6g} kN·s²/m; exact same R5.6 shell/beam/column mesh with flexible shell or rigid in-plane MPC. Source modal inertia loads actually solved on connected FEM, not canonical-frame proxies.</p>
<p>Output <a href="{PFX}.json">Numerical JSON</a> · <a href="{PFX}-modal.csv">Mode and mass participation CSV</a> · <a href="{PFX}-member-actions.csv">Modal and CQC member forces CSV</a> · <a href="{PFX}-manifest.json">SHA-256 manifest</a></p></header>
<section><h2>Mode/mass/diaphragm comparison — unsigned CQC responses</h2><div class="scroll"><table><tr>{''.join("<th>"+e(k)+"</th>" for k in headers)}</tr>{tab}</table></div>
<p><strong>Important:</strong> CQC combines signed per-mode components into <em>nonnegative scalar response maxima</em>. These values do not occur simultaneously and cannot be substituted for signed RC ULS member force combinations.</p></section>
{ch}<section><h2>Source and physical engineering holds</h2><ul>{''.join("<li>"+e(x)+"</li>" for x in r["remaining"])}</ul></section></body></html>"""

def emit(spec_path:Path,settings_path:Path,folder:Path,meshes=MESHES):
    r=build(json.loads(spec_path.read_text(encoding="utf-8")),
            json.loads(settings_path.read_text(encoding="utf-8")),meshes=meshes)
    folder.mkdir(parents=True,exist_ok=True)
    rows=[]
    members=[]
    for x in r["participation_summaries"]:
        for mode in x["modes"]:
            rows.append({"mesh":x["mesh"],"diaphragm_mode":x["diaphragm_mode"],
                "axis":x["axis"],**mode})
        for v in x["member_CQC_envelopes"]:
            members.append({"mesh":x["mesh"],"diaphragm_mode":x["diaphragm_mode"],
                 "axis":x["axis"],"mode":"CQC_MAGNITUDE", "member_id":v["member_id"],
                 "segment_tag":v["segment_tag"],"end":v["end"],**v["CQC_magnitude"]})
    for x in r["raw_modal_static_results"]:
        for m,segments in x["native_IJ_member_actions"].items():
            for seg in segments:
                for end in ("I","J"):
                    members.append({"mesh":x["mesh"],"diaphragm_mode":x["diaphragm_mode"],
                     "axis":x["axis"],"mode":x["mode"],"member_id":m,
                     "segment_tag":seg["tag"],"end":end,**seg[end]})
    artifacts={
     PFX+".json":json.dumps(r,sort_keys=True,indent=2,allow_nan=False)+"\n",
     PFX+".html":render_html(r),
     PFX+"-modal.csv":_csv(rows,["mesh","diaphragm_mode","axis","mode","period_s","omega_rad_s",
          "effective_modal_mass","participation_fraction","cumulative_participation_fraction",
          "base_shear_kN","roof_R1_m","drift_ratio","torsion_rad"]),
     PFX+"-member-actions.csv":_csv(members,["mesh","diaphragm_mode","axis","mode",
          "member_id","segment_tag","end",*COMPONENTS])}
    for name,data in artifacts.items():(folder/name).write_text(data,encoding="utf-8")
    manifest={"schema":"jp.structural.r6.connected_shell_modal_manifest.v0.1",
        "source_sha256":r["source_sha256"],"settings_sha256":r["settings_sha256"],
        "files":{n:hashlib.sha256(b.encode("utf-8")).hexdigest() for n,b in artifacts.items()},
        "engineering_approval":False}
    (folder/(PFX+"-manifest.json")).write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return r

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--input",type=Path,default=DEFAULT)
    a.add_argument("--settings",type=Path,default=SETTINGS)
    a.add_argument("--output-dir",type=Path,required=True)
    opts=a.parse_args()
    r=emit(opts.input,opts.settings,opts.output_dir)
    print("R6P2_SAME_CONNECTED_SHELL",r["native_modal_static_run_count"],"MODAL_NATIVE_CASES",r["audited_seismic_weight_kN"],"KN_MASS_F3_HOLD_NO_APPROVAL")
if __name__=="__main__":main()
