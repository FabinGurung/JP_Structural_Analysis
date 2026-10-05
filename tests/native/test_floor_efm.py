from jp_structural.solvers.native.floor_efm import lateral_distribution, span_positive_and_reactions, support_face_negative


def test_floor01_lateral_distribution_identity():
    out = lateral_distribution(100.0, 60.0, 0.85)
    assert out["column_strip_moment_ft_kip"] == 60.0
    assert out["beam_strip_moment_ft_kip"] == 51.0
    assert out["column_strip_remainder_ft_kip"] == 9.0
    assert out["two_half_middle_strips_moment_ft_kip"] == 40.0


def test_positive_span_reaction_equilibrium_identity():
    w, L, ml, mr = 2.0, 20.0, 30.0, 20.0
    out = span_positive_and_reactions(w, L, ml, mr)
    assert abs(out["VL_kip"] + out["VR_kip"] - w * L) < 1e-12
    assert support_face_negative(ml, out["VL_kip"], w, 0.75) < ml
