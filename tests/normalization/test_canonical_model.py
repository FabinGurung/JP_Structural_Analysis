from __future__ import annotations

from copy import deepcopy

from jp_structural.normalization.canonical import canonicalize_e2k_model
from jp_structural.qa.pre_solve import run_pre_solve_qa


def _legacy_model():
    return {
        "schema": "jp_structural.normalized_model.legacy_e2k.v0.1",
        "source": {"filename": "sanitized.e2k", "sha256": "abc123", "size_bytes": 321},
        "units": {"force": "N", "length": "mm", "temperature": "C"},
        "stories": [
            {"name": "Base", "elevation": 0.0},
            {"name": "Story1", "elevation": 3000.0},
        ],
        "materials": [{"name": "M", "E": 25000.0, "poisson": 0.2}],
        "frame_sections": [
            {
                "name": "C",
                "material": "M",
                "shape": "Rectangular",
                "width": 300.0,
                "depth": 300.0,
            }
        ],
        "slab_properties": [],
        "load_patterns": [{"name": "Dead", "type": "Dead", "self_weight": 1.0}],
        "nodes": [
            {
                "id": "Base::1",
                "source_point_id": "1",
                "story": "Base",
                "x": 0.0,
                "y": 0.0,
                "z": 0.0,
                "restraint": "UX UY UZ RX RY RZ",
                "diaphragm": None,
            },
            {
                "id": "Story1::1",
                "source_point_id": "1",
                "story": "Story1",
                "x": 0.0,
                "y": 0.0,
                "z": 3000.0,
                "restraint": None,
                "diaphragm": "D1",
            },
        ],
        "frames": [
            {
                "id": "Story1::C1",
                "source_id": "C1",
                "story": "Story1",
                "type": "COLUMN",
                "i_node": "Story1::1",
                "j_node": "Base::1",
                "section": "C",
            }
        ],
        "areas": [],
        "frame_loads": [],
        "area_loads": [],
        "mass_source": {
            "definition": 'MASSSOURCE "MsSrc1"',
            "load_factors": [{"pattern": "Dead", "factor": 1.0}],
        },
        "load_cases": [{"name": "Dead", "type": "Linear Static", "modal_case": None}],
        "load_combinations": ["1.2D"],
        "qa": {"status": "PASS_REFERENCE_INTEGRITY", "warnings": []},
    }


def _canonical():
    return canonicalize_e2k_model(
        _legacy_model(),
        project_id="PRJ-SANITIZED",
        design_basis={"code": "SANITIZED_TEST", "damping_ratio": 0.05},
    )


def test_canonical_bridge_is_stable_and_source_preserving():
    a = _canonical()
    b = _canonical()

    assert a["schema_version"] == "0.1"
    assert a["model_id"] == b["model_id"]
    assert a["nodes"][0]["id"] == b["nodes"][0]["id"]
    assert a["frame_members"][0]["id"] == b["frame_members"][0]["id"]
    assert a["source_references"][0]["sha256"] == "abc123"
    assert a["source_qa"]["status"] == "PASS_REFERENCE_INTEGRITY"
    assert a["translation_scope"]["end_releases"] == "NOT_NORMALIZED_FROM_LEGACY_PAYLOAD"


def test_canonical_bridge_expands_support_diaphragm_and_mass_references():
    model = _canonical()

    support = model["supports"][0]
    assert set(support["restrained_dofs"]) == {"UX", "UY", "UZ", "RX", "RY", "RZ"}
    assert support["node_id"] in {n["id"] for n in model["nodes"]}

    diaphragm = model["diaphragms"][0]
    assert diaphragm["source_name"] == "D1"
    assert len(diaphragm["node_ids"]) == 1

    dead = model["load_patterns"][0]
    assert model["mass_source"]["load_factors"][0]["load_pattern_id"] == dead["id"]


def test_pre_solve_qa_accepts_supported_canonical_frame():
    out = run_pre_solve_qa(_canonical())
    assert out["status"] == "PASS"
    assert out["blocking"] is False


def test_pre_solve_qa_fails_unsupported_disconnected_component():
    model = _canonical()
    top = deepcopy(model["nodes"][1])
    base = deepcopy(model["nodes"][0])
    top["id"] = "NOD-X-TOP"
    top["x"] = 5000.0
    top["support_id"] = None
    top["diaphragm_id"] = None
    base["id"] = "NOD-X-BASE"
    base["x"] = 5000.0
    base["support_id"] = None
    model["nodes"].extend([top, base])

    member = deepcopy(model["frame_members"][0])
    member["id"] = "FRM-X"
    member["i_node"] = top["id"]
    member["j_node"] = base["id"]
    model["frame_members"].append(member)

    out = run_pre_solve_qa(model)
    codes = {x["code"] for x in out["findings"]}
    assert out["status"] == "FAIL"
    assert "UNSUPPORTED_FRAME_COMPONENT" in codes
    assert "DISCONNECTED_FRAME_COMPONENTS" in codes


def test_pre_solve_qa_blocks_unresolved_response_spectrum_inputs():
    model = _canonical()
    model["load_cases"].append(
        {
            "id": "CASE-RS",
            "source_name": "RSX",
            "type": "Response Spectrum",
            "modal_case_id": None,
        }
    )

    out = run_pre_solve_qa(model)
    codes = {x["code"] for x in out["findings"]}
    assert out["status"] == "FAIL"
    assert "RESPONSE_SPECTRUM_INPUT_MISSING" in codes
