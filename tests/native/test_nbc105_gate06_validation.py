"""Gate06 source equation tests. Inputs are synthetic and public-safe."""
import math
import pytest
from jp_structural.solvers.native.nbc105_gate06_validation import (
    Gate06InputError,effective_EI_ratios,signed_eccentric_floor_wrenches,
    reconcile_trial_seismic_weight,governing_signed_component,
)
@pytest.mark.parametrize("state,beam,col",[("GROSS",1,1),("ULS",.35,.70),("SLS",.70,.90)])
def test_nbc105_effective_stiffness_table_3_1(state,beam,col):
    out=effective_EI_ratios(limit_state=state)
    assert out["beam_flexural_EI_over_EcIg"]==beam
    assert out["column_flexural_EI_over_EcIg"]==col
    assert out["axial_EA_ratio"]==1.
    assert out["beam_torsional_GJ_ratio"]==1.
    assert not out["engineering_approval"]

def test_compatibility_torsion_is_not_assumed_from_a_member_label():
    with pytest.raises(Gate06InputError,match="compatibility"):
        effective_EI_ratios(limit_state="ULS",include_torsion_reduction=True)
    r=effective_EI_ratios(limit_state="ULS",include_torsion_reduction=True,
                          beam_torsion_is_compatibility=True)
    assert r["beam_torsional_GJ_ratio"]==.1

@pytest.mark.parametrize("axis,breadth,loadsign,eccsign,expected_Fx,expected_Fy,expected_Mz",[
    ("X",12.,1,1,100.,0.,-60.),
    ("X",12.,1,-1,100.,0.,60.),
    ("X",12.,-1,1,-100.,0.,60.),
    ("X",12.,-1,-1,-100.,0.,-60.),
    ("Y",20.,1,1,0.,100.,100.),
    ("Y",20.,1,-1,0.,100.,-100.),
    ("Y",20.,-1,1,0.,-100.,-100.),
    ("Y",20.,-1,-1,0.,-100.,100.),
])
def test_all_signed_accidental_eccentricity_combinations(axis,breadth,loadsign,eccsign,
         expected_Fx,expected_Fy,expected_Mz):
    out=signed_eccentric_floor_wrenches(floor_forces_kN=[40,60],
         axis=axis,orthogonal_plan_breadth_m=breadth,
         load_direction_sign=loadsign,eccentricity_sign=eccsign)
    assert out["sum_signed_Fx_kN"]==pytest.approx(expected_Fx)
    assert out["sum_signed_Fy_kN"]==pytest.approx(expected_Fy)
    assert out["sum_signed_applied_Mz_kNm"]==pytest.approx(expected_Mz)
    assert not out["verified_rigid_diaphragm"]
    assert not out["engineering_approval"]

@pytest.mark.parametrize("bad",[
    {"floor_forces_kN":[]},{"floor_forces_kN":[-1,2]},
    {"eccentricity_sign":0},{"eccentricity_sign":True},
    {"load_direction_sign":0},{"axis":"Z"},
    {"orthogonal_plan_breadth_m":0},
])
def test_invalid_accidental_earthquake_wrench_is_rejected(bad):
    kw=dict(floor_forces_kN=[40,60],axis="X",orthogonal_plan_breadth_m=12.,
            eccentricity_sign=1,load_direction_sign=1)
    kw.update(bad)
    with pytest.raises(Gate06InputError):
        signed_eccentric_floor_wrenches(**kw)

def test_seismic_weight_shortfall_is_explicit_not_imputed_as_walls():
    m=reconcile_trial_seismic_weight(source_W_kN=1000.,
      member_dead_kN=250,floor_extra_dead_kN=350,nonroof_live_kN=100,
      roof_live_kN=35)
    assert m["reconstructed_trial_W_kN"]==pytest.approx(630)
    assert m["residual_source_minus_trial_kN"]==pytest.approx(370)
    assert m["roof_live_factor"]==0
    assert m["source_to_trial_mass_closed"] is False
    assert m["missing_components_inferred"] is False

def test_negative_mass_gap_is_not_turned_into_fake_closure():
    m=reconcile_trial_seismic_weight(source_W_kN=100,
       member_dead_kN=150,floor_extra_dead_kN=0,nonroof_live_kN=0)
    assert m["residual_source_minus_trial_kN"]==-50
    assert not m["source_to_trial_mass_closed"]

@pytest.mark.parametrize("factor",[.1,-.3,float("nan"),.5,True])
def test_unsupported_mass_live_fraction_fails(factor):
    with pytest.raises(Gate06InputError):
        reconcile_trial_seismic_weight(source_W_kN=100,
          member_dead_kN=50,floor_extra_dead_kN=0,
          nonroof_live_kN=30,live_factor_nonroof=factor)

def _row(case,Ni,Myi):
    v={x:0 for x in ("Ni","Vyi","Vzi","Ti","Myi","Mzi",
        "Nj","Vyj","Vzj","Tj","Myj","Mzj")}
    v["Ni"]=Ni;v["Myi"]=Myi
    return {"combination_id":case,"signed_local_end_forces":v}

def test_signed_member_governing_moment_keeps_concurrent_axial_force_from_one_case():
    rows=[_row("U_A",120,40),_row("U_B",-60,-90),_row("U_C",200,55)]
    r=governing_signed_component(member_id="SYNTH_COL_001",component="Myi",
         combination_actions=rows)
    assert r["combination_id"]=="U_B"
    assert r["signed_governing_value"]==-90
    assert r["same_case_signed_12_component_vector"]["Ni"]==-60
    assert r["do_not_combine_independent_case_peaks"]
    assert not r["engineering_approval"]

def test_signed_member_governing_axial_can_be_different_case_without_assembling_new_vector():
    rows=[_row("A",120,40),_row("B",-60,-90),_row("C",200,55)]
    r=governing_signed_component(member_id="SYNTH_COL_001",component="Ni",
         combination_actions=rows)
    assert r["combination_id"]=="C"
    assert r["same_case_signed_12_component_vector"]["Myi"]==55

def test_signed_member_envelope_requires_12_components_and_unique_case_ids():
    with pytest.raises(Gate06InputError):
        governing_signed_component(member_id="SYNTH",component="Myi",
           combination_actions=[{"combination_id":"A","signed_local_end_forces":{"Myi":20}}])
    with pytest.raises(Gate06InputError):
        governing_signed_component(member_id="SYNTH",component="Myi",
           combination_actions=[_row("A",1,2),_row("A",2,3)])

def test_governing_member_rejects_nan():
    r=_row("U_TEST",10,float("nan"))
    with pytest.raises(Gate06InputError):
        governing_signed_component(member_id="SYNTH",component="Myi",
           combination_actions=[r])
