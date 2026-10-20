from scripts.build_g15_public_ledger import build

def test_public_ledger_gate07():
    d=build()
    assert d['gate07']['case_count']==204
    assert d['safety']['actual_building_approved'] is False
    assert d['gravity_mass']['gate07_remaining_gap_kN']>0
