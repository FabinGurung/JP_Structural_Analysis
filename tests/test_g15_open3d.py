"""Actual source-derived G15 165-member 3D OpenSees numerical regression."""
import math
import pytest
from scripts.run_g15_open_3d import SAMPLE,validate,source,solve

def test_public_geometry_reconstructs_165_3d_members_without_source_pdf():
    d=source()
    assert len(d["column_positions_mm"])==23
    assert len(d["beam_edges"])==32
    assert d["hypothetical_beam_edge_indices"]==[30,31]
    assert 23*3+32*3==165
    assert d["safety"]["engineering_approval"] is False
    assert d["safety"]["F3_footing_one_way_shear"]=="NOT SAFE IN ONE WAY SHEAR"

def test_actual_3d_opensees_solves_signed_gravity_and_orthogonal_cases():
    d=solve(SAMPLE)
    assert d["model_counts"]=={"column_positions":23,"nodes":92,
         "members":165,"column_segments":69,"beam_segments":96}
    assert [x["case"] for x in d["cases"]]==[
       "GRAVITY","EQ_PLUS_X","EQ_MINUS_X","EQ_PLUS_Y","EQ_MINUS_Y"]
    assert all(len(x["member_signed_local_end_forces"])==165 for x in d["cases"])
    assert all(x["equilibrium_residual_kN"]<.001 for x in d["cases"])
    assert all(len(f["signed"])==12 for x in d["cases"]
               for f in x["member_signed_local_end_forces"])
    assert d["cases"][0]["reaction_kN_xyz"][2]==pytest.approx(sum(SAMPLE["floor_weights_kN"]),abs=.001)
    assert d["engineering_approval"] is False
    assert d["diaphragm_included"] is False
    assert d["foundation_F3_one_way_shear"]=="NOT SAFE IN ONE WAY SHEAR"

def test_x_y_reversed_signs_preserve_elastic_equilibrium():
    d=solve(SAMPLE)
    V=d["esm"]["base_shear_kN"]
    assert d["cases"][1]["reaction_kN_xyz"][0]==pytest.approx(-V,abs=.001)
    assert d["cases"][2]["reaction_kN_xyz"][0]==pytest.approx(V,abs=.001)
    assert d["cases"][3]["reaction_kN_xyz"][1]==pytest.approx(-V,abs=.001)
    assert d["cases"][4]["reaction_kN_xyz"][1]==pytest.approx(V,abs=.001)

@pytest.mark.parametrize("field,value",[
  ("beam_width_mm",0),("concrete_E_MPa",999),
  ("C_design",math.inf),("T_seconds",float("nan")),
  ("bridges","true"),("stiffness","PRODUCTION")
])
def test_fail_closed_input_ranges(field,value):
    p=dict(SAMPLE);p[field]=value
    with pytest.raises(ValueError):
        validate(p)

def test_public_users_cannot_inject_model_paths_or_code():
    d=dict(SAMPLE);d["model_url"]="https://untrusted.example"
    with pytest.raises(ValueError):
        validate(d)

def test_two_bridge_sensitivity_suppresses_exactly_six_beam_segments():
    d=dict(SAMPLE);d["bridges"]=False
    out=solve(d)
    assert out["model_counts"]["members"]==159
    assert out["engineering_approval"] is False

def test_authorized_github_contributors_are_allowed_without_user_edit_scripts(tmp_path):
    import json
    from scripts.run_g15_open_3d import parse_issue
    for login in ("FabinGurung","Kaksaveksaka"):
        event={"issue":{"title":"[JP G15 3D] verified case",
          "user":{"login":login},"body":"JP_G15_3D_RUN_V1\n"+json.dumps(SAMPLE)}}
        path=tmp_path/"issue.json";path.write_text(json.dumps(event))
        assert parse_issue(path)==validate(SAMPLE)
    event["issue"]["user"]["login"]="random-public-user"
    path.write_text(json.dumps(event))
    with pytest.raises(ValueError):
        parse_issue(path)
