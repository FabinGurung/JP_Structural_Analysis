"""Original supplied SP16:1980 provenance and source Table A numeric regressions."""
import json
from pathlib import Path
import pytest
from jp_structural.solvers.native.rc_column_section import _steel_stress, STEEL_TABLE_SOURCE

DATA=json.loads((Path(__file__).resolve().parents[2]/"registry"/"sp16_1980_primary_source.v0.1.json").read_text())

def test_original_sp16_source_and_chart_no_false_acceptance():
    assert DATA["sha256"]=="d2a6246a5dc7504568f4e55f310dd4be9d925fb1a8b04b6d7f5132c93f66c76e"
    assert DATA["pages"]==255
    assert DATA["table_a"]["physical_page"]==29
    assert DATA["chart31"]["physical_page"]==139
    assert DATA["chart31"]["printed_page"]==116
    assert DATA["chart31"]["original_chart_visually_available"] is True
    assert DATA["chart31"]["curve_points_independently_digitized"] is False
    assert DATA["chart31"]["engineering_approval"] is False
    assert DATA["engineering_approval"] is False
    assert "SP16:1980 original" in STEEL_TABLE_SOURCE

@pytest.mark.parametrize("fy,frac,strain,stress",[[415,0.8,0.00144,288.7],[415,0.85,0.00163,306.7],[415,0.9,0.00192,324.8],[415,0.95,0.00241,342.8],[415,0.975,0.00276,351.8],[415,1,0.0038,360.9],[500,0.8,0.00174,347.8],[500,0.85,0.00195,369.6],[500,0.9,0.00226,391.3],[500,0.95,0.00277,413],[500,0.975,0.00312,423.9],[500,1,0.00417,434.8]])
def test_original_sp16_table_a_12_points(fy,frac,strain,stress):
    assert {"fy_mpa":fy,"fraction":frac,"strain":strain,"stress_mpa":stress} in DATA["table_a"]["points"]
    assert _steel_stress(strain,fy)==pytest.approx(stress,abs=.11)
    assert _steel_stress(-strain,fy)==pytest.approx(-stress,abs=.11)
