import copy
import math
import pytest
from jp_structural.solvers.native.nbc105_2025_actions import (
    NBCActionError, SOURCE_URL, live_seismic_weight_factor, apply_verified_live_factors,
    rc_frame_design_period, esm_plateau_shape_factor, rc_mrf_esm_design_coefficients,
    period_vertical_distribution_exponent, seismic_story_forces,
    accidental_torsion_pairs, check_design_interstory_drift, mrsm_base_shear_scaling
)
from jp_structural.solvers.native.load_mass_assembly import allocate_loads_to_nodes

BASIS={"calculation_scope":"NEW_ENGINEERED_ANALYSIS",
       "code_set":{"NBC 105":"2025","NBC 206":"2024"},
       "source_references":{"NBC 105":SOURCE_URL,
                            "NBC 206":"https://ebps.kathmandu.gov.np/UploadFiles/NBC206Amended.pdf"},
       "registered_code_clauses":[]}

def test_nbc2025_live_category_factors_table_5_1():
    assert live_seismic_weight_factor("DEAD")["participation_factor"]==1
    assert live_seismic_weight_factor("STORAGE_LIVE")["participation_factor"]==.6
    assert live_seismic_weight_factor("OTHER_LIVE")["participation_factor"]==.3
    assert live_seismic_weight_factor("ROOF_LIVE")["participation_factor"]==0
    with pytest.raises(NBCActionError):
        live_seismic_weight_factor("generic")

def test_nbc_period_soil_esm_constant_branch_and_current_clauses():
    p=rc_frame_design_period(9.144, 0.55)
    assert p["empirical_period_s"]==pytest.approx(.075*9.144**.75)
    assert p["adopted_design_period_s"]==pytest.approx(1.25*.075*9.144**.75)
    s=esm_plateau_shape_factor("D", p["adopted_design_period_s"])
    assert s["spectral_shape_Ch"]==2.25
    c=rc_mrf_esm_design_coefficients(s["spectral_shape_Ch"], .35, 1.)
    assert c["C_elastic"]==pytest.approx(.7875)
    assert c["Cd_uls"]==pytest.approx(.13125)
    assert c["Cd_sls"]==pytest.approx(.126)
    assert period_vertical_distribution_exponent(.612)==pytest.approx(1.056)
    assert period_vertical_distribution_exponent(3)==2
    with pytest.raises(NBCActionError):
        esm_plateau_shape_factor("D",2.001)

def test_nbc_mass_source_to_esm_and_force_conservation():
    nodes=[
        {"node_id":"a","storey_id":"F1","x_m":0,"y_m":0,"z_m":3},
        {"node_id":"b","storey_id":"F2","x_m":0,"y_m":0,"z_m":6}
    ]
    raw=[
        {"id":"d1","source_key":"wall:1:DL","load_category":"DEAD","downward_load_kN":100,
         "node_shares":[{"node_id":"a","fraction":1}]},
        {"id":"d2","source_key":"slab:2:DL","load_category":"DEAD","downward_load_kN":200,
         "node_shares":[{"node_id":"b","fraction":1}]},
        {"id":"l2","source_key":"slab:2:LL","load_category":"OTHER_LIVE","downward_load_kN":50,
         "node_shares":[{"node_id":"b","fraction":1}]},
    ]
    enriched=apply_verified_live_factors(raw,BASIS)
    assert enriched[-1]["participation_factor"]==.3
    a=allocate_loads_to_nodes(nodes,enriched,9.81)
    assert a["total_seismic_weight_kN"]==pytest.approx(315)
    forces=seismic_story_forces(a,{"F1":3,"F2":6},.1,.612)
    assert forces["base_shear_kN"]==pytest.approx(31.5)
    assert sum(x["lateral_force"] for x in forces["levels"])==pytest.approx(31.5)
    assert len(forces["levels"])==2
    assert all(x["distribution_fraction"]>0 for x in forces["levels"])

def test_eccentricity_action_and_mrsm_scaling_excludes_displacements():
    moment=accidental_torsion_pairs(100,20)
    assert moment["eccentricity_m"]==1
    assert moment["torques_kNm"]==[-100,100]
    s=mrsm_base_shear_scaling(100,80)
    assert s["member_force_factor"]==pytest.approx(1.25)
    assert s["displacement_factor"]==1
    assert s["drift_factor"]==1
    assert mrsm_base_shear_scaling(80,100)["member_force_factor"]==1

def test_current_drift_limit_on_design_not_raw_displacement():
    assert check_design_interstory_drift(.060,3,"ULS",design_displacement_verified=True)["result"]=="PASS"
    assert check_design_interstory_drift(.080,3,"ULS",design_displacement_verified=True)["result"]=="FAIL"
    assert check_design_interstory_drift(.015,3,"SLS",design_displacement_verified=True)["result"]=="PASS"
    assert check_design_interstory_drift(.020,3,"SLS",design_displacement_verified=True)["result"]=="FAIL"
    with pytest.raises(NBCActionError):
        check_design_interstory_drift(.015,3,"SLS",design_displacement_verified=False)

@pytest.mark.parametrize("invalid",[
    lambda x:x["code_set"].update({"NBC 105":"2020"}),
    lambda x:x["code_set"].update({"NBC 205":"2024"}),
    lambda x:x["source_references"].update({"NBC 105":"https://somewhere.example/2025"}),
])
def test_code_basis_fail_closed(invalid):
    b=copy.deepcopy(BASIS);invalid(b)
    with pytest.raises(NBCActionError):
        apply_verified_live_factors([{"load_category":"OTHER_LIVE"}],b)

def test_factor_conflicts_fail_closed():
    with pytest.raises(NBCActionError):
        apply_verified_live_factors([{"load_category":"ROOF_LIVE","participation_factor":.3}],BASIS)
    with pytest.raises(NBCActionError):
        seismic_story_forces({"schema":"unverified"}, {"F1":3}, .1,1)
    with pytest.raises(NBCActionError):
        mrsm_base_shear_scaling(100,0)


def test_full_spectral_shape_branches_and_methods():
    from jp_structural.solvers.native.nbc105_2025_actions import spectral_shape_factor
    def ch(t,method):
        return spectral_shape_factor("D",t,method=method)["spectral_shape_Ch"]
    assert ch(.1,"ESM")==pytest.approx(2.25)
    assert ch(.1,"MRSM")==pytest.approx(1+(2.25-1)*(.1/.5))
    assert ch(.5,"MRSM")==pytest.approx(2.25)
    assert ch(2,"MRSM")==pytest.approx(2.25)
    assert ch(3,"MRSM")==pytest.approx(2.25*2/3)
    assert ch(5,"MRSM")==pytest.approx(2.25*2/5)
    assert ch(6,"MRSM")==pytest.approx(2.25*2*5/36)
    assert ch(5,"ESM")==pytest.approx(ch(5,"MRSM"))
    assert ch(3,"ESM")==pytest.approx(ch(3,"MRSM"))
    with pytest.raises(NBCActionError): spectral_shape_factor("D",6.1,method="MRSM")
    with pytest.raises(NBCActionError): spectral_shape_factor("D",.5,method="UNKNOWN")
    with pytest.raises(NBCActionError): spectral_shape_factor("E",1,method="ESM")

def test_verified_current_cracked_flexural_modifiers():
    from jp_structural.solvers.native.nbc105_2025_actions import effective_cracked_flexural_stiffness_factor
    f=effective_cracked_flexural_stiffness_factor
    assert f("BEAM","ULS")["gross_flexural_stiffness_multiplier"]==.35
    assert f("BEAM","SLS")["gross_flexural_stiffness_multiplier"]==.70
    assert f("COLUMN","ULS")["gross_flexural_stiffness_multiplier"]==.70
    assert f("COLUMN","SLS")["gross_flexural_stiffness_multiplier"]==.90
    with pytest.raises(NBCActionError):f("MASS","ULS")

def test_verified_current_mass_and_frequency_limits():
    from jp_structural.solvers.native.nbc105_2025_actions import modal_mass_coverage_gate
    f=modal_mass_coverage_gate
    modes=[{"mode_id":"1","frequency_hz":2.,"effective_mass_fraction":.60},
           {"mode_id":"2","frequency_hz":4.,"effective_mass_fraction":.35}]
    assert f(modes)["status"]=="PASS_BOUNDED"
    assert f(modes[:1])["status"]=="HOLD_MASS_OR_FREQ_CORRECTION"
    high=[{"mode_id":"1","frequency_hz":2.,"effective_mass_fraction":.92},
          {"mode_id":"99","frequency_hz":34.,"effective_mass_fraction":.02}]
    assert f(high)["status"]=="HOLD_MASS_OR_FREQ_CORRECTION"
    assert f(high,missing_mass_correction_evidence_id="MODEL-MISSING-MASS-001")["status"]=="PASS_BOUNDED"
    assert check_design_interstory_drift(0,3,"ULS",design_displacement_verified=True)["result"]=="PASS"
