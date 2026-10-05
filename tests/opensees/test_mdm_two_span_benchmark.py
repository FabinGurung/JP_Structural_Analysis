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
