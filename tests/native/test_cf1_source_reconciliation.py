from scripts.reconcile_cf1_source import build
def test_cf1_report_load_centroid_reconstructed_without_misleading_certification():
    a=build();r=a["results"]
    assert a["engineering_approval"] is False
    assert a["source"]["stated_total_load_including_self_weight_kN"]==501
    assert r["total_service_kN"]==501
    assert r["service_q_min_kPa"]>0
    assert r["service_q_max_kPa"]<160
    assert r["max_positive_moment_kNm_total"]>280
    assert abs(r["service_force_equilibrium_residual_kN"])<1e-8
    assert abs(r["service_moment_equilibrium_residual_kNm"])<1e-8
    assert not r["combined_footing_shear_punching_verified"]
