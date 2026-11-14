"""R6.25 real-drawing-source assumed connectivity is traceable, never design approved."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path

import pytest

from r6p25.qa_export import SCHEMA, build, emit, verify


@pytest.fixture(scope="module")
def data():
    cad=os.environ.get("R6P25_CAD_ROOT")
    if cad is None:
        pytest.skip("CAD repository checkout required: set R6P25_CAD_ROOT")
    return build(Path(cad))


def test_source_dimensions_counts_and_user_assumptions(data):
    assert data["schema"]==SCHEMA
    assert data["cad_source_sha"]=="259d11e1543e4ba7040373a752b823396e12d7f8"
    assert data["basis"]["seismic_code"]=="NBC 105:2025"
    assert data["basis"]["concrete_unit_weight_kN_m3"]==20.0
    assert data["location"].startswith("Pokhara")
    assert len(data["columns"])==23 and len(data["footings"])==21
    assert len(data["beams"])==66
    assert [sum(b["level"]==name for b in data["beams"]) for name in ("GF","FF","SF")]==[32,17,17]
    assert data["assumed_vertical_segments"]==69
    assert sum(f["architectural_reported_area_m2"] for f in data["floors"])==pytest.approx(581.45)


def test_every_candidate_has_visible_nearest_axis_distance_and_never_verified(data):
    all_joints=[x for b in data["beams"] for x in b["assumed_endpoint_joints"]]
    assert len(all_joints)==132
    assert len({c["id"] for c in data["columns"]})==23
    assert all(x["engineer_verified"] is False and x["distance_m"]>=0
               and x["column_id"] in {c["id"] for c in data["columns"]}
               for x in all_joints)
    assert any(x["plan_near_750mm"] for x in all_joints)
    assert any(not x["plan_near_750mm"] for x in all_joints)
    assert sum(not j["plan_near_750mm"] for j in all_joints)==data["summary"]["high_gap_endpoint_hypotheses"]
    assert data["summary"]["3d_member_connectivity_engineer_verified"]==0
    assert data["summary"]["actual_FE_solved_cases"]==0


def test_owner_geometry_exceptions_never_overwritten(data):
    c=[x for x in data["columns"] if x["source_axis"]=="I4"]
    assert len(c)==1 and c[0]["working_axis"]=="I3" and c[0]["i3_exception"]
    assert "G2" not in {x["source_axis"] for x in data["columns"]}
    assert sum(f["family"]=="CF1" for f in data["footings"])==2
    assert "G1" in " ".join(data["critical_holds"])
    assert "NOT SAFE IN ONE WAY SHEAR" in " ".join(data["critical_holds"])
    assert data["review_frame"]["full_architectural_common_datum_verified"] is False


def test_loads_support_checks_and_seismic_site_class_remain_held(data):
    assert data["basis"]["soil_bearing_working_kPa"]==160
    assert data["basis"]["geotechnical_report_table_reference_kPa"]==166
    assert data["basis"]["site_class_2025"]=="NOT_YET_CLASSIFIED"
    assert data["basis"]["assumed_diaphragm_model"].startswith("NOT_ASSIGNED")
    assert data["actual_independent_FE_run"] is False
    assert data["engineering_approval"] is False
    assert data["construction_release"] is False


def test_publication_is_hash_verified_and_links_to_narayani(tmp_path,data):
    (tmp_path/"index.html").write_text('<nav><a href="r6p23.html">FE</a></nav>')
    (tmp_path/"report.html").write_text('<nav><a href="r6p23.html">FE</a></nav>')
    (tmp_path/"more.html").write_text('<nav><a href="r6p23.html">FE</a></nav>')
    (tmp_path/"r6p23.html").write_text('<nav><a href="index.html">Home</a></nav>')
    receipt=emit(data,tmp_path)
    assert verify(tmp_path)==receipt
    for page in ("index.html","report.html","more.html","r6p23.html"):
        assert 'href="r6p25.html"' in (tmp_path/page).read_text()
    page=(tmp_path/"r6p25.html").read_text()
    assert "Engineering HOLD" in page
    assert "Narayani" in page and "not a real-project finite-element solution" in page
    assert 'id="floor"' in page and 'id="scope"' in page
    js=(tmp_path/"r6p25.js").read_text()
    assert "plan_near_750mm" in js and "assumed_endpoint_joints" in js
    assert 'M20' in page
    f=tmp_path/"data/r6p25-narayani-qa.json"
    raw=f.read_text()
    assert "13y0b0v8BiL2ooMXy0BFn2dtdSHWNOg2N" in raw
    assert "1PtkCjcWjWtYi9D2-GG4_O3P6KKW9S7B8" not in raw
    # source-coordinate safe: no absolute raw original-site DXF X values
    assert '"source_position_mm"' not in raw and '"source_center_mm"' not in raw
    f.write_text(raw.replace('"engineering_approval":false','"engineering_approval":true'))
    with pytest.raises(Exception, match="SHA256"):
        verify(tmp_path)
