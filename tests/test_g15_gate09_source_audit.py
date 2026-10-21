import math
from scripts.build_g15_gate09_source_audit import build

def test_panel_and_mass():
    x=build()
    assert math.isclose(x['panel']['area_m2'],17.874)
    assert len(x['panel']['candidate_beam_line_support'])==4
    assert math.isclose(x['mass_reconciliation']['unexplained_W_kN'],772.0329166282687,abs_tol=.001)
    assert x['mass_reconciliation']['source_supported_new_mass_kN']==0
    assert x['source_F3_status']=='NOT SAFE IN ONE WAY SHEAR'
    assert x['engineering_approval'] is False
