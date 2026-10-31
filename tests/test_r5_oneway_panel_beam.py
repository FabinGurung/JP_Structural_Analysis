"""R5.4 source-declared one-way rectangular slab panel-to-beam load QA."""
import copy
import csv
import hashlib
import json
from pathlib import Path

import pytest
from jp_structural.solvers.native.one_way_panel_to_beams import (
    PanelRoutingError,transfer_one_way_panels
)
from scripts.build_r5_oneway_panel_beam_case import DEFAULT,ROUTES,PFX,build,emit
from scripts.build_r5_uniform_beam_case import build as old_build

@pytest.fixture(scope="module")
def spec():
    return json.loads(DEFAULT.read_text(encoding="utf8"))

@pytest.fixture(scope="module")
def plan():
    return json.loads(ROUTES.read_text(encoding="utf8"))

@pytest.fixture(scope="module")
def result(spec,plan):
    return build(spec,plan)

def transfer(s,p):
    return transfer_one_way_panels(model=s["model"],loads=s["source_loads"],
       routes=p["routes"],gravity_m_s2=s["gravity_m_s2"])

def test_panel_beam_handoff_matches_independent_simply_supported_one_way_tributary_arithmetic(spec,plan,result):
    x=transfer(spec,plan)
    assert x["panel_source_count"]==2 and x["panel_route_count"]==2
    assert x["panel_edge_element_load_count"]==4
    assert x["source_wall_element_count"]==1
    assert x["source_total_gravity_kN"]==pytest.approx(128)
    assert x["source_seismic_weight_kN"]==pytest.approx(111.2)
    assert x["total_native_element_gravity_kN"]==pytest.approx(128)
    routes={x["panel_source_id"]:x for x in result["source_panel_routes"]}
    dead=routes["ROOF-FINISH-DL"]
    live=routes["ROOF-LIVE-LL"]
    assert dead["source_panel_area_m2"]==pytest.approx(12.)
    assert dead["support_spacing_m"]==pytest.approx(3.)
    assert dead["loaded_beam_length_m"]==pytest.approx(4.)
    assert dead["source_total_kN"]==pytest.approx(72.)
    assert live["source_total_kN"]==pytest.approx(24.)
    assert [b["member_id"] for b in dead["beam_loads"]]==["BM1","BM3"]
    assert all(b["area_tributary_m2"]==pytest.approx(6.) for b in dead["beam_loads"])
    assert all(b["downward_kN_per_m"]==pytest.approx(6*1.5) for b in dead["beam_loads"])
    assert all(b["downward_resultant_kN"]==pytest.approx(36) for b in dead["beam_loads"])
    assert all(b["downward_kN_per_m"]==pytest.approx(2*1.5) for b in live["beam_loads"])
    assert sum(x["downward_resultant_kN"] for x in result["source_routed_element_loads"]
               if x["case_id"]=="DL")==pytest.approx(104)
    assert sum(x["downward_resultant_kN"] for x in result["source_routed_element_loads"]
               if x["case_id"]=="LL")==pytest.approx(24)
    assert result["source_route_conservation"] and result["source_first_moment_conservation"]

def test_all_native_element_loads_and_mass_same_original_audited_R5_source(spec,plan,result):
    original=old_build(spec)
    assert result["source_mass_SHA256"]==original["mass_assembly_source_sha256"]
    assert result["source_total_gravity_kN"]==original["source_total_gravity_kN"]
    assert result["source_seismic_weight_kN"]==original["source_seismic_weight_kN"]
    assert result["native_element_gravity_kN"]==pytest.approx(128.)
    cases={x["case_id"]:x for x in result["signed_FE"]["raw_cases"]}
    assert len(cases["DL"]["nodal_loads"])==0
    assert len(cases["LL"]["nodal_loads"])==0
    assert len(cases["DL"]["uniform_beam_loads"])==3
    assert len(cases["LL"]["uniform_beam_loads"])==2
    assert len(cases["HX"]["uniform_beam_loads"])==0
    assert {x["member_id"] for x in cases["DL"]["uniform_beam_loads"]}=={"BM1","BM3"}
    assert len({x["source_key"] for x in cases["DL"]["uniform_beam_loads"]})==3
    assert result["edge_member_load_count"]==4
    assert result["independent_wall_load_count"]==1

def test_actual_opensees_3D_signed_cases_and_shear_moment_diagrams(result):
    assert result["signed_end_action_count"]==80
    assert result["frame_member_count"]==8
    assert result["raw_case_count"]==3 and result["combination_count"]==2
    assert result["max_global_force_moment_residual"]<1e-5
    assert all(x["global_equilibrium_pass"] for x in result["signed_FE"]["raw_cases"])
    assert result["source_signed_beam_diagrams"]["diagram_record_count"]==20
    assert result["source_signed_beam_diagrams"]["all_J_cut_boundary_equilibrium_pass"] is True
    assert result["bounded_M08_M09_M10"]["source_action_digest"]==result["signed_input_SHA256"]
    assert len(result["bounded_M08_M09_M10"]["beam_design"])==1
    assert result["bounded_M08_M09_M10"]["engineering_approval"] is False
    raw={x["case_id"]:x for x in result["signed_FE"]["raw_cases"]}
    cmb={x["combination_id"]:x for x in result["signed_FE"]["combinations"]}
    for m in ("BM1","BM3","COL1"):
        for end in ("I","J"):
            for axis in ("N","Vy","Vz","T","My","Mz"):
                dl=raw["DL"]["local_end_resisting_actions"][m][end][axis]
                ll=raw["LL"]["local_end_resisting_actions"][m][end][axis]
                hx=raw["HX"]["local_end_resisting_actions"][m][end][axis]
                assert cmb["U_PLUS"]["local_end_resisting_actions"][m][end][axis]==pytest.approx(1.2*dl+1.5*ll+hx,abs=1e-5)
                assert cmb["U_MINUS"]["local_end_resisting_actions"][m][end][axis]==pytest.approx(1.2*dl+1.5*ll-hx,abs=1e-5)

def test_reference_requires_unique_one_way_routes_and_no_guessing(spec,plan):
    p=copy.deepcopy(plan);p["routes"].pop()
    with pytest.raises(PanelRoutingError,match="all source panel"):
        transfer(spec,p)
    p=copy.deepcopy(plan);p["routes"].append(copy.deepcopy(p["routes"][0]))
    with pytest.raises(PanelRoutingError,match="duplicate/unknown"):
        transfer(spec,p)
    p=copy.deepcopy(plan);p["routes"][0]["panel_source_id"]="EDGE-WALL-DL"
    with pytest.raises(PanelRoutingError,match="duplicate/unknown"):
        transfer(spec,p)
    p=copy.deepcopy(plan);p["routes"][0]["transfer_model"]="TWO_WAY"
    with pytest.raises(PanelRoutingError,match="unverified"):
        transfer(spec,p)

@pytest.mark.parametrize("mutate,error",[
 (lambda p:p["routes"][0].update(span_direction="Z"),"X/Y"),
 (lambda p:p["routes"][0].update(edge_beam_member_ids=["BM1","BM1"]),"two distinct"),
 (lambda p:p["routes"][0].update(edge_beam_member_ids=["BM2","BM4"]),"opposite full panel"),
 (lambda p:p["routes"][0].update(edge_beam_member_ids=["BM3","BM1"]),"opposite full panel"),
 (lambda p:p["routes"][0].update(edge_beam_member_ids=["BM1","COL1"]),"explicit BEAM"),
 (lambda p:p["routes"][0].update(edge_beam_member_ids=["BM1","MISSING"]),"unknown edge"),
 (lambda p:p["routes"][0].update(extra="unsupported"),"route schema"),
])
def test_bad_route_id_orientation_and_member_fails_closed(mutate,error,spec,plan):
    p=copy.deepcopy(plan);mutate(p)
    with pytest.raises(PanelRoutingError,match=error):
        transfer(spec,p)

def test_other_rectangle_dimensions_recompute_trib_width_for_both_span_directions(spec,plan):
    s=copy.deepcopy(spec)
    for n in s["model"]["nodes"]:
        if n["x"]==4:n["x"]=5
    a=transfer(s,plan)
    assert a["source_total_gravity_kN"]==pytest.approx(6*15+2*15+8*5)
    assert a["total_native_element_gravity_kN"]==pytest.approx(160.)
    assert all(x["area_tributary_m2"]==pytest.approx(7.5)
               for p in a["panel_routes"] for x in p["beam_loads"])
    # For X span, beams running in Y direction: BM4 (x=0) and BM2 (x=5).
    p=copy.deepcopy(plan)
    for r in p["routes"]:
        r["span_direction"]="X"
        r["edge_beam_member_ids"]=["BM4","BM2"]
    b=transfer(s,p)
    assert b["source_total_gravity_kN"]==pytest.approx(160.)
    assert all(x["area_tributary_m2"]==pytest.approx(7.5)
               for r in b["panel_routes"] for x in r["beam_loads"])
    assert all(x["downward_kN_per_m"]==pytest.approx(6*2.5)
               for r in b["panel_routes"] if r["panel_source_id"]=="ROOF-FINISH-DL"
               for x in r["beam_loads"])

def test_reject_nonrectangle_or_beam_out_of_panel_geometry(spec,plan):
    s=copy.deepcopy(spec)
    next(n for n in s["model"]["nodes"] if n["id"]=="R3")["x"]=3.5
    with pytest.raises((PanelRoutingError,ValueError),match="rectang|axis-aligned|panel"):
        transfer(s,plan)
    s=copy.deepcopy(spec)
    next(n for n in s["model"]["nodes"] if n["id"]=="R3")["z"]=3.5
    with pytest.raises((PanelRoutingError,ValueError),match="horizontal|coplanar"):
        transfer(s,plan)

def test_original_source_F3_and_7_chapter_report_gates_stay_open(result):
    assert [c["id"] for c in result["chapters"]]==[f"{i:02d}" for i in range(1,8)]
    assert {m["id"] for c in result["chapters"] for m in c["modules"]}=={
       *(f"M{i:02d}" for i in range(1,17)),"S17","S18"}
    assert result["original_F3_failure"]=="NOT SAFE IN ONE WAY SHEAR"
    assert result["original_building_source_verified"] is False
    assert result["engineering_approval"] is False
    assert result["permit_eligible"] is False
    assert result["actual_shell_and_diaphragm_FE"] is False
    assert result["one_way_slab_assumption_not_physically_verified"] is True

def test_versioned_artifacts_are_hashed_and_linked_in_master_report(tmp_path):
    d=emit(DEFAULT,ROUTES,tmp_path)
    m=json.loads((tmp_path/(PFX+"-manifest.json")).read_text())
    assert m["engineering_approval"] is False
    assert set(m["files"])=={PFX+suffix for suffix in (".html",".json","-routes.csv","-member-ends.csv")}
    for name,checksum in m["files"].items():
        assert hashlib.sha256((tmp_path/name).read_bytes()).hexdigest()==checksum
    assert json.loads((tmp_path/(PFX+".json")).read_text())["schema"]==d["schema"]
    assert len(list(csv.DictReader((tmp_path/(PFX+"-routes.csv")).open())))==4
    assert len(list(csv.DictReader((tmp_path/(PFX+"-member-ends.csv")).open())))==80
    site=(Path(__file__).resolve().parents[1]/"site/report.html").read_text()
    assert 'id="annex-r5p4-oneway-slabs"' in site
    assert "reports/r5-oneway-panel-transfer.html" in site
