"""R6.26 independent Narayani frame-only OpenSees calculation and source ledger.

Source: pinned source-DXF-derived R6.25 Narayani graph.
Actual source locations are preserved; floors, 23 vertical columns, nearest
beam-to-column connections and elastic joint stiffness are explicitly assumed.
This is not a qualified building analysis or the source ETABS result.

Units: kN, m, kNm, kPa. Full six-component force/moment equilibrium required.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from hashlib import sha256
import json
import math
from pathlib import Path
from typing import Any

from r6p25.qa_export import build as source_graph, CAD_SHA

SCHEMA="jp.structural.r6p26.narayani_assumed_independent_frame.v0.1"
LEVELS=("B","GF","FF","SF")
CASE_NAMES=("DL","LL","PX10","PY10")
DOF=("Fx","Fy","Fz","Mx","My","Mz")
ACT=("N","Vy","Vz","T","My","Mz")


class EngineHold(ValueError):
    """Fail-closed numerical modeling or physical engineering acceptance hold."""


def require(ok:bool,why:str)->None:
    if not ok:
        raise EngineHold("R6.26 ENGINEERING HOLD: "+why)


def digest(value:Any)->str:
    return sha256(json.dumps(value,sort_keys=True,separators=(",",":"),
                             allow_nan=False).encode("utf-8")).hexdigest()


def make_spec(cad_root:Path)->dict:
    data=source_graph(cad_root)
    require(data["classification"]=="ORIGINAL_DXF_SOURCE_DERIVED_WITH_ASSUMED_UNVERIFIED_CONNECTIONS",
            "pinned original-DXF provenance required")
    require(data["cad_source_sha"]==CAD_SHA and not data["engineering_approval"]
            and not data["actual_independent_FE_run"],"source QA provenance/approval changed")
    require(data["basis"]["concrete_unit_weight_kN_m3"]==20
            and data["basis"]["seismic_code"]=="NBC 105:2025","user-approved basis missing")
    cols=data["columns"]
    require(len(cols)==23 and len(data["beams"])==66,"R6.25 source drawing element count changed")
    # Source revised report: storey 3.05m, slab 0.13m, main-beam 0.23x0.40m,
    # M20 concrete E=22,360.68 MPa; room LL=2kPa; wall UDL 9.24/4.47kN/m.
    # Missing per-floor slab boundaries/actual beams -> uniformly applied
    # *illustrative area-proxy nodal loads*, NOT a defensible structural load path.
    story=3.05
    floors=[{"id":"GF","z_m":story,"area_m2":205.16},
            {"id":"FF","z_m":2*story,"area_m2":200.67},
            {"id":"SF","z_m":3*story,"area_m2":175.62}]
    nodes=[]
    for i,level in enumerate(LEVELS):
        for c in cols:
            nodes.append({"id":level+":"+c["id"],"floor":level,
                          "column_axis":c["source_axis"],"x_m":c["x"],
                          "y_m":c["y"],"z_m":round(i*story,5),
                          "source":"GF_XY_FROM_PINNED_ORIGINAL_DXF",
                          "level_status":"ASSUMED_VERTICAL_EXTENSION" if i else
                                         "GF_DRAWING_SOURCE_BASE_CANDIDATE"})
    cmap={c["id"]:c for c in cols}
    beams=[]; audit=[]; seen=set()
    for b in data["beams"]:
        floor=b["level"]
        js=b["assumed_endpoint_joints"]
        i,j=js[0]["column_id"],js[1]["column_id"]
        if i==j:
            audit.append({"id":b["id"],"level":floor,
                          "reason":"BOTH_SOURCE_ENDPOINTS_MAP_TO_ONE_COLUMN",
                          "source_DXF_handles":b["original_DXF_handles"]})
            continue
        key=(floor,)+tuple(sorted((i,j)))
        if key in seen:
            audit.append({"id":b["id"],"level":floor,
                          "reason":"DUPLICATE_MAPPED_JOINT_PAIR_NOT_DOUBLE_MODELED",
                          "source_DXF_handles":b["original_DXF_handles"]})
            continue
        seen.add(key)
        ci,cj=cmap[i],cmap[j]
        length=math.hypot(ci["x"]-cj["x"],ci["y"]-cj["y"])
        require(0.30<length<45,"source-proxy beam length outside research range")
        beams.append({
            "id":b["id"],"type":"beam","floor":floor,
            "ni":floor+":"+i,"nj":floor+":"+j,
            "width_m":0.23, "depth_m":0.40,
            "length_m":round(length,7),
            "source_DXF_handles":b["original_DXF_handles"],
            "source_original_width_m":b["section_width_source_m"],
            "source_candidate_endpoints_m":b["endpoints"],
            "assumed_joint_gaps_m":[x["distance_m"] for x in js],
            "provisional_level":any(not x["plan_near_750mm"] for x in js),
            "geometry_status":"BEAM_SNAPPED_TO_NEAREST_GF_COLUMN_ASSUMED_NOT_SOURCE_VERIFIED",
        })
    members=[]
    for i in range(3):
        for c in cols:
            section=c["family"]
            require(section in {"C1","C2","C3","C4"},
                    "unrecognized source-reported column family")
            # C4: 350mm circular source report; C1–C3: 400x400mm.
            members.append({
                "id":"COL:"+str(i+1)+":"+c["id"],
                "type":"column","floor":LEVELS[i+1],
                "ni":LEVELS[i]+":"+c["id"],"nj":LEVELS[i+1]+":"+c["id"],
                "section":section,
                "diameter_m":0.35 if section=="C4" else None,
                "width_m":0.40 if section!="C4" else None,
                "depth_m":0.40 if section!="C4" else None,
                "length_m":story,
                "source_axis":c["source_axis"],
                "geometry_status":"GF_COLUMN_CROSS_SECTION_DECLARED_EXTENDED_THROUGH_ALL_STORIES_ASSUMED",
            })
    members.extend(beams)
    require(len(members)>=69 and len(beams)>0,"no 3D source frame created")
    areas={c["id"]:c["source_axis"] for c in cols}
    require(len(set(areas.values()))==23,"column axes are not source-unique")
    spec={
        "schema":SCHEMA,"project":"Narayani Parajuli — proposed Block B",
        "project_id":"PRJ-000007","location":"Pokhara Metropolitan City-15, Nepal",
        "classification":"ACTUAL_DXF_COORDINATES_AND_ASSUMED_UNVERIFIED_FRAME_LOADS",
        "geometry_source_cad_commit":CAD_SHA,
        "source_graph_digest":digest(data),
        "authoritative_source_report":{
            "title":"A Structural Analysis and Design Report for G+1.5 Storey Residential Building",
            "format":"ETABS v20.0.0 original report; independently generated output here",
            "gdrive_file_id":"1TpWUmOdrcQqOpkN6qvmhZ12KrYaNABBM",
        },
        "report_basis":{
            "concrete_grade":"M20",
            "reinforcement":"Fe500",
            "E_kN_m2":22360680.0,  # source report Ec 22360.68 MPa
            "E_provenance":"SOURCE_REVISED_REPORT_Ec_22360p68_MPa_NO_CRACKED_STIFFNESS",
            "poisson_assumed":0.2,
            "concrete_unit_weight_kN_m3":20.0,
            "storey_height_m":story,
            "floor_slab_depth_m":0.13,
            "beam_width_m":0.23,
            "beam_depth_m":0.40,
            "floor_finish_kPa":1.5,
            "floor_finish_status":"PROVISIONAL_R6P23_DEFAULT_NOT_AS_BUILT",
            "residential_room_imposed_kPa":2.0,
            "imposed_load_provenance":"SOURCE_REVISED_REPORT_RESIDENTIAL_ROOM__NOT_FULL_OCCUPANCY_ZONES",
            "main_wall_source_line_load_kN_m":9.24,
            "partition_wall_source_line_load_kN_m":4.47,
            "wall_load_applied_to_FE":False,
            "wall_omission_reason":"GF/FF/SF actual wall line classification/openings/support not source connected",
            "seismic_code_edition":"NBC 105:2025",
            "seismic_site_class_2025":"UNRESOLVED_VS30",
            "site_soil_bearing_scenario_kPa":160.0,
            "geotech_report_source_kPa":166.0,
            "foundation_design_performed":False,
            "gravity_slab_distribution":
                "EQUAL_NODAL_AREA_PROXY_ONLY__NO_VERIFIED_SLAB_TO_BEAM_SUPPORT",
            "lateral_scenarios":"PX10 and PY10: 10 kN at EACH elevated floor, "
               "diagnostic ONLY; not NBC 105 equivalent static or response spectrum",
            "joint_assumption":"RIGID_RC_FRAME_CONNECTION_PROVISIONAL",
            "foundation_assumption":"ALL_23_GF_COLUMN_BASES_FIXED__NOT_SOIL_SPRINGS",
        },
        "floors":floors,"nodes":nodes,"members":members,
        "mapping_audit":audit,
        "source_candidate_beams":len(data["beams"]),
        "beam_members_modeled":len(beams),
        "source_GF_column_mark_count":23,
        "assumed_vertical_segments":69,
        "source_footing_outline_count":21,
        "selected_footings":[{"id":f["id"],"family":f["family"],
            "width_m":f["width_m"],"depth_m":f["depth_m"],
            "original_DXF_handle":f["handle"]}
            for f in data["footings"]],
        "holds":[
            "23 GF columns assumed to continue unchanged through 3 floors; actual FF/SF column alignments unverified",
            "Beam candidate edges snapped to nearest column nodes including 19 gap endpoints; no source-verified load path",
            "Duplicate/same-column source line candidates are omitted from FE and fully recorded",
            "Only ordinary beam/column 3D elastic frame stiffness is solved, no true shell/slab/diaphragm FE, shear walls or stairs",
            "Slab source areas are architectural plan areas not verified load-bearing shell areas; loads distributed equally at column nodes",
            "Wall line loads published by original report are NOT applied; actual wall positions/sections not verified",
            "Concrete Ec from original report and gamma 20 owner-approved; cracked/nonlinear stiffness, joint zone behavior unresolved",
            "PX10/PY10 are fixed 10kN/floor lateral stability probes, NOT NBC 105:2025 seismic design actions",
            "Soil class 2020 Type B vs structural report Type D; 2025 VS30 and site-specific spectrum unresolved",
            "All 23 column-base nodes fixed; geotechnical reactions and foundation springs NOT modeled",
            "F3 'NOT SAFE IN ONE WAY SHEAR' retained; individual G1/CF1 design checks not resolved",
            "Actual member design, reinforcement, slab one/two-way checks, punching, seismic ULS/SLS, wind and staircase remain unverified"
        ],
        "engineering_approval":False,"construction_release":False,
        "full_structural_report_reproduced":False,
    }
    return spec


def section(m:dict)->tuple[float,float,float,float,float]:
    """Area, J, Iy, Iz, area_used_for_concrete_selfweight."""
    if m["type"]=="column" and m["section"]=="C4":
        d=m["diameter_m"]
        A=math.pi*d*d/4
        I=math.pi*d**4/64
        J=math.pi*d**4/32
        return A,J,I,I,A
    w=m["width_m"];h=m["depth_m"]
    A=w*h
    Iy=w*h**3/12
    Iz=h*w**3/12
    J=(w*h)*min(w,h)**2/3
    # Floor slab selfweight is already counted at the floor nodes:
    # use downstand-only section depth in beam source ledger to avoid double count.
    mass_area=A if m["type"]=="column" else w*(h-0.13)
    require(mass_area>0, "beam downstand selfweight must be positive")
    return A,J,Iy,Iz,mass_area


def loads(spec:dict)->tuple[dict,dict]:
    nodes={n["id"]:n for n in spec["nodes"]}
    L={case:defaultdict(lambda:[0.,0.,0.]) for case in CASE_NAMES}
    source=defaultdict(float)
    gamma=spec["report_basis"]["concrete_unit_weight_kN_m3"]
    for member in spec["members"]:
        A,J,Iy,Iz,mass_area=section(member)
        weight=gamma*mass_area*member["length_m"]
        for k in (member["ni"],member["nj"]):
            L["DL"][k][2]-=weight/2.
        source["column_concrete_kN" if member["type"]=="column" else "beam_downstand_concrete_kN"]+=weight
    for floor in spec["floors"]:
        nids=[n["id"] for n in spec["nodes"] if n["floor"]==floor["id"]]
        require(len(nids)==23,"floor physical supports changed")
        slab=floor["area_m2"]*spec["report_basis"]["floor_slab_depth_m"]*gamma
        finish=floor["area_m2"]*spec["report_basis"]["floor_finish_kPa"]
        live=floor["area_m2"]*spec["report_basis"]["residential_room_imposed_kPa"]
        for node in nids:
            L["DL"][node][2]-=(slab+finish)/len(nids)
            L["LL"][node][2]-=live/len(nids)
            L["PX10"][node][0]+=10./len(nids)
            L["PY10"][node][1]+=10./len(nids)
        source["floor_slab_concrete_kN"]+=slab
        source["floor_finish_kN"]+=finish
        source["room_imposed_kN"]+=live
        source["probe_lateral_x_kN"]+=10.
        source["probe_lateral_y_kN"]+=10.
    result={case:{k:[round(float(v),11) for v in val]
                  for k,val in sorted(rows.items())}
            for case,rows in L.items()}
    source=dict(sorted(source.items()))
    source["DL_total_kN"]=(source["column_concrete_kN"]+
                          source["beam_downstand_concrete_kN"]+
                          source["floor_slab_concrete_kN"]+source["floor_finish_kN"])
    source["LL_total_kN"]=source["room_imposed_kN"]
    return result,source


def _six_about_origin(coords:tuple[float,float,float],
                      actions:list[float])->list[float]:
    x,y,z=coords;Fx,Fy,Fz,Mx,My,Mz=actions
    return [Fx,Fy,Fz,Mx+y*Fz-z*Fy,My+z*Fx-x*Fz,Mz+x*Fy-y*Fx]


def analyze(spec:dict)->dict:
    import openseespy.opensees as ops
    require(spec["schema"]==SCHEMA and spec["engineering_approval"] is False,
            "unapproved source-engine contract required")
    nodes={n["id"]:n for n in spec["nodes"]}
    loads_by_case,ledger=loads(spec)
    case_results={}
    for case in CASE_NAMES:
        ops.wipe()
        ops.model("basic","-ndm",3,"-ndf",6)
        tags={}
        for no,n in enumerate(spec["nodes"],1):
            tags[n["id"]]=no
            ops.node(no,n["x_m"],n["y_m"],n["z_m"])
            if n["floor"]=="B": ops.fix(no,1,1,1,1,1,1)
        # Local x for column is global z -> reference local z in global X;
        # horizontal beams use global Z as local reference for stable orientation.
        ops.geomTransf("Linear",1,1.,0.,0.)
        ops.geomTransf("Linear",2,0.,0.,1.)
        elem=[]
        E=spec["report_basis"]["E_kN_m2"]
        nu=spec["report_basis"]["poisson_assumed"]
        G=E/(2*(1+nu))
        for e,m in enumerate(spec["members"],1):
            A,J,Iy,Iz,ma=section(m)
            t=1 if m["type"]=="column" else 2
            ops.element("elasticBeamColumn",e,tags[m["ni"]],tags[m["nj"]],
                        A,E,G,J,Iy,Iz,t)
            elem.append((e,m))
        ops.timeSeries("Linear",1)
        ops.pattern("Plain",1,1)
        for n,actions in loads_by_case[case].items():
            ops.load(tags[n],*actions,0.,0.,0.)
        ops.constraints("Plain")
        ops.numberer("RCM")
        ops.system("BandGeneral")
        ops.test("NormDispIncr",1e-9,20)
        ops.algorithm("Linear")
        ops.integrator("LoadControl",1.0)
        ops.analysis("Static")
        status=ops.analyze(1)
        require(status==0,"independent OpenSees 3D elastic frame solve failed: "+case)
        ops.reactions()
        supports=[]
        applied=[0.]*6;rest=[0.]*6
        for node,vec in loads_by_case[case].items():
            n=nodes[node]
            x=_six_about_origin((n["x_m"],n["y_m"],n["z_m"]),
                                vec+[0.,0.,0.])
            applied=[a+b for a,b in zip(applied,x)]
        for n in spec["nodes"]:
            if n["floor"]!="B":continue
            v=list(ops.nodeReaction(tags[n["id"]]))
            require(len(v)==6 and all(math.isfinite(k) for k in v),
                    "invalid 6-axis base reaction "+n["id"])
            x=_six_about_origin((n["x_m"],n["y_m"],n["z_m"]),v)
            rest=[a+b for a,b in zip(rest,x)]
            supports.append({"node":n["id"],"axis":n["column_axis"],
                             "Fz_kN":float(v[2]),"Fx_kN":float(v[0]),
                             "Fy_kN":float(v[1]),"Mx_kNm":float(v[3]),
                             "My_kNm":float(v[4]),"Mz_kNm":float(v[5])})
        residual=[a+b for a,b in zip(applied,rest)]
        max_res=max(abs(x) for x in residual)
        require(max_res<1e-4,"signed six-axis force/moment equilibrium failed "+case+": "+str(residual))
        members=[]
        for tag,m in elem:
            result=ops.eleResponse(tag,"localForce")
            require(result is not None and len(result)==12,
                    "no valid OpenSees local I/J member force response "+m["id"])
            values=[float(v) for v in result]
            require(all(math.isfinite(v) for v in values),
                    "nonfinite signed member forces "+m["id"])
            actions={
                "I":dict(zip(ACT,values[:6])),
                "J":dict(zip(ACT,values[6:]))
            }
            members.append({"id":m["id"],"type":m["type"],"floor":m["floor"],
                            "ni":m["ni"],"nj":m["nj"],
                            "local_I_J":actions,
                            "max_abs_axial_kN":max(abs(values[0]),abs(values[6])),
                            "max_abs_shear_kN":max(abs(values[i]) for i in (1,2,7,8)),
                            "max_abs_bending_kNm":max(abs(values[i]) for i in (4,5,10,11)),
                            "joint_gap_m":m.get("assumed_joint_gaps_m",[])})
        displacements=[]
        for floor in spec["floors"]:
            ids=[n["id"] for n in spec["nodes"] if n["floor"]==floor["id"]]
            xyz=[ops.nodeDisp(tags[k]) for k in ids]
            require(all(len(x)==6 for x in xyz),"missing 6DOF real frame displacement")
            displacements.append({
                "floor":floor["id"],"z_m":floor["z_m"],
                "max_abs_Ux_mm":1000*max(abs(v[0]) for v in xyz),
                "max_abs_Uy_mm":1000*max(abs(v[1]) for v in xyz),
                "max_abs_Uz_mm":1000*max(abs(v[2]) for v in xyz),
                "range_Ux_mm":[1000*min(v[0] for v in xyz),1000*max(v[0] for v in xyz)],
                "range_Uy_mm":[1000*min(v[1] for v in xyz),1000*max(v[1] for v in xyz)],
                "engineering_acceptance":False,
            })
        case_results[case]={
            "case":case,"source":"EXPLICIT_ASSUMED_SOURCE_DERIVED_3D_FRAME_OPENSEES",
            "applied_6axis":dict(zip(DOF,applied)),
            "base_6axis":dict(zip(DOF,rest)),
            "signed_equilibrium_residual":dict(zip(DOF,residual)),
            "max_6axis_equilibrium_residual":max_res,
            "base_support_reactions":supports,
            "floor_displacements":displacements,
            "signed_local_member_forces":members,
            "member_results_count":len(members),
            "engineering_approval":False,
        }
    ops.wipe()
    result={
        "schema":"jp.structural.r6p26.narayani_independent_frame_results.v0.1",
        "project_id":spec["project_id"],
        "model_source_digest":digest(spec),
        "geometry_source_cad_commit":CAD_SHA,
        "classification":"UNVERIFIED_NARAYANI_FRAME_WITH_REAL_DXF_GF_COORDINATES_AND_ASSUMED_JOINTS",
        "report_basis":spec["report_basis"],
        "report_source":spec["authoritative_source_report"],
        "source_area_and_load_ledger":ledger,
        "gravity_conditions":{"DL_kN":ledger["DL_total_kN"],
                              "LL_kN":ledger["LL_total_kN"],
                              "wall_load_included":False,
                              "slab_shells_modeled":False},
        "model_counts":{
            "source_GF_columns":23,
            "provisionally_extended_column_segments":69,
            "source_candidate_beam_edges":spec["source_candidate_beams"],
            "model_accepted_beam_link_hypotheses":spec["beam_members_modeled"],
            "discarded_or_duplicate_beam_candidate_edges":len(spec["mapping_audit"]),
            "physical_source_footing_outlines":21,
            "fully_verified_beam_column_connections":0,
            "actual_NBC105_seismic_design_cases":0,
            "independent_3D_elastic_frame_scenarios":len(CASE_NAMES),
        },
        "candidate_mapping_audit":spec["mapping_audit"],
        "source_members":spec["members"],
        "source_nodes":spec["nodes"],
        "floors":spec["floors"],
        "cases":case_results,
        "holds":spec["holds"],
        "member_design_checked":False,
        "seismic_code_design_performed":False,
        "real_shell_FE_solved":False,
        "professional_engineering_approval":False,
        "construction_release":False,
        "original_F3_unsafe_status_retained":True,
    }
    return result
