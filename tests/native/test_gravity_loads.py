import math
import pytest
from jp_structural.solvers.native.gravity_loads import (
    LoadInputError, layered_area_dead_load, wall_line_dead_load,
    member_self_weight, explicit_seismic_weight, mass_from_weight,
)


def test_fictional_layers_and_wall_math_not_code_design():
    layers = layered_area_dead_load([
        {"id":"tile","thickness_m":.025,"unit_weight_kN_m3":26.5},
        {"id":"mortar","thickness_m":.025,"unit_weight_kN_m3":20.4},
        {"id":"plaster","thickness_m":.015,"unit_weight_kN_m3":20.4},
    ])
    assert layers["area_load_kN_m2"] == pytest.approx(1.4785)
    wall = wall_line_dead_load(19.2, 3.05, .21, .23, .4)
    assert wall["line_load_kN_m"] == pytest.approx(9.244896)
    assert wall_line_dead_load(20, 3, 1, .2)["line_load_kN_m"] == 0


def test_explicit_mass_conservation_and_self_weight():
    assert member_self_weight(.16, 3, 25)["self_weight_kN"] == pytest.approx(12)
    w = explicit_seismic_weight([
        {"id":"DL","downward_load_kN":100,"participation_factor":1},
        {"id":"LL","downward_load_kN":30,"participation_factor":.3},
    ])
    assert w["total_seismic_weight_kN"] == pytest.approx(109)
    assert mass_from_weight(109, 9.81)["mass_kN_s2_per_m"] == pytest.approx(109/9.81)


@pytest.mark.parametrize("call", [
    lambda: layered_area_dead_load([]),
    lambda: layered_area_dead_load([{"id":"x","thickness_m":0,"unit_weight_kN_m3":20}]),
    lambda: layered_area_dead_load([
        {"id":"x","thickness_m":.2,"unit_weight_kN_m3":20},
        {"id":"x","thickness_m":.3,"unit_weight_kN_m3":25}]),
    lambda: wall_line_dead_load(20,3,-.01,.2),
    lambda: wall_line_dead_load(20,3,.1,.2,3),
    lambda: member_self_weight(.2,0,25),
    lambda: explicit_seismic_weight([{"id":"d","downward_load_kN":100}]),
    lambda: explicit_seismic_weight([{"id":"d","downward_load_kN":100,"participation_factor":1.1}]),
    lambda: explicit_seismic_weight([{"id":"d","downward_load_kN":0,"participation_factor":1}]),
    lambda: mass_from_weight(10,0),
    lambda: mass_from_weight(10,math.nan),
])
def test_bad_load_inputs_fail_closed(call):
    with pytest.raises(LoadInputError):
        call()
