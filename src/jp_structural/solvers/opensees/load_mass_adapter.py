"""Bridge audited load/mass assembly to bounded canonical OpenSees gravity analysis.

This adapter cannot derive geometry, slab tributary areas, code load factors,
soil springs or nonlinear RC behavior. It requires the exact same source node
coordinates in the canonical model and refuses pre-existing mass assignments.
Model: kN, m, s and mass kN*s²/m; 3D elastic frames only.
"""
from __future__ import annotations
import copy
import hashlib
import json
import math

import openseespy.opensees as ops

from jp_structural.solvers.opensees.canonical_frame import build_canonical_frame_model
from jp_structural.solvers.native.load_mass_assembly import (
    LoadAssemblyError, verify_vertical_support_equilibrium
)

class LoadMassAdapterError(ValueError):
    pass


def bind_assembly_to_canonical_model(model: dict, assembly: dict) -> dict:
    """Produce a NEW copy with source-exact nodal masses, no duplicate mass."""
    if not isinstance(model,dict) or not isinstance(assembly,dict):
        raise LoadMassAdapterError("canonical model and mass assembly required")
    if assembly.get("schema")!="jp.structural.load_mass_assembly.v0.1":
        raise LoadMassAdapterError("unrecognized assembly contract")
    u=model.get("units",{})
    for field,value in {"force":"kN","length":"m","time":"s","mass":"kN*s^2/m"}.items():
        if u.get(field)!=value:
            raise LoadMassAdapterError(f"canonical units.{field} must be {value}")
    if model.get("nodal_masses") or model.get("mass_source"):
        raise LoadMassAdapterError("existing nodal mass/mass source cannot be silently replaced")
    if model.get("joint_loads") or model.get("frame_loads") or model.get("area_loads"):
        raise LoadMassAdapterError("isolated gravity case forbids other active load records")
    nodes=model.get("nodes",[])
    by_id={r.get("id"):r for r in nodes}
    if len(by_id)!=len(nodes):
        raise LoadMassAdapterError("canonical model node IDs not unique")
    src_nodes=assembly.get("source_nodes")
    if not isinstance(src_nodes,list) or not src_nodes:
        raise LoadMassAdapterError("load assembly lacks source node geometry")
    used=set()
    for source in src_nodes:
        nid=source.get("node_id")
        if nid not in by_id or nid in used:
            raise LoadMassAdapterError("load node missing/duplicated in canonical model")
        used.add(nid)
        target=by_id[nid]
        if source.get("storey_id")!=target.get("storey_id"):
            raise LoadMassAdapterError("load node storey mismatch")
        for field,key in (("x_m","x"),("y_m","y"),("z_m","z")):
            try:a=float(source[field]);b=float(target[key])
            except (ValueError,TypeError,KeyError) as exc:
                raise LoadMassAdapterError("model coordinate not finite") from exc
            if not (math.isfinite(a) and math.isfinite(b) and math.isclose(a,b,rel_tol=0,abs_tol=1e-9)):
                raise LoadMassAdapterError(f"source/model geometry drift at {nid}:{field}")
    masses=assembly.get("nodal_masses",[])
    if not masses:
        raise LoadMassAdapterError("no seismic masses to apply")
    if any(row.get("node_id") not in used for row in masses):
        raise LoadMassAdapterError("mass node missing from source")
    new=copy.deepcopy(model)
    new["nodal_masses"]=copy.deepcopy(masses)
    prov=new.setdefault("provenance",{})
    if not isinstance(prov,dict):raise LoadMassAdapterError("model provenance must be object")
    canonical_json=json.dumps(assembly,sort_keys=True,separators=(",",":"),allow_nan=False)
    prov["load_mass_assembly_sha256"]=hashlib.sha256(canonical_json.encode()).hexdigest()
    prov["mass_assembly_formula_id"]=assembly.get("formula_id")
    prov["mass_engineering_approval"]=False
    return new


def run_audited_static_gravity(model: dict, assembly: dict, *, absolute_tolerance: float=1e-5) -> dict:
    """Solve one isolated 3D elastic gravity case and VERIFY global Rz/Mx/My.

    Uses the existing canonical elastic-frame builder. It is NOT a nonlinear
    design analysis; a passing equilibrium residual is not code/design acceptance.
    """
    if not isinstance(absolute_tolerance,(int,float)) or isinstance(absolute_tolerance,bool):
        raise LoadMassAdapterError("numeric absolute_tolerance required")
    if not math.isfinite(absolute_tolerance) or absolute_tolerance<=0:
        raise LoadMassAdapterError("positive finite absolute_tolerance required")
    resolved=bind_assembly_to_canonical_model(model,assembly)
    built=build_canonical_frame_model(resolved)
    case_id=901
    ops.timeSeries("Linear",case_id)
    ops.pattern("Plain",case_id,case_id)
    gravity_loads=assembly.get("gravity_nodal_loads",[])
    if not gravity_loads:
        raise LoadMassAdapterError("gravity nodal loads absent")
    for row in gravity_loads:
        nid=row.get("node_id")
        if nid not in built.node_tags:
            raise LoadMassAdapterError(f"gravity load references unknown node: {nid}")
        w=float(row["downward_load_kN"])
        if not math.isfinite(w) or w<0:raise LoadMassAdapterError("invalid gravity load")
        ops.load(built.node_tags[nid],0.,0.,-w,0.,0.,0.)
    ops.constraints("Transformation")
    ops.numberer("RCM")
    ops.system("BandGeneral")
    ops.algorithm("Linear")
    ops.integrator("LoadControl",1.)
    ops.analysis("Static")
    status=ops.analyze(1)
    if status!=0:raise LoadMassAdapterError(f"OpenSees gravity analysis failed: {status}")
    ops.reactions()
    support_nodes={str(r.get("node_id")) for r in resolved.get("supports",[])}
    if not support_nodes or not support_nodes.issubset(built.node_tags):
        raise LoadMassAdapterError("explicit support nodes required")
    reactions=[{"node_id":nid,"Rz_kN":float(ops.nodeReaction(built.node_tags[nid],3)),
                "Mx_kNm":float(ops.nodeReaction(built.node_tags[nid],4)),
                "My_kNm":float(ops.nodeReaction(built.node_tags[nid],5))}
               for nid in sorted(support_nodes)]
    try:
        equilibrium=verify_vertical_support_equilibrium(
            assembly["source_nodes"],gravity_loads,reactions,
            abs_tol=absolute_tolerance,rel_tol=1e-8)
    except LoadAssemblyError as exc:
        raise LoadMassAdapterError(f"global gravity equilibrium rejected: {exc}") from exc
    return {"schema":"jp.structural.opensees_gravity_run.v0.1",
            "solver":"OpenSeesPy","case":"EXPLICIT_STATIC_GRAVITY",
            "status":"ELASTIC_FRAME_GRAVITY_EQUILIBRIUM_PASS_NOT_DESIGN_APPROVAL",
            "analysis_steps":1,"node_count":len(built.node_tags),
            "seismic_mass_nodes":len(built.node_masses),
            "model_source_sha256":resolved["provenance"]["load_mass_assembly_sha256"],
            "support_reactions":reactions,"equilibrium":equilibrium}
