"""Gate16: source-conflict evidence and third real ShellMITC4 mesh density."""
import json
import math
from pathlib import Path
from scripts.run_g15_gate16_three_mesh import build_plan, mesh_for, MODES, solve

ROOT=Path(__file__).resolve().parents[1]

def test_source_review_preserves_terrace_density_occupancy_conflicts():
    d=json.loads((ROOT/"registry/g15-gate16-drawing-mass-review.v0.1.json").read_text())
    assert d["source_pdf_sha256"]=="f122904444a2e2f75230d9d4e41da0093d050da25c6e8140c86d466b7e37cc52"
    assert d["review"]["second_floor_terrace_label_visually_present"] is True
    assert d["review"]["ground_drawing_occupancy_label"]=="COMMERCIAL SPACE"
    assert d["review"]["full_slab_polygons_source_verified"] is False
    assert d["review"]["actual_slab_voids_source_verified"] is False
    assert d["review"]["source_report_etabs_area_object_polygons_found"] is False
    assert d["concrete_unit_weight_conflict"]["summary_kN_m3"]==20
    assert d["concrete_unit_weight_conflict"]["table_rc_kN_m3"]==25
    assert d["concrete_unit_weight_conflict"]["resolved"] is False
    assert d["engineering_approval"] is False

def test_actual_8x8_mesh_geometry_and_boundary():
    original,study,xy,*_=build_plan()
    expected=[(2,4,6,5),(4,16,22,13),(8,64,78,29),(4,12,21,13)]
    for mode,(n,quads,extra,boundary) in zip(MODES,expected):
        m=mesh_for(mode,xy)
        assert m["n"]==n
        assert len(m["quads"])==quads
        assert len(m["extra"])==extra
        assert len(m["boundary"])==boundary
        assert math.isclose(m["active_area_per_level_m2"],17.874*(.75 if m["opening"] else 1),abs_tol=1e-8)

def test_real_FE_four_modes_36_equilibrated_cases_identical_full_panel_mass():
    d=solve(summary_only=True)
    assert d["schema"]=="jp.structural.g15.gate16.third_resolution_source_mass_review.v0.1"
    assert len(d["cases"])==36 and len(d["comparisons"])==9
    assert [x["element_count_two_levels"] for x in d["models"]]==[8,32,128,24]
    assert all(c["force_and_moment_equilibrium_pass"] is True and
               c["force_equilibrium_error_kN"]<.001 and
               c["moment_equilibrium_error_kNm"]<.001 for c in d["cases"])
    for mode,beams,shells in zip(MODES,[177,193,225,193],[8,32,128,24]):
        group=[x for x in d["cases"] if x["mode"]==mode]
        assert len(group)==9
        assert all(x["frame_local_signed_action_count"]==beams and
                   x["shell_mitc4_elements"]==shells for x in group)
    for case in {x["case"] for x in d["cases"]}:
        group=[x for x in d["cases"] if x["case"]==case]
        weights=[x["conditional_seismic_floor_weights_kN"] for x in group]
        assert weights[0]==weights[1]==weights[2]
        assert math.isclose(weights[0][0]-weights[3][0],22.923405,abs_tol=1e-7)
        assert math.isclose(weights[0][1]-weights[3][1],22.923405,abs_tol=1e-7)
    assert d["source_concrete_unit_weight_conflict_unresolved"] is True
    assert d["concrete_density_conflict_not_recalibrated_into_solver"] is True
    assert d["source_full_slab_and_terrace_boundaries_verified"] is False
    assert d["mesh_convergence_accepted"] is False
    assert d["mass_source_reconciled"] is False
    assert d["F3_one_way_shear"]=="NOT SAFE IN ONE WAY SHEAR"
    assert d["engineering_approval"] is False

def test_all_36_cases_have_same_physical_tracked_member_action():
    d=solve(summary_only=False)
    for c in d["cases"]:
        f=c["full_frame_local_signed_actions"]
        assert len(f)==c["frame_local_signed_action_count"]
        match=[q for q in f if q["id"]=="COL-F1-L0-1"]
        assert len(match)==1
        assert math.isclose(match[0]["signed"][5],c["tracked_same_member_signed_Mzi_kNm"],abs_tol=1e-9)
        assert all(len(q["signed"])==12 and all(math.isfinite(v) for v in q["signed"]) for q in f)
    assert all(q["common_full_bay_mass_and_loading"] is True and
               q["mesh_convergence_accepted"] is False for q in d["comparisons"])
