"""Fully synthetic, source-labelled two-column frame for D2 regression reports.

All dimensions and actions were assumed deliberately; not a client structure.
Five nodes, two fixed columns, two beam segments, six-DOF nodal actions.
"""
from __future__ import annotations
import math


def case_fixture():
    fixed = ["UX", "UY", "UZ", "RX", "RY", "RZ"]
    nodes = [
        {"id":"B1","storey_id":"BASE","x":0., "y":0., "z":0.},
        {"id":"B2","storey_id":"BASE","x":4., "y":0., "z":0.},
        {"id":"T1","storey_id":"ROOF","x":0., "y":0., "z":3.},
        {"id":"TM","storey_id":"ROOF","x":2., "y":0., "z":3.},
        {"id":"T2","storey_id":"ROOF","x":4., "y":0., "z":3.},
    ]
    model = {
        "schema_version":"0.1","model_id":"SYNTHETIC-D2-FRAME-001",
        "project":{"project_id":"SYNTHETIC-NOT-CLIENT"},
        "units":{"force":"kN","length":"m","time":"s","mass":"kN*s^2/m"},
        "design_basis":{"code":"SANITIZED_TEST","damping_ratio":0.05},
        "source_references":[{"id":"SYNTHETIC-D2","source_type":"SYNTHETIC_TEST"}],
        "storeys":[{"id":"BASE","elevation":0},{"id":"ROOF","elevation":3}],
        "nodes":nodes,
        "materials":[{"id":"CONC","E":25_000_000.0,"poisson":.2}],
        "sections":[
            {"id":"COL-S","material_id":"CONC","shape":"Rectangular","width":.4,"depth":.5},
            {"id":"BEAM-S","material_id":"CONC","shape":"Rectangular","width":.3,"depth":.45},
        ],
        "supports":[
            {"id":"F1","node_id":"B1","restrained_dofs":fixed},
            {"id":"F2","node_id":"B2","restrained_dofs":fixed},
        ],
        "frame_members":[
            {"id":"COL1","i_node":"B1","j_node":"T1","section_id":"COL-S","member_type":"COLUMN"},
            {"id":"COL2","i_node":"B2","j_node":"T2","section_id":"COL-S","member_type":"COLUMN"},
            {"id":"BM1","i_node":"T1","j_node":"TM","section_id":"BEAM-S","member_type":"BEAM"},
            {"id":"BM2","i_node":"TM","j_node":"T2","section_id":"BEAM-S","member_type":"BEAM"},
        ],
        "diaphragms":[],"end_releases":[],"rigid_offsets":[],"shell_elements":[],
        "joint_loads":[],"frame_loads":[],"area_loads":[],
        "load_patterns":[],"load_cases":[],"load_combinations":[],
        "mass_source":{},"nodal_masses":[],
    }
    def load(n, **kwargs):
        row = {"node_id":n}
        row.update({key:kwargs.get(key,0.0) for key in
            ("Fx_kN","Fy_kN","Fz_kN","Mx_kNm","My_kNm","Mz_kNm")})
        return row
    cases = [
        {"case_id":"G","source_id":"ASSUMED_GRAVITY_D2",
         "nodal_loads":[load("T1",Fz_kN=-260),load("TM",Fz_kN=-100),
                         load("T2",Fz_kN=-260)]},
        {"case_id":"HX","source_id":"ASSUMED_LATERAL_PLUS_X_D2",
         "nodal_loads":[load("T1",Fx_kN=50),load("TM",Fx_kN=25),
                         load("T2",Fx_kN=50)]},
    ]
    combinations = [
        {"combination_id":"U_PLUS","source_id":"EXPLICIT_ASSUMED_1P2_G_PLUS_HX",
         "components":[{"case_id":"G","factor":1.2},{"case_id":"HX","factor":1.2}]},
        {"combination_id":"U_MINUS","source_id":"EXPLICIT_ASSUMED_1P2_G_MINUS_HX",
         "components":[{"case_id":"G","factor":1.2},{"case_id":"HX","factor":-1.2}]},
    ]
    diameter = 25.0
    area=math.pi * diameter**2 / 4
    bars=[{"x_mm":x,"y_mm":y,"area_mm2":area}
          for x,y in ((50,50),(200,50),(350,50),(50,450),
                      (200,450),(350,450),(50,250),(350,250))]
    beam = [{
        "member_id":"BM1","source_id":"ASSUMED_BEAM_D2",
        "combination_ids":["U_PLUS","U_MINUS"],"gravity_case_id":"G",
        "shear_component":"Vy","strength_source_id":"ASSUMED_HINGE_STRENGTHS_D2",
        "strengths_kNm":{"right_I":200,"right_J":200,"left_I":200,"left_J":200},
    }]
    column=[{
        "member_id":"COL1","source_id":"SYNTHETIC_FE415_8D25_COLUMN_D2",
        "combination_ids":["U_PLUS","U_MINUS"],
        "moment_component_mapping":{"Mux":"Mz","Muy":"My"},
        "section":{"width_mm":400,"depth_mm":500,"fck_MPa":25,
                   "fy_MPa":415,"bars":bars,"clear_height_mm":3000,
                   "effective_length_x_mm":3000,"effective_length_y_mm":3000},
    }]
    joint=[{
        "joint_node_id":"T1","beam_member_id":"BM1",
        "column_member_id":"COL1","column_end":"J","shear_component":"Vz",
        "combination_ids":["U_PLUS","U_MINUS"],
        "source_id":"ASSUMED_JOINT_GEOMETRY_AND_STEEL_D2",
        "joint":{"confinement_faces":"THREE","framing":"INTERIOR",
                 "fck_MPa":25,"fy_MPa":415,"joint_breadth_mm":400,
                 "joint_width_mm":400,"Ast_top_mm2":804,"Ast_bottom_mm2":603},
    }]
    return model,cases,combinations,beam,column,joint
