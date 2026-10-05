import numpy as np

from jp_structural.solvers.native.direct_stiffness import solve_frame


def test_dsf01_l_frame_regression():
    nodes = {
        "A": {"x": 0.0, "y": 0.0, "restraints": {"ux": True, "uy": True, "rz": True}},
        "B": {"x": 0.0, "y": 3000.0, "restraints": {"ux": False, "uy": False, "rz": False}},
        "C": {"x": 4000.0, "y": 3000.0, "restraints": {"ux": False, "uy": False, "rz": False}},
    }
    members = [
        {"id": "AB", "i": "A", "j": "B", "E": 200000.0, "A": 10000.0, "I": 100000000.0},
        {"id": "BC", "i": "B", "j": "C", "E": 200000.0, "A": 10000.0, "I": 100000000.0},
    ]
    solved = solve_frame(nodes, members, [{"node": "C", "Fx": 10000.0, "Fy": -20000.0, "Mz": 0.0}])
    node_index = {nid: i for i, nid in enumerate(solved["node_ids"])}
    def dofs(nid):
        i = 3 * node_index[nid]
        return solved["U"][i:i+3]
    np.testing.assert_allclose(dofs("B"), [22.5, -0.03, -0.01425], atol=3e-12, rtol=0)
    np.testing.assert_allclose(dofs("C"), [22.52, -78.36333333333333, -0.02225], atol=3e-12, rtol=0)
    np.testing.assert_allclose(solved["R"][:3], [-10000.0, 20000.0, 110000000.0], atol=1e-5, rtol=0)
    assert np.allclose(solved["K"], solved["K"].T)
    assert np.all(np.linalg.eigvalsh(solved["Kff"]) > 0)
