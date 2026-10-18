import json
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]

def test_two_span_opensees_benchmark_preserves_known_reaction_discrepancy():
    proc=subprocess.run(
        [sys.executable,str(ROOT/"benchmarks/opensees/mdm_two_span_validation.py")],
        cwd=ROOT,check=True,capture_output=True,text=True,
    )
    report=json.loads(proc.stdout)
    comp=report["comparison"]
    assert comp["moment_checks_pass"] is True
    assert comp["equilibrium"]["opensees_global_equilibrium_pass"] is True
    assert comp["status"]=="FAIL_REACTION_DATA_RECONCILIATION"
    # This isn't merely a disagreement between two solvers: original source
    # reaction values contradict original source final member end moments.
    assert comp["stored_member_local_statics_pass"] is False
    by_member={x["member"]:x for x in comp["stored_member_local_static_checks"]}
    assert by_member["AB"]["expected_near_from_stored_moments_kN"]==33.75
    assert by_member["AB"]["expected_far_from_stored_moments_kN"]==26.25
    assert by_member["BC"]["expected_near_from_stored_moments_kN"]==3.75
    assert by_member["BC"]["expected_far_from_stored_moments_kN"]==-3.75
    assert all(x["force_balance_pass"] for x in by_member.values())
    assert not any(x["moment_balance_pass"] for x in by_member.values())
