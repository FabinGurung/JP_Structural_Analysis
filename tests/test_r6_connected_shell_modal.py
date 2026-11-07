"""R6.2 same connected ShellMITC4-frame modal inertia and CQC QA."""
import copy
import csv
import hashlib
import json
import math
from pathlib import Path
import pytest

from scripts.build_r6_connected_shell_modal import (
    DEFAULT, SETTINGS, PFX, MODES, AXES, NMODES, ShellModalError,
    build, emit, _cqc,
)
from scripts.build_r5_connected_shell_frame import exact_reference,solve_mesh
from jp_structural.solvers.opensees.canonical_seismic import (
    cqc_correlation_coefficient, ResponseSpectrumError)

@pytest.fixture(scope="module")
def r2():
    return build(meshes=(2,))

def test_actual_same_shell_boundary_and_source_mass(r2):
    assert r2["schema"]=="jp.structural.r6.connected_shell_modal_mrsm.v0.1"
    assert r2["mesh_divisions"]==[2]
    assert r2["diaphragm_modes"]==list(MODES)
    assert r2["axes"]==list(AXES)
    assert r2["modes_per_axis"]==4
    assert r2["native_modal_static_run_count"]==16
    assert r2["modal_eigensolution_count"]==16
    assert r2["original_source_seismic_corner_mass_unchanged"]
    assert r2["same_R5p6_connected_shell_FE"]
    assert r2["R6p1_canonical_frame_model_not_used_for_R6p2"]
    assert r2["audited_seismic_weight_kN"]==pytest.approx(111.2)
    assert r2["source_total_gravity_kN"]==pytest.approx(128.)
    assert r2["audited_seismic_mass_kN_s2_m"]==pytest.approx(111.2/9.81)
    assert len(r2["source_mass_SHA256"])==64

def test_four_true_modes_per_direction_and_MPC(r2):
    assert len(r2["participation_summaries"])==4
    assert len(r2["raw_modal_static_results"])==16
    for x in r2["raw_modal_static_results"]:
        assert x["axis"] in AXES
        assert x["diaphragm_mode"] in MODES
        assert x["mode"] in (1,2,3,4)
        assert x["eigenvalue_1_s2"]>0
        assert x["period_s"]>0
        assert x["source_Sa_m_s2"]==pytest.approx(2.)
        assert x["source_total_mass_kN_s2_m"]==pytest.approx(111.2/9.81)
        assert x["modal_mass_participation_fraction"]>=0
        assert x["six_component_support_balance_pass"]
        assert x["eigen_displacement_vs_modal_force_static_pass"]
        assert len(x["native_IJ_member_actions"])==8
        for m in ("BM1","BM2","BM3","BM4"):
            assert len(x["native_IJ_member_actions"][m])==2
        for m in ("COL1","COL2","COL3","COL4"):
            assert len(x["native_IJ_member_actions"][m])==1
        assert max(abs(v) for v in x["global_force_moment_residual"])<1e-4
        assert x["source_modal_base_shear_kN"]==pytest.approx(
             x["effective_modal_mass_kN_s2_m"]*2.,abs=1e-7)

def test_CQC_member_component_magnitudes_are_not_concurrent_signed_vectors(r2):
    for x in r2["participation_summaries"]:
        assert x["axis"] in AXES
        assert len(x["modes"])==4
        assert x["cqc_signed_concurrent_vector"] is False
        assert x["combined_base_shear_kN"]>0
        assert x["combined_drift_ratio"]>=0
        assert x["combined_roof_torsion_rad"]>=0
        assert 0<=x["cumulative_modal_participation_fraction"]<=1.0005
        assert x["unrepresented_modal_mass_fraction"]>=0
        for member in x["member_CQC_envelopes"]:
            assert member["concurrent_signed_combination"] is False
            assert set(member["CQC_magnitude"])=={"N","Vy","Vz","T","My","Mz"}
            assert all(math.isfinite(v) and v>=0 for v in member["CQC_magnitude"].values())
    assert cqc_correlation_coefficient(10,10,.05)==pytest.approx(1.)
    assert _cqc((3,4),(10,30),.0001)==pytest.approx(5.,abs=.02)

def test_reject_wrong_source_settings_and_mode_count():
    original=json.loads(DEFAULT.read_text())
    settings=json.loads(SETTINGS.read_text())
    changed=copy.deepcopy(settings)
    changed["number_modes"]=6
    with pytest.raises(ShellModalError,match="four"):
        build(spec=original,settings=changed,meshes=(2,))
    changed=copy.deepcopy(settings)
    changed["response_spectrum"]["units"]["spectral_acceleration"]="cm/s^2"
    with pytest.raises((ShellModalError,ResponseSpectrumError),match="units|provenance"):
        build(spec=original,settings=changed,meshes=(2,))
    with pytest.raises(ShellModalError,match="mesh"):
        build(spec=original,settings=settings,meshes=(4,))
    source=copy.deepcopy(original)
    source["model"]["nodal_masses"]=[{"node_id":"R1","mx":1}]
    with pytest.raises((ShellModalError,ValueError),match="mass"):
        build(spec=source,settings=settings,meshes=(2,))

def test_reports_manifest_and_single_live_master_annex(tmp_path):
    r=emit(DEFAULT,SETTINGS,tmp_path,meshes=(2,))
    manifest=json.loads((tmp_path/(PFX+"-manifest.json")).read_text())
    assert not manifest["engineering_approval"]
    assert len(manifest["files"])==4
    for name,digest in manifest["files"].items():
        assert hashlib.sha256((tmp_path/name).read_bytes()).hexdigest()==digest
    modal=list(csv.DictReader((tmp_path/(PFX+"-modal.csv")).open()))
    actions=list(csv.DictReader((tmp_path/(PFX+"-member-actions.csv")).open()))
    assert len(modal)==16 and len(actions)>0
    html=(tmp_path/(PFX+".html")).read_text()
    assert "NOT ENGINEER APPROVED" in html
    assert "NOT SAFE IN ONE WAY SHEAR" in html
    master=(Path(__file__).resolve().parents[1]/"site/report.html").read_text()
    assert 'id="annex-r6p2-connected-shell-modal"' in master
    assert "reports/r6-connected-shell-modal.html" in master
    assert r["original_building_accepted_evidence_gates"]==0
    assert r["original_F3_failure"]=="NOT SAFE IN ONE WAY SHEAR"
    assert r["engineering_approval"] is False and r["permit_eligible"] is False

def test_previous_connected_static_shell_solver_unchanged_after_modal_entry():
    src=json.loads(DEFAULT.read_text())
    ref=exact_reference(src)
    a=solve_mesh(ref,2,"HX",diaphragm_mode="RIGID_INPLANE_MPC")
    assert a["global_equilibrium_pass"]
    assert abs(a["applied_force_kN"][0]-40)<1e-6
    assert a["rigid_compatibility_residual_m"]<1e-8
