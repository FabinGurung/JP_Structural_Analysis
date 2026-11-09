"""R6.10 whole-source original combo algebra on explicitly incomplete shell model."""
import hashlib
import math
from pathlib import Path
from scripts.build_r6p10_gravity_casebook import build_casebook, export

def test_12_connected_shell_gravity_and_seismic_sensitivity_cases_and_22_original_combos():
    d=build_casebook()
    assert d["replayed_source_gravity_pattern_cases"]==8
    assert d["replayed_source_conditional_seismic_pattern_cases"]==4
    assert d["recombined_original_source_linear_add_expressions"]==22
    assert d["source_shells_numerically_solved"]==103
    assert d["original_shells_source_vertically_unanchored"]==12
    assert d["original_structural_frames_numerically_solved"]==165
    assert not d["source_8x8_mesh_exactly_reproduced"]
    assert not d["source_approved_seismic_mass_reproduced"]
    assert not d["engineering_approval"] and d["F3_one_way_shear_unsafe"]
    for role in ("ULS","SLS"):
        r=d["role_results"][role]
        assert len(r["independently_run_research_patterns"])==6
        assert len(r["recombined_original_11_linear_add_expressions"])==11
        assert sum(c["source_seismic_combination"] for c in r["recombined_original_11_linear_add_expressions"])==8
        for c in r["recombined_original_11_linear_add_expressions"]:
            assert max(c["force_residual_N"])<max(.5,sum(abs(x) for x in c["applied_resultant_N"])*6e-5)
            assert len(c["signed_member_end_actions_non_design"])==165
            assert all(len(x)==12 and all(math.isfinite(v) for v in x)
                       for x in c["signed_member_end_actions_non_design"].values())
            assert not c["source_eccentricity_plus_minus_5pct_applied"]
            assert not c["fully_reproduced_original_source_case"]
            assert not c["design_envelope_approved"]
            assert c["F3_one_way_shear_unsafe"]

def test_machine_reproducible_source_and_solver_checksum_casebook():
    d,m=export()
    p=Path("site/data/r6p10-connected-shell-gravity-casebook.json")
    assert hashlib.sha256(p.read_bytes()).hexdigest()==m["casebook_SHA256"]
    assert m["independently_run_gravity_stiffness_cases"]==8
    assert m["independently_run_centred_source_coefficient_seismic_sensitivities"]==4
    assert m["source_combinations_algebraically_evaluated"]==22
    assert not m["actual_original_ETABS21_seismic_with_eccentricity_reproduced"]
    assert not m["source_auto_8x8_mesh_reproduced"]
    assert not m["full_building_design_accepted"]
