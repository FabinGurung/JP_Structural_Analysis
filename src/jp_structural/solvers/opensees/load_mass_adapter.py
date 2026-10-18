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


def _verify_assembly_contract(assembly: dict) -> None:
    """Reject altered or internally inconsistent input before OpenSees sees it.

    Validates totals, source identity and nodal moment/mass geometry. This does
    not assert that a source component is physically present in a building.
    """
    if assembly.get("status") != "SOURCE_ASSIGNED_NUMERIC_CONSERVATION_PASS_NOT_ENGINEERING_APPROVAL":
        raise LoadMassAdapterError("unverified load mass assembly status")
    if assembly.get("units") != {"force":"kN","length":"m","time":"s","mass":"kN*s^2/m"}:
        raise LoadMassAdapterError("load mass assembly units mismatch")

    def num(value, field, *, strict=False):
        if isinstance(value, bool):
            raise LoadMassAdapterError(f"{field}: boolean invalid")
        try: v=float(value)
        except (ValueError, TypeError, OverflowError) as exc:
            raise LoadMassAdapterError(f"{field}: expected a finite number") from exc
        if not math.isfinite(v) or v<0 or (strict and v<=0):
            raise LoadMassAdapterError(f"{field}: finite nonnegative value required")
        return v

    def close(value, expected, name):
        if not math.isclose(value,expected,rel_tol=1e-8,abs_tol=1e-7):
            raise LoadMassAdapterError(f"{name}: derived totals disagree")

    g=num(assembly.get("gravity_m_s2"),"gravity_m_s2",strict=True)
    declared_gravity=num(assembly.get("total_gravity_load_kN"),"total_gravity_load_kN",strict=True)
    declared_seismic=num(assembly.get("total_seismic_weight_kN"),"total_seismic_weight_kN",strict=True)

    sources=assembly.get("sources")
    if not isinstance(sources,list) or not sources:
        raise LoadMassAdapterError("load mass assembly sources required")
    source_keys=set(); source_ids=set(); weight=[]; seismic=[]
    for row in sources:
        if not isinstance(row,dict):
            raise LoadMassAdapterError("source row must be an object")
        sid=row.get("id"); key=row.get("source_key")
        if not isinstance(sid,str) or not sid or not isinstance(key,str) or not key:
            raise LoadMassAdapterError("source identity required")
        if sid in source_ids or key in source_keys:
            raise LoadMassAdapterError("duplicate physical source/component in mass assembly")
        source_ids.add(sid);source_keys.add(key)
        w=num(row.get("gravity_weight_kN"),"source.gravity_weight_kN")
        s=num(row.get("seismic_weight_kN"),"source.seismic_weight_kN")
        if s>w+1e-8:
            raise LoadMassAdapterError("source seismic weight exceeds original gravity load")
        weight.append(w);seismic.append(s)
    close(math.fsum(weight),declared_gravity,"source gravity")
    close(math.fsum(seismic),declared_seismic,"source seismic")

    source_nodes=assembly.get("source_nodes")
    if not isinstance(source_nodes,list) or not source_nodes:
        raise LoadMassAdapterError("source node list required")
    nodeids=set();coord={}
    for n in source_nodes:
        if not isinstance(n,dict):
            raise LoadMassAdapterError("source node must be an object")
        key=n.get("node_id")
        if not isinstance(key,str) or not key or key in nodeids:
            raise LoadMassAdapterError("source node ID must be unique and nonempty")
        nodeids.add(key)
        try:
            xy=(float(n["x_m"]),float(n["y_m"]))
        except (KeyError,TypeError,ValueError,OverflowError) as exc:
            raise LoadMassAdapterError("source node geometry invalid") from exc
        if not all(math.isfinite(x) for x in xy):
            raise LoadMassAdapterError("source coordinates not finite")
        coord[key]=xy

    gravity_nodes=assembly.get("gravity_nodal_loads")
    mass_nodes=assembly.get("nodal_masses")
    if not isinstance(gravity_nodes,list) or not gravity_nodes or not isinstance(mass_nodes,list) or not mass_nodes:
        raise LoadMassAdapterError("nodal gravity and seismic mass records required")
    loads=[]; masses=[]; seen=set(); loaded_by_node={}
    for row in gravity_nodes:
        key=row.get("node_id")
        if key not in nodeids or key in seen:
            raise LoadMassAdapterError("gravity node unknown or duplicated")
        seen.add(key)
        w=num(row.get("downward_load_kN"),"gravity_nodal_load",strict=True)
        loads.append(w);loaded_by_node[key]=w
    seen.clear()
    seismic_by_node={}
    for row in mass_nodes:
        key=row.get("node_id")
        if key not in nodeids or key in seen:
            raise LoadMassAdapterError("seismic mass node unknown or duplicated")
        seen.add(key)
        m=num(row.get("mx"),"nodal_mx",strict=True)
        for axis in ("my","mz"):
            v=num(row.get(axis),f"nodal_{axis}",strict=True)
            close(v,m,f"nodal {axis}/mx")
        for rotation in ("mrx","mry","mrz"):
            if num(row.get(rotation),f"nodal_{rotation}")!=0:
                raise LoadMassAdapterError("rotational mass requires independently verified inertia")
        masses.append(m);seismic_by_node[key]=m*g
    close(math.fsum(loads),declared_gravity,"nodal gravity")
    close(math.fsum(masses)*g,declared_seismic,"nodal seismic mass")

    # The source allocation never includes a floor whose seismic mass is zero
    # in its storey summary; check all reported positive-mass storey centres.
    storeys=assembly.get("storeys")
    if not isinstance(storeys,list) or not storeys:
        raise LoadMassAdapterError("positive mass storey summary required")
    seen_stories=set()
    storey_ids={n["node_id"]:n.get("storey_id") for n in source_nodes}
    for story in storeys:
        sid=story.get("storey_id")
        if not isinstance(sid,str) or not sid or sid in seen_stories:
            raise LoadMassAdapterError("storey summary identity invalid")
        seen_stories.add(sid)
        ids=[key for key in seismic_by_node if storey_ids[key]==sid]
        if not ids:raise LoadMassAdapterError("empty storey with reported seismic mass")
        subtotal=math.fsum(seismic_by_node[key] for key in ids)
        close(subtotal,num(story.get("seismic_weight_kN"),"storey seismic weight"),"storey seismic")
        gravity_story=math.fsum(val for key,val in loaded_by_node.items() if storey_ids[key]==sid)
        close(gravity_story,num(story.get("gravity_kN"),"storey gravity weight"),"storey gravity")
        for name,i in (("center_mass_x_m",0),("center_mass_y_m",1)):
            try:
                requested=float(story[name])
            except (KeyError,ValueError,TypeError) as exc:
                raise LoadMassAdapterError("storey centre missing") from exc
            if not math.isfinite(requested):
                raise LoadMassAdapterError("storey centre nonfinite")
            true=math.fsum(coord[k][i]*seismic_by_node[k] for k in ids)/subtotal
            if not math.isclose(true,requested,rel_tol=1e-8,abs_tol=1e-8):
                raise LoadMassAdapterError("storey centre inconsistent with nodal masses")
    if seen_stories!={storey_ids[key] for key in seismic_by_node}:
        raise LoadMassAdapterError("storey summary incomplete")


def bind_assembly_to_canonical_model(model: dict, assembly: dict) -> dict:
    """Produce a NEW copy with source-exact nodal masses, no duplicate mass."""
    if not isinstance(model,dict) or not isinstance(assembly,dict):
        raise LoadMassAdapterError("canonical model and mass assembly required")
    if assembly.get("schema")!="jp.structural.load_mass_assembly.v0.1":
        raise LoadMassAdapterError("unrecognized assembly contract")
    _verify_assembly_contract(assembly)
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
            [{"node_id":n["id"],"x_m":n["x"],"y_m":n["y"]} for n in resolved["nodes"]],
            gravity_loads,reactions,
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
