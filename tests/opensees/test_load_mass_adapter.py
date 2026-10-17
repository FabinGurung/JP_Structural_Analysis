import copy
import math
import pytest
from jp_structural.solvers.opensees.load_mass_adapter import (
    LoadMassAdapterError, bind_assembly_to_canonical_model, run_audited_static_gravity
)
from jp_structural.solvers.native.load_mass_assembly import allocate_loads_to_nodes
from jp_structural.solvers.opensees.canonical_frame import build_canonical_frame_model


def _fixture():
    m={
        "schema_version":"0.1","model_id":"DEMO-FRAME-1",
        "project":{"project_id":"SYNTHETIC-001"},
        "units":{"force":"kN","length":"m","time":"s","mass":"kN*s^2/m"},
        "source_references":[{"id":"SYNTH","source_type":"SYNTHETIC"}],
        "storeys":[{"id":"BASE","elevation":0},{"id":"ROOF","elevation":3}],
        "nodes":[
            {"id":"B1","storey_id":"BASE","x":0,"y":0,"z":0},
            {"id":"B2","storey_id":"BASE","x":4,"y":0,"z":0},
            {"id":"T1","storey_id":"ROOF","x":0,"y":0,"z":3},
            {"id":"T2","storey_id":"ROOF","x":4,"y":0,"z":3}],
        "materials":[{"id":"CONC","E":25000000,"poisson":.2}],
        "sections":[{"id":"S","material_id":"CONC","shape":"Rectangular","width":.3,"depth":.3}],
        "supports":[
            {"id":"FIX1","node_id":"B1","restrained_dofs":["UX","UY","UZ","RX","RY","RZ"]},
            {"id":"FIX2","node_id":"B2","restrained_dofs":["UX","UY","UZ","RX","RY","RZ"]}],
        "frame_members":[
            {"id":"COL1","i_node":"B1","j_node":"T1","section_id":"S"},
            {"id":"COL2","i_node":"B2","j_node":"T2","section_id":"S"},
            {"id":"BEAM","i_node":"T1","j_node":"T2","section_id":"S"}],
        "diaphragms":[],"end_releases":[],"rigid_offsets":[],"shell_elements":[],
        "load_patterns":[],"load_cases":[],"joint_loads":[],"frame_loads":[],"area_loads":[],
        "mass_source":{},"nodal_masses":[]}
    nodes=[{"node_id":"T1","storey_id":"ROOF","x_m":0,"y_m":0,"z_m":3},
           {"node_id":"T2","storey_id":"ROOF","x_m":4,"y_m":0,"z_m":3}]
    sources=[
        {"id":"DL","source_key":"roof:DL","load_category":"DEAD",
         "downward_load_kN":100,"participation_factor":1,
         "node_shares":[{"node_id":"T1","fraction":.5},{"node_id":"T2","fraction":.5}]},
        {"id":"LL","source_key":"roof:LL:synthetic","load_category":"OTHER_LIVE",
         "downward_load_kN":30,"participation_factor":.3,
         "node_shares":[{"node_id":"T1","fraction":.5},{"node_id":"T2","fraction":.5}]}
    ]
    return m, allocate_loads_to_nodes(nodes,sources,9.81)


def test_assembly_binds_mass_without_mutating_model_and_matches_opensees():
    m,a=_fixture()
    bound=bind_assembly_to_canonical_model(m,a)
    assert m["nodal_masses"]==[]
    assert len(bound["nodal_masses"])==2
    assert bound["provenance"]["load_mass_assembly_sha256"]
    built=build_canonical_frame_model(bound)
    assert len(built.node_masses)==2
    actual=run_audited_static_gravity(m,a)
    assert actual["status"]=="ELASTIC_FRAME_GRAVITY_EQUILIBRIUM_PASS_NOT_DESIGN_APPROVAL"
    assert sum(r["Rz_kN"] for r in actual["support_reactions"])==pytest.approx(130,abs=1e-4)
    assert actual["equilibrium"]["status"]=="VERTICAL_GLOBAL_FORCE_AND_MOMENT_EQUILIBRIUM_PASS"


def test_assembly_blocks_preexisting_mass_and_coordinate_drift():
    m,a=_fixture()
    x=copy.deepcopy(m);x["nodes"][2]["x"]=.01
    with pytest.raises(LoadMassAdapterError,match="geometry drift"):
        bind_assembly_to_canonical_model(x,a)
    x=copy.deepcopy(m);x["nodal_masses"]=[{"node_id":"T1","mx":1,"my":1,"mz":1}]
    with pytest.raises(LoadMassAdapterError,match="existing nodal mass"):
        bind_assembly_to_canonical_model(x,a)
    x=copy.deepcopy(m);x["units"]["force"]="N"
    with pytest.raises(LoadMassAdapterError,match="units.force"):
        bind_assembly_to_canonical_model(x,a)
