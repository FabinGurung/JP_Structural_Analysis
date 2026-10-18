"""Reference arithmetic and unsafe examples for bounded RC engines."""
import math
import pytest
from jp_structural.solvers.native.rc_report_kernels import (
    RCDesignError,nbc_capacity_design_beam_shear,is456_biaxial_column,
    nbc_joint_shear,is456_centered_isolated_footing,
)
def test_capacity_design_shear_is_larger_than_fe_when_applicable():
    r=nbc_capacity_design_beam_shear(span_mm=6000,gravity_shear_a_kN=65,
        gravity_shear_b_kN=60,analysis_shear_a_kN=100,analysis_shear_b_kN=95,
        sway_right_moment_a_kNm=105,sway_right_moment_b_kNm=95,
        sway_left_moment_a_kNm=100,sway_left_moment_b_kNm=90,
        moment_capacity_source_id="SYNTHETIC")
    assert r["end_demands"][0]["required_shear_kN"]==pytest.approx(65+1.4*200/6)
    assert r["end_demands"][1]["required_shear_kN"]==pytest.approx(60+1.4*200/6)
    assert not r["engineering_approval"]
    with pytest.raises(RCDesignError):
        nbc_capacity_design_beam_shear(span_mm=0,gravity_shear_a_kN=65,
        gravity_shear_b_kN=60,analysis_shear_a_kN=100,analysis_shear_b_kN=95,
        sway_right_moment_a_kNm=105,sway_right_moment_b_kNm=95,
        sway_left_moment_a_kNm=100,sway_left_moment_b_kNm=90,
        moment_capacity_source_id="SYNTHETIC")
def test_iit_worked_biaxial_column_and_negative_cases():
    inputs=dict(width_mm=400,depth_mm=500,fck_MPa=25,fy_MPa=415,
        Ast_mm2=5538,Pu_kN=1475,Mux_kNm=252,Muy_kNm=29.5,
        Mux1_kNm=272,Muy1_kNm=340,clear_height_mm=2500,
        effective_length_x_mm=2500,effective_length_y_mm=2500,
        uniaxial_capacity_source_id="IITGN-EQ06-SP16-P23")
    r=is456_biaxial_column(**inputs)
    Puz=(.45*25*(200000-5538)+.75*415*5538)/1000
    alpha=1+(1475/Puz-.2)/.6
    assert r["Puz_kN"]==pytest.approx(Puz)
    assert r["alpha_n"]==pytest.approx(alpha)
    assert r["interaction_utilization"]==pytest.approx((252/272)**alpha+(29.5/340)**alpha)
    assert r["status"].startswith("BOUNDED_")
    assert is456_biaxial_column(**(inputs|{"Mux_kNm":500}))["status"]=="FAIL"
    assert is456_biaxial_column(**(inputs|{"effective_length_x_mm":7000}))["status"]=="FAIL"
def test_nbc_joint_coefficients_equilibrium_and_deficit():
    inputs=dict(confinement_faces="THREE",framing="INTERIOR",
        fck_MPa=25,fy_MPa=415,joint_breadth_mm=400,joint_width_mm=400,
        Ast_top_mm2=804,Ast_bottom_mm2=603,column_shear_kN=100,
        joint_geometry_source_id="SYNTHETIC")
    r=nbc_joint_shear(**inputs)
    assert r["nominal_Vjc_kN"]==pytest.approx(1.2*400*400*5/1000)
    assert r["factored_Vjh_kN"]==pytest.approx(1.25*415*(804+603)/1000-100)
    assert r["joint_nominal_shear_pass"]
    bad=nbc_joint_shear(**(inputs|{"Ast_top_mm2":2600,"Ast_bottom_mm2":2500}))
    assert not bad["joint_nominal_shear_pass"]
    assert bad["additional_Ajh_mm2"]>0
    assert not bad["engineering_approval"]
def test_foundation_actual_equations_and_unsafe_example():
    x=dict(B_mm=2100,L_mm=2100,D_mm=450,d_x_mm=392,d_y_mm=392,
        column_b_mm=400,column_l_mm=400,fck_MPa=25,fy_MPa=415,
        Ast_x_mm2_per_m=1000,Ast_y_mm2_per_m=1000,
        P_service_kN=571,P_ultimate_kN=856.5,allowable_soil_kPa=160,
        soil_assumption_source_id="ASSUMED_160kPa_NOT_TESTED")
    r=is456_centered_isolated_footing(**x)
    qu=856.5/(2.1*2.1)
    assert r["service_pressure_kPa"]==pytest.approx(571/4.41)
    assert r["axis_checks"][0]["M_ultimate_kNm_per_m"]==pytest.approx(qu*.85**2/2)
    assert r["axis_checks"][0]["V_oneway_kN_per_m"]==pytest.approx(qu*(.85-.392))
    b0=2*(.4+.392+.4+.392)*1000
    assert r["punch_tau_v_MPa"]==pytest.approx(qu*(4.41-(.4+.392)**2)*1000/(b0*392))
    assert r["status"].startswith("BOUNDED_")
    assert not r["engineering_approval"]
    weak=is456_centered_isolated_footing(**(x|{"D_mm":250,"d_x_mm":180,"d_y_mm":180,"Ast_x_mm2_per_m":350,"Ast_y_mm2_per_m":350}))
    assert weak["status"]=="FAIL"
    with pytest.raises(RCDesignError,match="evidence"):
        is456_centered_isolated_footing(**(x|{"soil_assumption_source_id":""}))
