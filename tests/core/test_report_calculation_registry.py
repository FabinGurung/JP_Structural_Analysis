import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_coverage_has_all_eighteen_contract_modules():
    path = ROOT / "registry/report-calculation-coverage.v0.1.json"
    obj = json.loads(path.read_text(encoding="utf-8"))
    rows = {item["id"]: item for item in obj["requirements"]}
    assert len(rows) == 18
    assert set(rows) == {f"M{i:02d}" for i in range(1, 17)} | {"S17", "S18"}
    assert rows["M08"]["status"] == "PARTIAL"
    assert rows["M09"]["status"] == "PARTIAL"
    assert rows["M12"]["status"] == "MISSING"
    assert rows["M13"]["status"] == "MISSING"
    assert rows["M01"]["status"] == "PARTIAL"
    assert rows["M02"]["status"] == "PARTIAL"
    assert "f7c2f8ad" in obj["frozen_seq9_commit"]
    assert all(x["validation_gate"] and x["remaining_scope"] for x in rows.values())


def test_site_data_is_reproducible_and_links_real_modules():
    subprocess.run([sys.executable, str(ROOT/"scripts/build_calculation_coverage.py"), "--check"], cwd=ROOT, check=True)
