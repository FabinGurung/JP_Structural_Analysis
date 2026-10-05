import json
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]

def test_sanitized_sar_package_builds_fail_closed(tmp_path):
    out=tmp_path/"sar"
    subprocess.run([sys.executable,str(ROOT/"examples/sanitized/mdm_two_span/build_example.py"),"--output",str(out)],cwd=ROOT,check=True)
    validation=json.loads((out/"validation_results.json").read_text())
    manifest=json.loads((out/"report_manifest.json").read_text())
    sar=(out/"SAR.html").read_text()
    assert validation["status"]=="FAIL"
    assert validation["professional_state"]=="ENGINEER_REVIEW_REQUIRED"
    assert manifest["unresolved_count"]>=1
    assert "ENGINEER_REVIEW_REQUIRED" in sar
    assert (out/"analysis_results.json").exists()
