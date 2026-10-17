import copy
import math
import pytest
from jp_structural.solvers.native.load_mass_assembly import (
    LoadAssemblyError, allocate_loads_to_nodes, verify_vertical_support_equilibrium
)

NODES=[{"node_id":"N0","storey_id":"F1","x_m":0,"y_m":0,"z_m":3},
       {"node_id":"N4","storey_id":"F1","x_m":4,"y_m":0,"z_m":3}]
LOADS=[
    {"id":"DL1","source_key":"concrete:slabA:DL","load_category":"DEAD",
     "downward_load_kN":100,"participation_factor":1.0,
     "node_shares":[{"node_id":"N0","fraction":0.5},{"node_id":"N4","fraction":0.5}]},
    {"id":"LL1","source_key":"occupancy:slabA:LL","load_category":"OTHER_LIVE",
     "downward_load_kN":30,"participation_factor":0.3,
     "node_shares":[{"node_id":"N0","fraction":0.25},{"node_id":"N4","fraction":0.75}]}
]

def test_conservative_gravity_and_mass_assembly():
    out=allocate_loads_to_nodes(NODES,LOADS,9.81)
    assert out["total_gravity_load_kN"]==pytest.approx(130)
    assert out["total_seismic_weight_kN"]==pytest.approx(109)
    mass={x["node_id"]:x["mx"] for x in out["nodal_masses"]}
    assert mass["N0"]*9.81==pytest.approx(52.25)
    assert mass["N4"]*9.81==pytest.approx(56.75)
    assert sum(x["downward_load_kN"] for x in out["gravity_nodal_loads"])==pytest.approx(130)
    assert out["storeys"][0]["center_mass_x_m"]==pytest.approx(4*56.75/109)
    assert out["units"]["mass"]=="kN*s^2/m"
    assert all(x["mrz"]==0 for x in out["nodal_masses"])

def test_finite_gravity_reaction_force_and_moments():
    out=allocate_loads_to_nodes(NODES,LOADS,9.81)
    reaction=[{"node_id":"N0","Rz_kN":57.5},{"node_id":"N4","Rz_kN":72.5}]
    assert verify_vertical_support_equilibrium(NODES,out["gravity_nodal_loads"],reaction)["status"].endswith("PASS")

def test_reaction_error_and_wrong_support_couple_fail():
    out=allocate_loads_to_nodes(NODES,LOADS,9.81)
    for reactions in (
        [{"node_id":"N0","Rz_kN":57.5},{"node_id":"N4","Rz_kN":71.5}],
        [{"node_id":"N0","Rz_kN":57.5,"My_kNm":1},{"node_id":"N4","Rz_kN":72.5}],
        [{"node_id":"N0","Rz_kN":130}],
    ):
        with pytest.raises(LoadAssemblyError):
            verify_vertical_support_equilibrium(NODES,out["gravity_nodal_loads"],reactions)

@pytest.mark.parametrize("modify",[
    lambda x:x[0].update(source_key="occupancy:slabA:LL"),
    lambda x:x[0]["node_shares"][0].update(fraction=.4),
    lambda x:x[0]["node_shares"].append({"node_id":"N0","fraction":0}),
    lambda x:x[0].update(participation_factor=1.1),
    lambda x:x[1].pop("participation_factor"),
    lambda x:x[1].update(downward_load_kN=math.inf),
    lambda x:x[0]["node_shares"][0].update(node_id="UNKNOWN"),
    lambda x:x[0].update(id="LL1"),
])
def test_ambiguous_or_invalid_loads_fail_closed(modify):
    rows=copy.deepcopy(LOADS);modify(rows)
    with pytest.raises(LoadAssemblyError):
        allocate_loads_to_nodes(NODES,rows,9.81)

def test_signed_coordinates_and_multiple_storeys():
    nodes=[{"node_id":"N-2","storey_id":"F2","x_m":-2,"y_m":-1,"z_m":6}]
    loads=[{"id":"d","source_key":"member:v1:DL","load_category":"DEAD",
            "downward_load_kN":10,"participation_factor":1,
            "node_shares":[{"node_id":"N-2","fraction":1}]}]
    out=allocate_loads_to_nodes(nodes,loads,9.81)
    assert out["storeys"][0]["center_mass_x_m"]==-2
    assert out["storeys"][0]["center_mass_y_m"]==-1
