"""R6.1 sourced synthetic modal MRSM, drift, torsion and PDelta verification."""
import copy
import csv
import hashlib
import json
import math
from pathlib import Path
import pytest
from jp_structural.solvers.opensees.canonical_seismic import ResponseSpectrumError
from scripts.build_r6_source_seismic_case import (
    DEFAULT,SETTINGS,PFX,build,emit,pdelta_cantilever,R6ReferenceError)

@pytest.fixture(scope="module")
def source():
    return json.loads(DEFAULT.read_text(encoding="utf-8"))

@pytest.fixture(scope="module")
def config():
    return json.loads(SETTINGS.read_text(encoding="utf-8"))

@pytest.fixture(scope="module")
def case():
    return build()

def test_source_eligible_mass_and_source_sha_uncorrupted(case):
    assert case["schema"]=="jp.structural.r6.source_mass_mrsm_drift_torsion_pdelta_reference.v0.1"
    assert case["audited_gravity_kN"]==pytest.approx(128.)
    assert case["audited_seismic_weight_kN"]==pytest.approx(111.2)
    assert case["audited_seismic_mass_kN_s2_m"]==pytest.approx(111.2/9.81,rel=1e-9)
    assert sum(n["mx"] for n in case["source_nodal_mass_rows"])==pytest.approx(111.2/9.81)
    assert all(n["mrx"]==n["mry"]==n["mrz"]==0
               for n in case["source_nodal_mass_rows"])
    assert len(case["source_assembly_SHA256"])==64
    assert case["seismic_mass_source_conservation"] is True

def test_modal_participation_mrsm_drift_and_explicit_two_edge_torsion(case):
    assert case["dynamic_response_axes"]==["X","Y"]
    assert case["modal_mode_count_per_axis"]==6
    assert len(case["source_modal_results"])==2
    for x in case["source_modal_results"]:
        c=x["case"]["case_results"][0]
        assert c["num_modes"]==6
        assert c["modal_combination"]=="CQC"
        assert c["combined"]["base_shear"]>0
        assert c["total_translational_mass"]==pytest.approx(111.2/9.81)
        assert len(c["combined"]["interstorey_drift"])==1
        assert c["combined"]["interstorey_drift"][0]["drift_ratio"]>=0.
        assert len(c["combined"]["torsional_rotation"])==1
        assert c["combined"]["torsional_rotation"][0]["rotation"]>=0.
        assert all(m["period"]>0 for m in c["modes"])
        assert all(m["base_shear"]==pytest.approx(2*m["effective_modal_mass"],rel=1e-7)
                   for m in c["modes"])
        ratios=[m["cumulative_participation_ratio"] for m in c["modes"]]
        assert all(0<=v<=1.000001 for v in ratios)
        assert all(a<=b+1e-7 for a,b in zip(ratios,ratios[1:]))
    assert case["orthogonal_source_factor_envelope"]["orthogonal_factor"]==pytest.approx(.3)

def test_independent_three_compression_PDelta_3d_cantilever_matches_first_order_formula(case):
    p=case["pdelta_independent_3d_benchmark"]
    rows=p["rows"]
    assert [x["axial_compression_kN"] for x in rows]==[0,1000,2000]
    hand=10*3**3/(3*25_000_000*(.4*.4**3/12))
    assert p["analytical_zero_compression_Ux_m"]==pytest.approx(hand)
    assert rows[0]["linear"]["tip_Ux_m"]==pytest.approx(hand,rel=1e-5)
    assert rows[0]["PDelta"]["tip_Ux_m"]==pytest.approx(hand,rel=1e-5)
    assert rows[0]["displacement_amplification"]==pytest.approx(1,rel=1e-5)
    assert rows[0]["displacement_amplification"]<rows[1]["displacement_amplification"]<rows[2]["displacement_amplification"]
    assert p["monotone_PDelta_amplification"] is True
    assert p["whole_building_PDelta_verified"] is False
    assert all(x["linear"]["base_Rx_kN"]==pytest.approx(-10,abs=1e-6)
               for x in rows)

@pytest.mark.parametrize("mutate,error",[
    (lambda c:c["response_spectrum"].update(unit_consistency_verified=False),"unit_consistency_verified"),
    (lambda c:c["response_spectrum"]["units"].update(spectral_acceleration="cm/s^2"),"numerical|mass|unit|spectrum"),
    (lambda c:c["response_spectrum"].update(source_reference="NOT_A_SPECTRUM_SOURCE"),"synthetic spectrum source"),
    (lambda c:c.update(number_modes=0),"mode count"),
    (lambda c:c.update(orthogonal_factor=-1),"out of bounds"),
    (lambda c:c["torsion_probes"]["X"][0].update(separation=0),"positive"),
    (lambda c:c["pdelta"]["axial_compression_kN"].__setitem__(2,500000),"Euler"),
])
def test_invalid_units_unverified_source_provenance_and_unstable_benchmark_fail_closed(config,mutate,error):
    c=copy.deepcopy(config)
    mutate(c)
    with pytest.raises((R6ReferenceError,ResponseSpectrumError,ValueError),match=error):
        build(settings=c)

def test_G15_F3_original_failure_and_seven_chapters_untouched(case):
    assert case["original_building_sources_accepted"]==0
    assert case["original_F3_failure"]=="NOT SAFE IN ONE WAY SHEAR"
    assert case["engineering_approval"] is False
    assert case["nbc105_2025_compliance_approved"] is False
    assert case["connected_shell_modal_mass_verified"] is False
    assert case["pdelta_not_full_building"] is True
    assert [x["id"] for x in case["chapters"]]==[f"{i:02d}" for i in range(1,8)]
    assert {m["id"] for c in case["chapters"] for m in c["modules"]}=={
         *(f"M{i:02d}" for i in range(1,17)),"S17","S18"}

def test_artifact_hash_csv_and_annex_links(tmp_path):
    r=emit(DEFAULT,SETTINGS,tmp_path)
    manifest=json.loads((tmp_path/(PFX+"-manifest.json")).read_text())
    assert manifest["engineering_approval"] is False
    assert len(manifest["files"])==4
    for name,digest in manifest["files"].items():
        assert hashlib.sha256((tmp_path/name).read_bytes()).hexdigest()==digest
    modes=list(csv.DictReader((tmp_path/(PFX+"-modes.csv")).open()))
    pd=list(csv.DictReader((tmp_path/(PFX+"-pdelta.csv")).open()))
    assert len(modes)==12
    assert len(pd)==3
    page=(tmp_path/(PFX+".html")).read_text()
    assert "NOT CODE APPROVED" in page
    assert "NOT SAFE IN ONE WAY SHEAR" in page
    master=(Path(__file__).resolve().parents[1]/"site/report.html").read_text()
    assert 'id="annex-r6p1-source-seismic"' in master
    assert "reports/r6-synthetic-seismic-source.html" in master
