#!/usr/bin/env python3
"""R5.6 same connected shell/frame: flexible vs rigid in-plane MPC and combos.

Three original signed source cases and source-declared concurrent factors
are solved within each identical 3D shell/frame mesh and each diaphragm
constraint mode. Per-component end force, corner displacements and support
reactions must match algebraic elastic superposition (never mix extrema).

RIGID_INPLANE_MPC ties Ux/Uy/Rz, leaves the shell's Uz/Rx/Ry free.
No code seismic acceptance, modal MRSM, selfweight or original building.
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
    DEFAULT,exact_reference,solve_mesh,ShellBridgeError,sha,MESHES)
from scripts.build_structural_template_engine import CONTRACT,COVERAGE

PFX="r5-shell-diaphragm-signed"
SCHEMA="jp.structural.r5.connected_shell_mpc_signed_combinations.v0.1"
MODES=("FLEXIBLE_SHELL","RIGID_INPLANE_MPC")
COMPONENTS=("N","Vy","Vz","T","My","Mz")
CASE_IDS=("DL","LL","HX")

def _close(a,b,label,abs_tol=1e-5):
    if not math.isclose(float(a),float(b),rel_tol=1e-8,abs_tol=abs_tol):
        raise ShellBridgeError(f"same-mesh signed case superposition failed for {label}: {a} != {b}")

def _source_combinations(spec):
    rows=spec.get("combinations")
    if not isinstance(rows,list) or not rows:raise ShellBridgeError("source signed combinations required")
    used=set();out=[]
    for row in rows:
        if not isinstance(row,dict) or set(row)!={"combination_id","source_id","components"}:
            raise ShellBridgeError("signed combination source schema invalid")
        cid=row["combination_id"]
        if not isinstance(cid,str) or not cid or cid in used or cid in CASE_IDS:
            raise ShellBridgeError("duplicate or conflicting signed combination identity")
        used.add(cid)
        if not isinstance(row["source_id"],str) or not row["source_id"]:
            raise ShellBridgeError("signed combination provenance missing")
        comps=row["components"]
        if not isinstance(comps,list) or not comps:raise ShellBridgeError("empty source factor ledger")
        weights={}
        for c in comps:
            if not isinstance(c,dict) or set(c)!={"case_id","factor"}:
                raise ShellBridgeError("source factor schema unsupported")
            name=c["case_id"];factor=c["factor"]
            if name not in CASE_IDS or name in weights:
                raise ShellBridgeError("duplicate/unknown load case factor")
            if isinstance(factor,bool) or not isinstance(factor,(float,int)) or not math.isfinite(factor):
                raise ShellBridgeError("nonfinite load case factor")
            weights[name]=float(factor)
        out.append((cid,weights))
    return out

def _superposition(raw,combo,factors):
    # All source actions are taken from the SAME 3D connected shell topology,
    # material, nodal mass and diaphragm mode; no envelope or stiffness mix.
    for i,v in enumerate(combo["applied_force_kN"]):
        _close(v,math.fsum(raw[c]["applied_force_kN"][i]*f for c,f in factors.items()),
               "external force",abs_tol=1e-7)
    for i,v in enumerate(combo["support_reactions_Fz_kN"]):
        _close(v,math.fsum(raw[c]["support_reactions_Fz_kN"][i]*f for c,f in factors.items()),
               "source reaction",abs_tol=2e-5)
    _close(combo["center_shell_Uz_m"],
           math.fsum(raw[c]["center_shell_Uz_m"]*f for c,f in factors.items()),
           "shell center displacement",abs_tol=1e-9)
    for corner,dofs in combo["corner_displacements_m"].items():
        for dof,value in dofs.items():
            _close(value,math.fsum(raw[c]["corner_displacements_m"][corner][dof]*f
                                   for c,f in factors.items()),
                   "corner displacement",abs_tol=1e-9)
    for mid,segments in combo["signed_member_end_actions"].items():
        for idx,seg in enumerate(segments):
            for end in ("I","J"):
                for axis in COMPONENTS:
                    _close(seg[end][axis],math.fsum(
                       raw[c]["signed_member_end_actions"][mid][idx][end][axis]*f
                       for c,f in factors.items()),
                       "concurrent local signed "+mid+"/"+end+"/"+axis,
                       abs_tol=2e-5)
    return True

def build(spec=None,meshes=MESHES):
    if spec is None:spec=json.loads(DEFAULT.read_text(encoding="utf8"))
    if tuple(meshes) not in ((2,4,8),(2,4),(2,)):
        raise ShellBridgeError("R5.6 bounded tested mesh choices are 2/4/8")
    ref=exact_reference(spec)
    combinations=_source_combinations(spec)
    results=[];comparisons=[];checks=[]
    for n in meshes:
        mode_results={}
        for mode in MODES:
            raw={cid:solve_mesh(ref,n,cid,diaphragm_mode=mode) for cid in CASE_IDS}
            combos={}
            for cid,factors in combinations:
                computed=solve_mesh(ref,n,cid,diaphragm_mode=mode,factors=factors)
                _superposition(raw,computed,factors)
                combos[cid]=computed
                checks.append({"mesh":n,"diaphragm_mode":mode,
                   "combination_id":cid,"source_factors":factors,
                   "concurrent_signed_member_actions_match_raw_case_superposition":True,
                   "same_shell_frame_stiffness_and_constraint_branch":True})
            all_rows=list(raw.values())+list(combos.values())
            if any(not x["global_equilibrium_pass"] for x in all_rows):
                raise ShellBridgeError("six-component support equilibrium failed")
            if any(x["source_seismic_weight_kN"]!=ref["audit"]["audited_assembly"]["total_seismic_weight_kN"] for x in all_rows):
                raise ShellBridgeError("seismic source mass mutated by mode/mesh/load case")
            if mode=="RIGID_INPLANE_MPC":
                if any(x["master_tag"]!=9900 or x["rigid_compatibility_residual_m"]>1e-8
                       for x in all_rows):
                    raise ShellBridgeError("rigid in-plane MPC not verified")
            mode_results[mode]={x["case_id"]:x for x in all_rows}
            results.extend(all_rows)
        for cid in list(CASE_IDS)+[c for c,_ in combinations]:
            flexible=mode_results["FLEXIBLE_SHELL"][cid]
            rigid=mode_results["RIGID_INPLANE_MPC"][cid]
            _close(flexible["applied_force_kN"][0],rigid["applied_force_kN"][0],
                   "mode matched applied Fx",abs_tol=1e-7)
            _close(flexible["applied_force_kN"][2],rigid["applied_force_kN"][2],
                   "mode matched applied Fz",abs_tol=1e-7)
            comparisons.append({
               "mesh":n,"case_id":cid,
               "flexible_center_Uz_m":flexible["center_shell_Uz_m"],
               "rigid_center_Uz_m":rigid["center_shell_Uz_m"],
               "center_Uz_difference_m":rigid["center_shell_Uz_m"]-flexible["center_shell_Uz_m"],
               "flexible_inplane_UX_strain_metric_m":flexible["inplane_row_UX_difference_m"],
               "rigid_inplane_UX_strain_metric_m":rigid["inplane_row_UX_difference_m"],
               "flexible_inplane_UY_strain_metric_m":flexible["inplane_col_UY_difference_m"],
               "rigid_inplane_UY_strain_metric_m":rigid["inplane_col_UY_difference_m"],
               "rigid_MPC_max_residual_m":rigid["rigid_compatibility_residual_m"],
               "same_3D_material_mesh_member_topology":True,
               "source_forces_identical":True,
            })
    if not any((r["flexible_inplane_UX_strain_metric_m"]>r["rigid_inplane_UX_strain_metric_m"]+1e-12
                or r["flexible_inplane_UY_strain_metric_m"]>r["rigid_inplane_UY_strain_metric_m"]+1e-12)
               for r in comparisons if r["case_id"]=="HX"):
        raise ShellBridgeError("flexible and rigid diaphragm have no independently observable in-plane difference")
    contract=json.loads(CONTRACT.read_text(encoding="utf8"))
    coverage={r["id"]:r for r in json.loads(COVERAGE.read_text(encoding="utf8"))["requirements"]}
    scope={"M02":"EXPLICIT_SOURCE_DL_LL_HX_AND_UNCHANGED_AUDITED_SEISMIC_MASS",
      "M04":"SAME_CONNECTED_3D_SHELL_FRAME_FLEXIBLE_VS_RIGID_XY_MPC",
      "M05":"SOURCE_DECLARED_SIGNED_STATIC_LOAD_FACTORS_NOT_CODE_CERTIFIED",
      "M08":"CONCURRENT_SIGNED_IJ_BEAM_FORCES_NO_FULL_RC_DESIGN",
      "M09":"CONCURRENT_SIGNED_COLUMN_ENDS_NO_COMPLETE_RC_DESIGN",
      "S17":"MP_CONSTRAINT_KINEMATICS_GLOBAL_6DOF_AND_SUPERPOSITION"}
    chapters=[{"id":x["id"],"title":x["title"],"modules":[{"id":i,"title":coverage[i]["title"],
        "status":scope.get(i,"NOT_CALCULATED_IN_THIS_ENGINE_INCREMENT")}
        for i in x["requirement_ids"]]} for x in contract["chapters"]]
    if len(chapters)!=7 or {x["id"] for c in chapters for x in c["modules"]}!=set(coverage):
        raise ShellBridgeError("seven chapter/eighteen module report contract drift")
    return {"schema":SCHEMA,"case_id":spec["case_id"],"source_SHA256":sha(spec),
       "source_mass_SHA256":ref["explicit_original_mass_SHA256"],
       "synthetic_source_gravity_kN":ref["audit"]["audited_assembly"]["total_gravity_load_kN"],
       "synthetic_source_seismic_weight_kN":ref["audit"]["audited_assembly"]["total_seismic_weight_kN"],
       "mesh_divisions":list(meshes),"diaphragm_modes":list(MODES),
       "raw_case_ids":list(CASE_IDS),"source_combinations":[
          {"combination_id":cid,"components":factors} for cid,factors in combinations],
       "solver_run_count":len(results),"superposition_check_count":len(checks),
       "mpc_comparison_count":len(comparisons),
       "connected_shell_solved_by_both_modes":True,
       "rigid_constraint_only_UX_UY_RZ":True,
       "flexible_slab_vertical_bending_preserved":True,
       "combined_signed_actions_solved_concurrently":True,
       "global_six_component_equilibrium_pass":True,
       "all_combination_superposition_checks_pass":True,
       "all_rigid_MPC_kinematic_checks_pass":True,
       "case_results":results,"diaphragm_comparisons":comparisons,
       "signed_checks":checks,"chapters":chapters,
       "original_F3_failure":"NOT SAFE IN ONE WAY SHEAR",
       "original_building_source_accepted":False,
       "original_building_evidence_gates_accepted":0,
       "engineering_approval":False,"permit_eligible":False,
       "code_load_factors_approved":False,"modal_or_PDelta_completed":False,
       "original_building_model":False,
       "open_debt":[
          "Single synthetic rectangle, original G+1.5 floor geometry and 15 physical evidence gates unverified.",
          "Rigid MPC enforces in-plane UX/UY/RZ only; vertical slab bending remains elastic shell FE.",
          "Static HX lateral loads and two signed combinations are sourced synthetic assumptions, NOT NBC design.",
          "No modal analysis, MRSM, accidental eccentricity, P-Delta or in-plane cracking under verified building mass.",
          "No signed shell section resultants/reinforcement design, verified slab thickness, original geotech or footing clearance.",
          "Original F3 source verdict NOT SAFE IN ONE WAY SHEAR has not changed."
       ]}

def _csv(rows,cols):
    b=io.StringIO();w=csv.writer(b,lineterminator="\n");w.writerow(cols)
    for row in rows:w.writerow([row.get(k) for k in cols])
    return b.getvalue()

def render_html(result):
    e=lambda x:html.escape(str(x),quote=True)
    cols=["mesh","case_id","flexible_inplane_UX_strain_metric_m","rigid_inplane_UX_strain_metric_m",
      "flexible_center_Uz_m","rigid_center_Uz_m"]
    table="".join("<tr>"+"".join(f"<td>{e(row.get(k))}</td>" for k in cols)+"</tr>"
                  for row in result["diaphragm_comparisons"])
    chapters="".join(f'<section id="ch-{e(c["id"])}"><h2>Chapter {e(c["id"])} — {e(c["title"])}</h2><table><tr><th>Module</th><th>Verification scope</th></tr>'+''.join(f'<tr><td>{e(x["id"])}</td><td>{e(x["status"])}</td></tr>' for x in c["modules"])+'</table></section>' for c in result["chapters"])
    comparison=f'<section><h2>Paired flexible-versus-rigid diaphragm load-case response</h2><div class="scroll"><table><tr>'+''.join(f'<th>{e(c)}</th>' for c in cols)+'</tr>'+table+'</table></div></section>'
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>R5.6 Connected Shell MPC and Signed Cases</title><style>body{{font:14px/1.5 system-ui;color:#243850;max-width:1050px;margin:auto;padding:16px;background:#f4f7fb}}header,section{{background:white;border:1px solid #d7e0ea;border-radius:10px;padding:18px;margin:15px 0}}.hold{{border-left:5px solid #b55849;padding:10px;background:#fff0ec}}.scroll{{overflow:auto}}table{{border-collapse:collapse;min-width:500px;width:100%;font-size:12px}}td,th{{border:1px solid #d2dce7;padding:7px;text-align:left}}th{{background:#edf2f6}}@media print{{body{{background:white}}}}</style></head><body><header>
<small>JP STRUCTURAL · R5.6 · SYNTHETIC CONNECTED SHELL/FRAME</small>
<h1>Flexible shell versus rigid in-plane diaphragm</h1>
<p class="hold"><strong>NOT ENGINEER APPROVED / NOT FOR MUNICIPAL PERMIT OR CONSTRUCTION.</strong> The original building's F3 remains NOT SAFE IN ONE WAY SHEAR.</p>
<p>Real connected 3D ShellMITC4 slab/frame with shared beam/column nodes; rigid MPC ties Ux, Uy and Rz only. {result["solver_run_count"]} distinct FE analyses across {len(result["mesh_divisions"])} meshes, 2 modes, 3 raw cases and {len(result["source_combinations"])} signed combinations. All global equilibrium, compatibility and superposition checks passed.</p>
<p>Source synthetic gravity {result["synthetic_source_gravity_kN"]:.1f}kN, unchanged source-assumed seismic-eligible weight {result["synthetic_source_seismic_weight_kN"]:.1f}kN.</p>
<p><a href="{PFX}.json">Calculation and signed member force JSON</a> · <a href="{PFX}-comparisons.csv">Mode comparison CSV</a> · <a href="{PFX}-member-actions.csv">Source-factored signed I/J CSV</a> · <a href="{PFX}-manifest.json">SHA manifest</a></p></header>
{comparison}{chapters}<section><h2>Annex: retained engineering holds</h2><ul>{''.join("<li>"+e(d)+"</li>" for d in result["open_debt"])}</ul></section></body></html>"""

def emit(output_dir:Path,spec=None,meshes=MESHES):
    r=build(spec,meshes=meshes)
    output_dir.mkdir(parents=True,exist_ok=True)
    actions=[]
    for run in r["case_results"]:
        for mid,segs in sorted(run["signed_member_end_actions"].items()):
            for seg in segs:
                for end in ("I","J"):
                    actions.append({"mesh":run["mesh_divisions"],"diaphragm_mode":run["diaphragm_mode"],
                       "case_id":run["case_id"],"member_id":mid,"element_tag":seg["element_tag"],
                       "end":end,**seg[end]})
    ccols=["mesh","case_id","flexible_center_Uz_m","rigid_center_Uz_m",
       "center_Uz_difference_m","flexible_inplane_UX_strain_metric_m",
       "rigid_inplane_UX_strain_metric_m","flexible_inplane_UY_strain_metric_m",
       "rigid_inplane_UY_strain_metric_m","rigid_MPC_max_residual_m"]
    files={
       PFX+".json":json.dumps(r,sort_keys=True,allow_nan=False,indent=2)+"\n",
       PFX+".html":render_html(r),
       PFX+"-comparisons.csv":_csv(r["diaphragm_comparisons"],ccols),
       PFX+"-member-actions.csv":_csv(actions,
          ["mesh","diaphragm_mode","case_id","member_id","element_tag","end",*COMPONENTS])}
    for fn,s in files.items():(output_dir/fn).write_text(s,encoding="utf8")
    m={"schema":"jp.structural.r5.mpc_signed_manifest.v0.1",
       "source_SHA256":r["source_SHA256"],
       "files":{fn:hashlib.sha256(s.encode("utf8")).hexdigest() for fn,s in files.items()},
       "engineering_approval":False}
    (output_dir/(PFX+"-manifest.json")).write_text(json.dumps(m,sort_keys=True,indent=2)+"\n",encoding="utf8")
    return r

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--output-dir",type=Path,required=True)
    args=a.parse_args()
    r=emit(args.output_dir)
    print("R5P6_SHELL_MPC_SIGNED",r["solver_run_count"],"RUNS",
          r["superposition_check_count"],"SUPERPOSITION_CHECKS_F3_UNSAFE_NO_APPROVAL")
if __name__=="__main__":main()
