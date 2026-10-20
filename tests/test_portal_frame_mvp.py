"""Public-frame MVP: bounded inputs, actual OpenSees solver equilibrium and HOLDs."""
import copy
import math
import pytest
from scripts.run_portal_frame import SAMPLE, validate, run_opensees, parse_issue

def test_portal_sample_fe_has_signed_actions_and_equilibrium():
    d=run_opensees(SAMPLE)
    assert d["schema"]=="jp.structural.portal.frame.output.v1"
    assert [x["case"] for x in d["cases"]]==["GRAVITY","ESM_PLUS_X","ESM_MINUS_X"]
    assert all(x["equilibrium_verified"] for x in d["cases"])
    assert all(len(x["signed_end_actions"])==9 for x in d["cases"])
    assert all(len(y["signed_local_kN_kNm"])==6 for x in d["cases"] for y in x["signed_end_actions"])
    assert math.isclose(d["esm"]["base_shear_kN"],157.5)
    assert d["cases"][0]["support_reaction_y_kN"]==pytest.approx(1200,abs=1e-5)
    assert d["cases"][1]["support_reaction_x_kN"]==pytest.approx(-157.5,abs=1e-5)
    assert d["cases"][2]["support_reaction_x_kN"]==pytest.approx(157.5,abs=1e-5)
    assert not d["engineering_approval"] and not d["actual_g15_project_model"]

def test_planar_frame_sign_reversal_changes_displacement_sign():
    d=run_opensees(SAMPLE)
    p=d["cases"][1]["floor_displacements_m"][-1]
    n=d["cases"][2]["floor_displacements_m"][-1]
    assert p>0 and n<0
    assert p==pytest.approx(-n,rel=1e-7)

@pytest.mark.parametrize("name,value",[
    ("span_m",0),("beam_EI_factor",0),("column_EI_factor",2),
    ("period_s",float("nan")),("Ec_MPa",float("inf")),("span_m",True),
])
def test_unphysical_public_inputs_rejected(name,value):
    data=dict(SAMPLE);data[name]=value
    with pytest.raises(ValueError):
        validate(data)

def test_unknown_and_private_fields_are_rejected():
    data=dict(SAMPLE);data["client_name"]="confidential"
    with pytest.raises(ValueError,match="approved numeric fields"):
        validate(data)

def test_wrong_floor_lengths_rejected():
    data=dict(SAMPLE);data["floor_weights_kN"]=[300,300]
    with pytest.raises(ValueError,match="three"):
        validate(data)

def test_refuse_non_synthetic_case():
    data=dict(SAMPLE);data["model"]="ACTUAL_BUILDING"
    with pytest.raises(ValueError,match="non-synthetic"):
        validate(data)

def test_owner_only_issue_request(tmp_path):
    jsondata=dict(SAMPLE)
    event={"issue":{"title":"[JP Frame MVP] test","user":{"login":"FabinGurung"},
                    "body":"JP_FRAME_RUN_V1\n"+__import__("json").dumps(jsondata)+"\n"}}
    fp=tmp_path/"event.json";fp.write_text(__import__("json").dumps(event))
    assert parse_issue(fp)==validate(SAMPLE)
    event["issue"]["user"]["login"]="unauthorized"
    fp.write_text(__import__("json").dumps(event))
    with pytest.raises(ValueError,match="authorized"):
        parse_issue(fp)
