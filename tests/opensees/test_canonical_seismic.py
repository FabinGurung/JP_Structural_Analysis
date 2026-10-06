import pytest

from jp_structural.solvers.opensees.canonical_seismic import (
    ResponseSpectrumError,
    interpolate_spectral_acceleration,
    normalize_response_spectrum,
    run_canonical_response_spectrum,
)


def _model():
    return {
        "schema_version": "0.1",
        "model_id": "MOD-SANITIZED-PHASEC",
        "project": {"project_id": "PRJ-SANITIZED-PHASEC"},
        "units": {
            "force": "N",
            "length": "mm",
            "mass": "N*s^2/mm",
            "time": "s",
        },
        "design_basis": {"code": "SANITIZED_TEST", "damping_ratio": 0.05},
        "source_references": [
            {
                "id": "SRC-SANITIZED-PHASEC",
                "source_type": "SYNTHETIC_TEST",
                "sha256": "1" * 64,
            }
        ],
        "storeys": [
            {"id": "STY-BASE", "source_name": "Base", "elevation": 0.0},
            {"id": "STY-ROOF", "source_name": "Roof", "elevation": 3000.0},
        ],
        "nodes": [
            {
                "id": "N-B1",
                "storey_id": "STY-BASE",
                "x": 0.0,
                "y": 0.0,
                "z": 0.0,
                "support_id": "SUP-B1",
                "diaphragm_id": None,
            },
            {
                "id": "N-B2",
                "storey_id": "STY-BASE",
                "x": 4000.0,
                "y": 0.0,
                "z": 0.0,
                "support_id": "SUP-B2",
                "diaphragm_id": None,
            },
            {
                "id": "N-T1",
                "storey_id": "STY-ROOF",
                "x": 0.0,
                "y": 0.0,
                "z": 3000.0,
                "support_id": None,
                "diaphragm_id": "DIA-R",
            },
            {
                "id": "N-T2",
                "storey_id": "STY-ROOF",
                "x": 4000.0,
                "y": 0.0,
                "z": 3000.0,
                "support_id": None,
                "diaphragm_id": "DIA-R",
            },
        ],
        "materials": [
            {
                "id": "MAT-C",
                "source_name": "Concrete",
                "E": 25000.0,
                "poisson": 0.2,
            }
        ],
        "sections": [
            {
                "id": "SEC-300",
                "source_name": "300x300",
                "section_family": "frame",
                "material_id": "MAT-C",
                "shape": "Rectangular",
                "width": 300.0,
                "depth": 300.0,
            }
        ],
        "supports": [
            {
                "id": "SUP-B1",
                "node_id": "N-B1",
                "restrained_dofs": ["UX", "UY", "UZ", "RX", "RY", "RZ"],
            },
            {
                "id": "SUP-B2",
                "node_id": "N-B2",
                "restrained_dofs": ["UX", "UY", "UZ", "RX", "RY", "RZ"],
            },
        ],
        "constraints": [],
        "diaphragms": [
            {
                "id": "DIA-R",
                "source_name": "Roof diaphragm",
                "constraint_type": "RIGID",
                "perpendicular_axis": "Z",
                "retained_node_id": "N-T1",
                "node_ids": ["N-T1", "N-T2"],
            }
        ],
        "frame_members": [
            {
                "id": "FRM-C1",
                "member_type": "COLUMN",
                "i_node": "N-B1",
                "j_node": "N-T1",
                "section_id": "SEC-300",
            },
            {
                "id": "FRM-C2",
                "member_type": "COLUMN",
                "i_node": "N-B2",
                "j_node": "N-T2",
                "section_id": "SEC-300",
            },
            {
                "id": "FRM-B1",
                "member_type": "BEAM",
                "i_node": "N-T1",
                "j_node": "N-T2",
                "section_id": "SEC-300",
            },
        ],
        "shell_elements": [],
        "end_releases": [],
        "rigid_offsets": [],
        "stiffness_modifiers": [],
        "load_patterns": [],
        "load_cases": [],
        "load_combinations": [],
        "mass_source": {},
        "joint_loads": [],
        "frame_loads": [],
        "area_loads": [],
        "response_spectra": [],
        "analysis_cases": [],
        "nodal_masses": [
            {"node_id": "N-T1", "mx": 1.0, "my": 1.0, "mz": 1.0},
            {"node_id": "N-T2", "mx": 1.0, "my": 1.0, "mz": 1.0},
        ],
        "source_qa": {"status": "PASS_REFERENCE_INTEGRITY", "warnings": []},
        "normalization_warnings": [],
        "translation_scope": {
            "local_axes": "AXIS_ALIGNED_SANITIZED_FIXTURE",
            "end_releases": "NOT_PRESENT",
            "rigid_offsets": "NOT_PRESENT",
            "shell_mesh": "NOT_APPLICABLE",
        },
        "provenance": {
            "source_schema": "synthetic.phase_c.v0.1",
            "source_preserving": True,
        },
    }


def _spectrum():
    return {
        "id": "RS-SANITIZED-CONSTANT",
        "ordinate_type": "ACCELERATION",
        "damping_ratio": 0.05,
        "scale_factor": 1.0,
        "unit_consistency_verified": True,
        "units": {
            "period": "s",
            "spectral_acceleration": "mm/s^2",
            "displacement": "mm",
            "base_shear": "N",
        },
        "points": [
            {"period": 0.0, "spectral_acceleration": 1000.0},
            {"period": 10.0, "spectral_acceleration": 1000.0},
        ],
        "source_reference": "SYNTHETIC_TEST_ONLY",
    }


def test_spectrum_normalization_and_interpolation_are_deterministic():
    normalized = normalize_response_spectrum(_spectrum(), model_units=_model()["units"])
    assert interpolate_spectral_acceleration(normalized, 0.0) == pytest.approx(1000.0)
    assert interpolate_spectral_acceleration(normalized, 4.25) == pytest.approx(1000.0)
    assert interpolate_spectral_acceleration(normalized, 10.0) == pytest.approx(1000.0)


def test_response_spectrum_returns_base_shear_storey_displacement_and_drift():
    kwargs = {
        "direction": "X",
        "modal_combination": "SRSS",
        "response_points": [
            {"storey_id": "STY-BASE", "node_id": "N-B1"},
            {"storey_id": "STY-ROOF", "node_id": "N-T1"},
        ],
        "eigen_solver": "fullGenLapack",
    }
    first = run_canonical_response_spectrum(_model(), _spectrum(), 2, **kwargs)
    second = run_canonical_response_spectrum(_model(), _spectrum(), 2, **kwargs)

    assert first["analysis_run_id"] == second["analysis_run_id"]
    assert first["result_set_id"] == second["result_set_id"]
    case = first["case_results"][0]
    assert case["direction"] == "X"
    assert case["modal_combination"] == "SRSS"
    assert case["combined"]["base_shear"] > 0.0
    assert len(case["combined"]["storey_displacement"]) == 2
    assert len(case["combined"]["interstorey_drift"]) == 1
    assert case["combined"]["interstorey_drift"][0]["drift_ratio"] >= 0.0
    assert first["qa"]["scope"]["accidental_eccentricity"] == "NOT_IMPLEMENTED_FAIL_CLOSED"


def test_response_spectrum_refuses_unverified_unit_conversion():
    spectrum = _spectrum()
    spectrum["unit_consistency_verified"] = False
    with pytest.raises(ResponseSpectrumError, match="unit_consistency_verified"):
        run_canonical_response_spectrum(
            _model(),
            spectrum,
            2,
            direction="X",
            eigen_solver="fullGenLapack",
        )


def test_response_spectrum_refuses_period_extrapolation_and_unsupported_combination():
    normalized = normalize_response_spectrum(_spectrum(), model_units=_model()["units"])
    with pytest.raises(ResponseSpectrumError, match="outside explicit spectrum domain"):
        interpolate_spectral_acceleration(normalized, 10.1)

    with pytest.raises(ResponseSpectrumError, match="only explicit modal_combination='SRSS'"):
        run_canonical_response_spectrum(
            _model(),
            _spectrum(),
            2,
            direction="X",
            modal_combination="CQC",
            eigen_solver="fullGenLapack",
        )


def test_explicit_design_limits_are_evaluated_but_not_invented():
    result = run_canonical_response_spectrum(
        _model(),
        _spectrum(),
        2,
        direction="X",
        response_points=[
            {"storey_id": "STY-BASE", "node_id": "N-B1"},
            {"storey_id": "STY-ROOF", "node_id": "N-T1"},
        ],
        design_checks={
            "code_reference": "SYNTHETIC_LIMITS_NOT_A_REAL_CODE",
            "minimum_modal_mass_participation_ratio": 0.01,
            "maximum_interstorey_drift_ratio": 1.0,
        },
        eigen_solver="fullGenLapack",
    )
    checks = result["case_results"][0]["design_checks"]
    assert checks["code_reference"] == "SYNTHETIC_LIMITS_NOT_A_REAL_CODE"
    assert checks["checks"]
    assert all(item["status"] in {"PASS", "FAIL", "UNRESOLVED"} for item in checks["checks"])
