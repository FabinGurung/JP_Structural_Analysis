"""Assumption/provenance gates on built RC mathematical reference package."""
import json
from scripts.build_rc_reference_case import build
def test_rc_reference_is_reproducible_and_not_an_actual_building():
    data=build()
    assert data==json.loads(json.dumps(data,allow_nan=False))
    assert data["client_project_result"] is False
    assert data["engineering_approval"] is False
    assert data["historical_unsafe_F3_flag"].startswith("PRESERVED")
    rows=data["results"]
    assert len(rows)==4
    assert all(x["engineering_approval"] is False for x in rows.values())
    assert rows["M08_capacity_shear"]["end_demands"][0]["required_shear_kN"]>100
    assert rows["M09_biaxial_PMM"]["interaction_utilization"]<1
    assert rows["M10_joint_shear"]["nominal_Vjc_kN"]>rows["M10_joint_shear"]["factored_Vjh_kN"]
    assert rows["M12_isolated_footing"]["status"]=="BOUNDED_NUMERIC_PASS_UNVERIFIED_SITE_HOLD"
