import math

import pytest

from jp_structural.solvers.opensees.canonical_frame import (
    CanonicalTranslationError,
    build_canonical_frame_model,
    run_modal_analysis,
)


def _canonical_frame_model():
    return {
        "schema_version": "0.1",
        "model_id": "MOD-SANITIZED-PHASEB",
        "project": {"project_id": "PRJ-SANITIZED-PHASEB"},
        "units": {
            "force": "N",
            "length": "mm",
            "mass": "N*s^2/mm",
            "time": "s",
        },
        "design_basis": {"code": "SANITIZED_TEST", "damping_ratio": 0.05},
        "source_references": [
            {
                "id": "SRC-SANITIZED",
                "source_type": "SYNTHETIC_TEST",
                "sha256": "0" * 64,
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
            "source_schema": "synthetic.phase_b.v0.1",
            "source_preserving": True,
        },
    }


def test_canonical_phase_b_builds_frame_masses_and_rigid_diaphragm():
    model = _canonical_frame_model()
    built = build_canonical_frame_model(model)

    assert len(built.node_tags) == 4
    assert len(built.element_tags) == 3
    assert len(built.diaphragm_constraints) == 1
    assert built.diaphragm_constraints[0]["retained_node_id"] == "N-T1"
    assert set(built.node_masses) == {"N-T1", "N-T2"}
    assert built.pre_solve_qa["blocking"] is False


def test_modal_results_are_normalized_and_deterministic():
    model = _canonical_frame_model()
    first = run_modal_analysis(model, 2, eigen_solver="fullGenLapack")
    second = run_modal_analysis(model, 2, eigen_solver="fullGenLapack")

    assert first["schema_version"] == "0.1"
    assert first["result_set_id"] == second["result_set_id"]
    assert first["analysis_run_id"] == second["analysis_run_id"]
    assert first["model_id"] == model["model_id"]
    assert first["solver"]["name"] == "OpenSeesPy"
    assert first["solver"]["analysis_type"] == "MODAL_EIGEN"

    case = first["case_results"][0]
    assert case["num_modes"] == 2
    assert case["total_translational_mass"] == {"X": 2.0, "Y": 2.0, "Z": 2.0}
    assert len(case["modes"]) == 2
    for mode in case["modes"]:
        assert math.isfinite(mode["period"]) and mode["period"] > 0
        assert math.isfinite(mode["frequency"]) and mode["frequency"] > 0
        assert math.isfinite(mode["circular_frequency"]) and mode["circular_frequency"] > 0
        assert math.isfinite(mode["generalized_mass"]) and mode["generalized_mass"] > 0
        for axis in ("X", "Y", "Z"):
            ratio = mode["participation_ratio"][axis]
            assert ratio is None or (math.isfinite(ratio) and ratio >= 0)


def test_modal_analysis_refuses_to_invent_nodal_mass_from_mass_source():
    model = _canonical_frame_model()
    model["nodal_masses"] = []
    model["mass_source"] = {
        "id": "MASS-SOURCE",
        "load_factors": [{"load_pattern_id": "DEAD", "factor": 1.0}],
    }

    with pytest.raises(CanonicalTranslationError, match="explicit nodal_masses"):
        run_modal_analysis(model, 1, eigen_solver="fullGenLapack")


def test_rigid_diaphragm_requires_explicit_execution_semantics():
    model = _canonical_frame_model()
    model["diaphragms"][0].pop("constraint_type")

    with pytest.raises(CanonicalTranslationError, match="constraint_type='RIGID'"):
        build_canonical_frame_model(model)
