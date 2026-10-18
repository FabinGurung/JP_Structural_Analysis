import math
import pytest
from jp_structural.solvers.native.rc_detailing_checks import (
    RCPrecheckInputError,beam_geometry_precheck,beam_min_longitudinal_precheck,
    column_geometry_precheck,column_longitudinal_steel_precheck,
    column_beam_moment_capacity_precheck,fail_closed_design_summary
)

def test_beam_mandatory_geometry_and_nonmandatory_preference():
    assert beam_geometry_precheck(230,400,3200)["status"]=="BOUNDED_PRECHECK_PASS"
    narrow=beam_geometry_precheck(190,400,3200)
    assert narrow["status"]=="FAIL"
    # b/d >0.3 is described as preferable, so must not fail the mandatory gate
    advisory=beam_geometry_precheck(200,900,3600)
    assert advisory["status"]=="BOUNDED_PRECHECK_PASS"
    assert advisory["advisories"]["preferred_width_to_depth_gt_0_3"] is False

def test_beam_longitudinal_minimum():
    assert beam_min_longitudinal_precheck([12,12],[16,16])["status"]=="BOUNDED_PRECHECK_PASS"
    assert beam_min_longitudinal_precheck([12,10],[12,12])["status"]=="FAIL"

def test_column_dimensions_and_bar_count_rho():
    assert column_geometry_precheck(400,16,400)["status"]=="BOUNDED_PRECHECK_PASS"
    assert column_geometry_precheck(300,20,300)["status"]=="FAIL"
    c=column_longitudinal_steel_precheck("RECTANGULAR",400*400,[16]*8)
    assert c["status"]=="BOUNDED_PRECHECK_PASS"
    assert .01 < c["provided_rho"] < .04
    assert column_longitudinal_steel_precheck("RECTANGULAR",400*400,[12]*8)["status"]=="FAIL"
    circ=column_longitudinal_steel_precheck("CIRCULAR",math.pi*350*350/4,[16]*6)
    assert circ["status"]=="BOUNDED_PRECHECK_PASS"

def test_joint_strict_ratio_and_roof_exception():
    assert column_beam_moment_capacity_precheck(121,100,roof_joint=False,
             capacity_inputs_independently_verified=True)["status"]=="BOUNDED_PRECHECK_PASS"
    assert column_beam_moment_capacity_precheck(120,100,roof_joint=False,
             capacity_inputs_independently_verified=True)["status"]=="FAIL"
    assert column_beam_moment_capacity_precheck(0,0,roof_joint=True,
             capacity_inputs_independently_verified=False)["status"]=="NOT_APPLICABLE_ROOF_JOINT"
    with pytest.raises(RCPrecheckInputError):
        column_beam_moment_capacity_precheck(121,100,roof_joint=False,
            capacity_inputs_independently_verified=False)

def test_unsafe_footing_never_overridden_by_adopted_summary():
    # A legacy source says this footing fails shear while its summary adopts it.
    summary=fail_closed_design_summary([
        {"check_id":"F3-one-way-shear","status":"NOT SAFE"},
        {"check_id":"F3-summary-adopted","status":"PASS"}])
    assert summary["status"]=="FAIL"
    assert summary["engineering_approval"] is False
    assert summary["accepted_design"] is False
    assert summary["failed_check_ids"]==["F3-one-way-shear"]

def test_unverified_inputs_fail_closed():
    assert fail_closed_design_summary([
        {"check_id":"unverified-biaxial","status":"HOLD"}])["status"]=="HOLD"
    with pytest.raises(RCPrecheckInputError):
        column_geometry_precheck(400,0,400)
    with pytest.raises(RCPrecheckInputError):
        column_longitudinal_steel_precheck("UNKNOWN",160000,[16]*8)
    with pytest.raises(RCPrecheckInputError):
        fail_closed_design_summary([{"check_id":"x","status":"APPROVED"}])



def test_nbc_beam_max_face_rho_and_bottom_face_ratio_fail_closed():
    from jp_structural.solvers.native.rc_detailing_checks import beam_seismic_rebar_ratios_precheck
    f=beam_seismic_rebar_ratios_precheck
    assert f(width_mm=230,effective_depth_mm=450,top_steel_area_mm2=1000,
             bottom_steel_area_mm2=700,at_column_face=True)["status"]=="BOUNDED_PRECHECK_PASS"
    assert f(width_mm=230,effective_depth_mm=450,top_steel_area_mm2=2800,
             bottom_steel_area_mm2=2000,at_column_face=False)["status"]=="FAIL"
    assert f(width_mm=230,effective_depth_mm=450,top_steel_area_mm2=1200,
             bottom_steel_area_mm2=300,at_column_face=True)["status"]=="FAIL"
    with pytest.raises(RCPrecheckInputError):
        f(width_mm=230,effective_depth_mm=450,top_steel_area_mm2=1200,
          bottom_steel_area_mm2=600,at_column_face="true")


def test_nbc_beam_links_are_not_equivalent_to_ductile_shear_design():
    from jp_structural.solvers.native.rc_detailing_checks import beam_seismic_links_precheck
    args=dict(effective_depth_mm=450,smallest_longitudinal_bar_mm=12,
              link_diameter_mm=8,first_link_from_joint_mm=50,
              end_zone_link_spacing_mm=90,remaining_span_link_spacing_mm=200)
    assert beam_seismic_links_precheck(**args)["status"]=="BOUNDED_PRECHECK_PASS"
    for update in [
        {"link_diameter_mm":6},
        {"first_link_from_joint_mm":51},
        {"end_zone_link_spacing_mm":101},
        {"remaining_span_link_spacing_mm":250},
    ]:
        assert beam_seismic_links_precheck(**(args|update))["status"]=="FAIL"
