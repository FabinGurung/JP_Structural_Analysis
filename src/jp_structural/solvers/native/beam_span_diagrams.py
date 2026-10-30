"""Source-audited in-span local Vz / My reconstruction for 3D elastic beams.

For canonical horizontal beam local z=global +Z and full-span -Wz, integrate
section equilibrium from OpenSees local I resisting end actions:

Vz(x) = Vz_I - w*x
My(x) = My_I + Vz_I*x - w*x^2/2

At x=L, Vz(L) = -Vz_J and My(L)=-My_J for a complete isolated member
free body (the end result vectors are *resisting* localForce values).
My in this module is the *sagging-positive local cut diagram convention*;
it is NOT the same sign as J-end resisting My. These signs are checked
against the actual J-end results for EVERY case, including signed combos.
This does not claim OpenSees section recorder output or inelastic behavior.
"""
from __future__ import annotations
import hashlib
import json
import math
from collections.abc import Mapping

class SpanDiagramError(ValueError):
    pass

def _num(v,field):
    if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):
        raise SpanDiagramError(f"{field}: finite numeric required")
    return float(v)

def _digest(o):
    return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()

def reconstruct_local_vertical_diagram(*,length_m,left:Mapping,right:Mapping,
                                        downward_uniform_kN_m,sample_divisions:int=16,
                                        residual_tolerance:float=1e-6):
    """Return section force samples including exact interior zero-shear location.

    The signed positive downward w is permitted to be negative for load
    combinations; x is measured from I towards J. Reconstructs ONLY local
    Vz and My. Full axial/torsion/second transverse direction not handled.
    """
    L=_num(length_m,"span")
    w=_num(downward_uniform_kN_m,"w")
    tol=_num(residual_tolerance,"tolerance")
    if L<=0 or tol<=0:raise SpanDiagramError("positive span/tolerance required")
    if isinstance(sample_divisions,bool) or not isinstance(sample_divisions,int) or not (2<=sample_divisions<=100):
        raise SpanDiagramError("bounded integer sample divisions 2..100 required")
    if not isinstance(left,Mapping) or not isinstance(right,Mapping):
        raise SpanDiagramError("I and J end source vectors required")
    i_v=_num(left.get("Vz"),"I.Vz");i_m=_num(left.get("My"),"I.My")
    j_v=_num(right.get("Vz"),"J.Vz");j_m=_num(right.get("My"),"J.My")
    def at(x):
        return {"x_m":x,"x_over_L":x/L,
                "Vz_section_kN":i_v-w*x,
                "My_sagging_positive_kNm":i_m+i_v*x-w*x*x/2}
    v_end=i_v-w*L
    m_end=i_m+i_v*L-w*L*L/2
    vr=v_end+j_v
    mr=m_end+j_m
    scale=max(1.,abs(i_v),abs(j_v),abs(w*L),abs(i_m)/L,abs(j_m)/L)
    if abs(vr)>max(tol,1e-9*scale) or abs(mr)>max(tol,1e-9*scale*L):
        raise SpanDiagramError(f"local beam cut/J-end equilibrium failed: V={vr:g} M={mr:g}")
    xstar=i_v/w if abs(w)>1e-12 else None
    valid_star=xstar is not None and 0<xstar<L
    locs=[L*j/sample_divisions for j in range(sample_divisions+1)]
    if valid_star and all(abs(xstar-x)>1e-9 for x in locs):
        locs.append(xstar);locs.sort()
    samples=[at(x) for x in locs]
    # Quadratic moment under uniform w has only one interior stationary
    # location. Extremal values among ends plus xstar are therefore exact.
    extrema=[at(0.),at(L)]
    if valid_star:extrema.append(at(xstar))
    max_my=max(extrema,key=lambda x:x["My_sagging_positive_kNm"])
    min_my=min(extrema,key=lambda x:x["My_sagging_positive_kNm"])
    return {
        "schema":"jp.structural.beam_span_vertical_diagram.v0.1",
        "length_m":L,"w_downward_signed_kN_m":w,
        "convention":"I_LOCAL_RESISTING_MY_TO_SAGGING_POSITIVE_CUT_MY; J_BOUNDARY_NEGATED",
        "formula":{"Vz":"Vz_I - w*x","My":"My_I + Vz_I*x - w*x*x/2"},
        "samples":samples,"sample_count":len(samples),
        "zero_shear_inside_member_x_m":xstar if valid_star else None,
        "critical_moment_max":max_my,"critical_moment_min":min_my,
        "cut_left":{"Vz_kN":i_v,"My_kNm":i_m},
        "cut_right":{"Vz_kN":v_end,"My_kNm":m_end},
        "J_resisting":{"Vz_kN":j_v,"My_kNm":j_m},
        "end_boundary_residuals":{"Vz_kN":vr,"My_kNm":mr},
        "end_equilibrium_pass":True,
        "unsupported_axes_or_effects":["LOCAL_VY_MZ","AXIAL_DISTRIBUTION","TORSION","POINT_LOADS","PARTIAL_LOADS","INELASTIC_SECTIONS"],
        "engineering_approval":False,
    }

def build_signed_span_diagrams(*,model:dict,solved:dict,raw_cases:list,combinations:list,
                                sample_divisions:int=16):
    """Source-bound beam diagrams for raw and concurrent signed cases.

    Checks the signed FE SHA and exact case factors before reconstructing.
    No inferred member x/y/z axes or undocumented uniform load assumptions.
    """
    if solved.get("schema")!="jp.structural.signed_design_actions.v0.1" or solved.get("engineering_approval") is not False:
        raise SpanDiagramError("unsigned/approved/unsupported solver source")
    if solved.get("model_id")!=model.get("model_id"):
        raise SpanDiagramError("diagram source model ID mismatch")
    original={"model":model,"cases":raw_cases,"combinations":combinations}
    if _digest(original)!=solved.get("input_bundle_sha256"):
        raise SpanDiagramError("source signed action bundle digest mismatch")
    result_digest=_digest({"raw_cases":solved["raw_cases"],"combinations":solved["combinations"]})
    if result_digest!=solved.get("results_digest_sha256"):
        raise SpanDiagramError("tampered signed local end forces")
    nodes={x["id"]:x for x in model["nodes"]}
    members={x["id"]:x for x in model["frame_members"]}
    if len(nodes)!=len(model["nodes"]) or len(members)!=len(model["frame_members"]):
        raise SpanDiagramError("duplicate model node/member IDs")
    beams={}
    for mid,m in members.items():
        if m.get("member_type")!="BEAM":continue
        if any(m.get(k) is not None for k in ("local_axis_vector","local_axis_angle","orientation")):
            raise SpanDiagramError("explicit beam local orientation unsupported for this vertical diagram")
        a,b=nodes[m["i_node"]],nodes[m["j_node"]]
        coords=tuple(_num(b[k],k)-_num(a[k],k) for k in ("x","y","z"))
        if abs(coords[2])>1e-9:
            raise SpanDiagramError("inclined/vertical beams require a verified local load mapper")
        L=math.hypot(coords[0],coords[1])
        if L<=1e-9:raise SpanDiagramError("collapsed beam length")
        beams[mid]=L
    if not beams:raise SpanDiagramError("no eligible horizontal BEAM members")
    source={x["case_id"]:x for x in raw_cases}
    if len(source)!=len(raw_cases):raise SpanDiagramError("duplicate raw case")
    weights={}
    for cid,case in source.items():
        bymid={}
        for entry in case.get("uniform_beam_loads",[]):
            mid=entry["member_id"]
            if mid not in beams:raise SpanDiagramError("uniform load member must be eligible BEAM")
            bymid[mid]=bymid.get(mid,0.)+_num(entry["downward_kN_per_m"],"source beam w")
        weights[cid]=bymid
    records=[]
    for kind,cases in (("RAW",solved["raw_cases"]),("COMBINATION",solved["combinations"])):
        for r in cases:
            cid=r["case_id"] if kind=="RAW" else r["combination_id"]
            if kind=="RAW":
                if cid not in source:raise SpanDiagramError("solved unrecognized raw case")
                factors={cid:1.}
            else:
                spec=next((c for c in combinations if c["combination_id"]==cid),None)
                if spec is None:raise SpanDiagramError("unknown combination")
                factors={x["case_id"]:_num(x["factor"],"case factor") for x in spec["components"]}
                if len(factors)!=len(spec["components"]):raise SpanDiagramError("duplicated combination components")
                if set(factors)!={x["case_id"] for x in r["signed_factors"]}:
                    raise SpanDiagramError("combination components differ from solver")
                for x in r["signed_factors"]:
                    if not math.isclose(factors[x["case_id"]],x["factor"],abs_tol=1e-10,rel_tol=1e-10):
                        raise SpanDiagramError("combination factor tampered")
            for mid,L in beams.items():
                w=math.fsum(weights[sid].get(mid,0.)*factor for sid,factor in factors.items())
                end=r["local_end_resisting_actions"][mid]
                out=reconstruct_local_vertical_diagram(
                    length_m=L,left=end["I"],right=end["J"],
                    downward_uniform_kN_m=w,sample_divisions=sample_divisions)
                records.append({
                   "kind":kind,"case_id":cid,"member_id":mid,
                   "downward_uniform_signed_kN_m":w,
                   "local_end_source_SHA256":solved["results_digest_sha256"],
                   "diagram":out,
                })
    if len(records)!=(len(raw_cases)+len(combinations))*len(beams):
        raise SpanDiagramError("missing case-member diagram records")
    return {
       "schema":"jp.structural.signed_span_diagram_collection.v0.1",
       "model_id":model["model_id"],
       "source_signed_input_sha256":solved["input_bundle_sha256"],
       "source_signed_result_sha256":solved["results_digest_sha256"],
       "source_member_count":len(beams),
       "signed_case_count":len(raw_cases),
       "signed_combination_count":len(combinations),
       "diagram_record_count":len(records),
       "diagrams":records,
       "all_J_cut_boundary_equilibrium_pass":all(x["diagram"]["end_equilibrium_pass"] for x in records),
       "engineering_approval":False,
    }
