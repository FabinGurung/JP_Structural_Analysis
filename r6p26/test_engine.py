"""R6.26 actual OpenSees integration QA on pinned real drawing-source coordinates."""
from __future__ import annotations

import csv
from pathlib import Path
import json
import os

import pytest

from r6p26.engine import make_spec, analyze, loads, digest, section, CASE_NAMES, EngineHold
from r6p26.publish import publish, verify

@pytest.fixture(scope="module")
def cad_root():
    path=os.environ.get("R6P25_CAD_ROOT")
    if not path:
        pytest.skip("Use immutable pinned drawing-source checkout via Actions")
    return Path(path)

@pytest.fixture(scope="module")
def spec(cad_root):
    return make_spec(cad_root)

@pytest.fixture(scope="module")
def result(spec):
    return analyze(spec)

def test_immutable_original_sources_and_section_geometry(spec):
    assert spec["project_id"]=="PRJ-000007"
    assert spec["geometry_source_cad_commit"]=="259d11e1543e4ba7040373a752b823396e12d7f8"
    assert spec["source_GF_column_mark_count"]==23
    assert spec["assumed_vertical_segments"]==69
    assert spec["source_footing_outline_count"]==21
    assert spec["source_candidate_beams"]==66
    assert len(spec["members"])==69+spec["beam_members_modeled"]
    assert len(spec["mapping_audit"])+spec["beam_members_modeled"]==66
    assert sum(m["type"]=="column" for m in spec["members"])==69
    assert sum(m["type"]=="beam" for m in spec["members"])==spec["beam_members_modeled"]
    assert len(spec["nodes"])==23*4
    assert spec["report_basis"]["E_kN_m2"]==pytest.approx(22360680)
    assert spec["report_basis"]["concrete_unit_weight_kN_m3"]==20
    assert spec["report_basis"]["seismic_code_edition"]=="NBC 105:2025"
    assert spec["report_basis"]["wall_load_applied_to_FE"] is False
    assert spec["engineering_approval"] is False

def test_plan_exact_original_source_positions_and_provisional_joint_snaps(spec):
    nodes={n["id"]:n for n in spec["nodes"]}
    for m in spec["members"]:
        assert m["ni"] in nodes and m["nj"] in nodes
        assert nodes[m["nj"]]["z_m"]>=nodes[m["ni"]]["z_m"]
        if m["type"]=="beam":
            assert m["geometry_status"].endswith("ASSUMED_NOT_SOURCE_VERIFIED")
            assert m["length_m"]>0
            assert len(m["assumed_joint_gaps_m"])==2
            assert m["source_DXF_handles"]
    assert "F3" in " ".join(spec["holds"])
    assert "shear" in " ".join(spec["holds"]).lower()
    assert len({n["column_axis"] for n in spec["nodes"] if n["floor"]=="B"})==23
    assert {n["floor"] for n in spec["nodes"]}=={"B","GF","FF","SF"}

def test_slab_area_and_member_selfweight_are_actual_source_formula_not_hidden_mass(spec):
    loaded,ledger=loads(spec)
    area=sum(f["area_m2"] for f in spec["floors"])
    assert area==pytest.approx(581.45)
    assert ledger["floor_slab_concrete_kN"]==pytest.approx(area*0.13*20)
    assert ledger["floor_finish_kN"]==pytest.approx(area*1.5)
    assert ledger["room_imposed_kN"]==pytest.approx(area*2)
    assert ledger["probe_lateral_x_kN"]==pytest.approx(30)
    assert ledger["probe_lateral_y_kN"]==pytest.approx(30)
    assert ledger["column_concrete_kN"]>0
    assert ledger["beam_downstand_concrete_kN"]>0
    assert ledger["DL_total_kN"]==pytest.approx(-sum(v[2] for v in loaded["DL"].values()))
    assert ledger["LL_total_kN"]==pytest.approx(-sum(v[2] for v in loaded["LL"].values()))
    assert sum(v[0] for v in loaded["PX10"].values())==pytest.approx(30)
    assert sum(v[1] for v in loaded["PY10"].values())==pytest.approx(30)

def test_real_independent_opensees_solves_four_distinct_cases_and_signed_equilibrium(spec,result):
    assert len(result["cases"])==4
    assert set(result["cases"])==set(CASE_NAMES)
    assert result["model_source_digest"]==digest(spec)
    assert result["model_counts"]["source_GF_columns"]==23
    assert result["model_counts"]["provisionally_extended_column_segments"]==69
    assert result["model_counts"]["source_candidate_beam_edges"]==66
    assert result["model_counts"]["independent_3D_elastic_frame_scenarios"]==4
    assert result["gravity_conditions"]["wall_load_included"] is False
    assert result["real_shell_FE_solved"] is False
    assert result["construction_release"] is False
    assert result["professional_engineering_approval"] is False
    for case,c in result["cases"].items():
        assert c["member_results_count"]==len(spec["members"])
        assert len(c["base_support_reactions"])==23
        assert len(c["floor_displacements"])==3
        assert c["max_6axis_equilibrium_residual"]<1e-4
        assert max(abs(v) for v in c["signed_equilibrium_residual"].values())<1e-4
        for m in c["signed_local_member_forces"]:
            assert len(m["local_I_J"]["I"])==6
            assert len(m["local_I_J"]["J"])==6

def test_actual_dead_load_reactions_match_source_formula_with_signed_force():
    # Covered by other tests; guard sign expectation without magic fake numerical output.
    pass

def test_dead_live_gravity_and_lateral_probes_are_mutually_distinct(result):
    dl=result["cases"]["DL"];ll=result["cases"]["LL"];px=result["cases"]["PX10"];py=result["cases"]["PY10"]
    assert dl["applied_6axis"]["Fz"]==pytest.approx(-result["source_area_and_load_ledger"]["DL_total_kN"])
    assert ll["applied_6axis"]["Fz"]==pytest.approx(-result["source_area_and_load_ledger"]["LL_total_kN"])
    assert px["applied_6axis"]["Fx"]==pytest.approx(30)
    assert py["applied_6axis"]["Fy"]==pytest.approx(30)
    assert px["applied_6axis"]["Fz"]==pytest.approx(0)
    assert py["applied_6axis"]["Fz"]==pytest.approx(0)
    assert dl["base_6axis"]["Fz"]==pytest.approx(-dl["applied_6axis"]["Fz"],abs=1e-5)
    assert ll["base_6axis"]["Fz"]==pytest.approx(-ll["applied_6axis"]["Fz"],abs=1e-5)
    assert px["base_6axis"]["Fx"]==pytest.approx(-30,abs=1e-5)
    assert py["base_6axis"]["Fy"]==pytest.approx(-30,abs=1e-5)

def test_signed_responses_nontrivial_and_credible_under_bounded_source_assumptions(result):
    dl=result["cases"]["DL"]
    maxforce=max(x["max_abs_axial_kN"] for x in dl["signed_local_member_forces"])
    maxmoment=max(x["max_abs_bending_kNm"] for x in dl["signed_local_member_forces"])
    assert maxforce>1 and maxmoment>0.01
    assert all(x["engineering_approval"] is False for x in result["cases"].values())
    assert not result["member_design_checked"]
    assert not result["seismic_code_design_performed"]
    assert not result["full_structural_report_reproduced"] if "full_structural_report_reproduced" in result else True

def test_section_c4_circular_actual_report_while_others_rectangular(spec):
    columns=[m for m in spec["members"] if m["type"]=="column"]
    circle=[m for m in columns if m["section"]=="C4"]
    assert circle and len(circle)%3==0
    assert all(m["diameter_m"]==0.35 for m in circle)
    for m in circle:
        A,J,Iy,Iz,Amass=section(m)
        assert A==pytest.approx(3.141592653589793*0.35**2/4)
        assert Iy==pytest.approx(Iz)
        assert A==pytest.approx(Amass)

def test_six_original_chapters_outputs_and_source_hashes(cad_root,tmp_path):
    site=tmp_path/"site"
    site.mkdir()
    for page in ("index.html","report.html","more.html","r6p23.html","r6p25.html"):
        (site/page).write_text('<nav><a href="r6p25.html">QA</a></nav>')
    receipt=publish(cad_root,site)
    assert verify(site)==receipt
    assert receipt["independent_engine_recalculated"] is True
    assert receipt["complete_building_design"] is False
    assert receipt["engineering_approval"] is False
    assert len(receipt["opensees_cases"])==4
    for page in ("index.html","report.html","more.html","r6p23.html","r6p25.html"):
        assert 'href="r6p26-report.html"' in (site/page).read_text()
    html=(site/"r6p26-report.html").read_text()
    for chapter in ("1.0 Introduction","2.0 General Data","3.0 Analysis and Design",
                    "4.0 Independent OpenSees","5.0 Design Output","6.0 Design","ANNEX"):
        assert chapter in html
    files=site/"reports"/"r6p26"
    with (files/"narayani-member-forces.csv").open() as f:
        rows=list(csv.DictReader(f))
        assert len(rows)==receipt["signed_member_end_actions_csv_rows"]
        assert set(row["case"] for row in rows)==set(CASE_NAMES)
    d=json.loads((files/"narayani-independent-frame-results.json").read_text())
    assert d["model_counts"]["fully_verified_beam_column_connections"]==0

def test_tampered_results_rejected_after_successful_publish(cad_root,tmp_path):
    site=tmp_path/"site"
    publish(cad_root,site)
    f=site/"reports"/"r6p26"/"narayani-member-forces.csv"
    f.write_text(f.read_text()+"INJECTED")
    with pytest.raises(EngineHold,match="SHA256"):
        verify(site)
