"""R6.13 source member ledger boundaries; computed research is not design safety."""
import math
import pytest
from scripts.build_r6p13_member_gravity_research import action_metrics,source_load_summary,build
from scripts.build_r6p8_native_source_catalogue import build as native_source

def test_exact_local_force_order_metrics_and_negative_signs():
    x=action_metrics([-10,2,-3,.7,14,-15,10,-4,5,-1,-11,13])
    a=x["signed_local_end_actions"]
    assert a["Ni_kN"]==-10 and a["Mzj_kNm"]==13
    assert x["max_abs_component_of_end_actions"]=={
      "axial_kN":10,"shear_kN":5,"bending_kNm":15,"torsion_kNm":1}
    assert not x["engineering_member_design_accepted"]
    for vector in ([0]*11,[0]*13,[0]*11+[float("nan")],[0]*11+[float("inf")]):
        with pytest.raises(ValueError):
            action_metrics(vector)

def test_actual_governing_source_b46_wall_which_is_not_a_design_moment():
    native=native_source()
    assert len(native["members"])==199 and len(native["shells"])==115
    b46=next(m for m in native["members"] if m["key"]=="GF:B46")
    w=source_load_summary(b46)
    assert math.isclose(w["source_member_wall_resultant_kN"],44.61275,abs_tol=1.e-5)
    assert w["simple_span_wall_only_counterfactual"] is not None
    assert w["simple_span_wall_only_counterfactual"]["not_a_source_frame_end_action"]
    assert b46["length_mm"]==4823
    assert "GF:B19" not in {m["key"] for m in native["members"]}

def test_full_casebook_member_join_and_12_shell_hold():
    x=build()
    assert x["count"]["actual_structural_frame_members"]==165
    assert x["count"]["unsectioned_line_source_records"]==34
    assert x["count"]["source_shell_objects"]==115
    assert x["count"]["research_shells_included"]==103
    assert x["count"]["research_shells_excluded"]==12
    assert sum(not s["included_in_103_shell_research_trial"] for s in x["shells"])==12
    assert sum(s["included_in_103_shell_research_trial"] for s in x["shells"])==103
    assert len({m["key"] for m in x["members"]})==165
    b46=next(m for m in x["members"] if m["key"]=="GF:B46")
    assert math.isclose(b46["source_loading"]["source_member_wall_resultant_kN"],44.61275,abs_tol=1.e-5)
    assert len(b46["trial_actions_by_source_stiffness"])==2
    for member in x["members"]:
        assert member["capacity_verification"]=="NOT_PERFORMED"
        assert member["unverified_as_built_rebar"]
        for role in ("ULS","SLS"):
            data=member["trial_actions_by_source_stiffness"][role]
            assert len(data["raw_gravity_case_trial"])==4
            assert len(data["three_original_gravity_combo_research_trials"])==3
            assert data["member_capacity_or_safety"]=="NOT_DETERMINED"
            for values in data["raw_gravity_case_trial"].values():
                assert len(values["signed_local_end_actions"])==12
                assert all(math.isfinite(z) for z in values["signed_local_end_actions"].values())
                assert not values["original_ETABS21_solved_end_actions"]
    assert x["twelve_unsupported_shells_excluded"]
    assert x["F3_one_way_shear_unsafe"]
    assert not x["engineering_approval"]
    assert not x["original_ETABS21_native_mesh_or_reactions_reproduced"]
    assert not x["research_member_strength_or_capacity_accepted"]
