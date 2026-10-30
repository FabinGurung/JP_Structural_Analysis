"""R5.3 same-source in-span beam force and moment regression and hand benchmarks."""
import copy
import csv
import hashlib
import json
import math
from pathlib import Path

import pytest
from jp_structural.solvers.native.beam_span_diagrams import (
    SpanDiagramError,reconstruct_local_vertical_diagram,build_signed_span_diagrams
)
from scripts.build_r5_beam_span_diagrams import DEFAULT,PFX,build,emit

@pytest.fixture(scope="module")
def calculation():
    return build()

def test_closed_form_fixed_fixed_uniform_beam_shear_and_moments():
    # Independently derive fixed end values for L=4m, w=8kN/m.
    w=8.;L=4.
    result=reconstruct_local_vertical_diagram(length_m=L,
       left={"Vz":w*L/2,"My":-w*L*L/12},
       right={"Vz":w*L/2,"My":w*L*L/12},
       downward_uniform_kN_m=w,sample_divisions=16)
    assert result["end_equilibrium_pass"] is True
    assert result["sample_count"]==17
    assert result["zero_shear_inside_member_x_m"]==pytest.approx(2.)
    assert result["cut_left"]["My_kNm"]==pytest.approx(-10.6666666667)
    assert result["cut_right"]["My_kNm"]==pytest.approx(-10.6666666667)
    assert result["critical_moment_max"]["x_m"]==pytest.approx(2.)
    assert result["critical_moment_max"]["My_sagging_positive_kNm"]==pytest.approx(w*L*L/24)
    assert result["critical_moment_min"]["My_sagging_positive_kNm"]==pytest.approx(-w*L*L/12)
    assert result["samples"][8]["Vz_section_kN"]==pytest.approx(0.)

def test_simply_supported_uniform_beam_midspan_M_wL2_over8():
    w=12.;L=6.
    res=reconstruct_local_vertical_diagram(length_m=L,
       left={"Vz":w*L/2,"My":0.},
       right={"Vz":w*L/2,"My":0.},
       downward_uniform_kN_m=w,sample_divisions=12)
    assert res["critical_moment_max"]["My_sagging_positive_kNm"]==pytest.approx(w*L*L/8)
    assert res["critical_moment_max"]["x_m"]==pytest.approx(3)
    assert res["cut_right"]["My_kNm"]==pytest.approx(0)
    assert res["samples"][0]["Vz_section_kN"]==pytest.approx(36)
    assert res["samples"][-1]["Vz_section_kN"]==pytest.approx(-36)

def test_unsampled_interior_critical_station_is_inserted_exactly():
    out=reconstruct_local_vertical_diagram(length_m=4.,
       left={"Vz":10.,"My":-16.},right={"Vz":22.,"My":40.},
       downward_uniform_kN_m=8.,sample_divisions=8)
    # xstar=1.25 m is not a 0.5m sampling interval.
    assert out["zero_shear_inside_member_x_m"]==pytest.approx(1.25)
    assert out["sample_count"]==10
    assert any(x["x_m"]==pytest.approx(1.25) for x in out["samples"])

def test_fail_closed_for_incorrect_J_end_sign_or_spoofed_actions():
    base={"Vz":16.,"My":-32/3}
    end={"Vz":16.,"My":32/3}
    with pytest.raises(SpanDiagramError,match="cut/J-end equilibrium"):
        reconstruct_local_vertical_diagram(length_m=4,left=base,right={"Vz":16.,"My":-32/3},downward_uniform_kN_m=8)
    with pytest.raises(SpanDiagramError,match="cut/J-end equilibrium"):
        reconstruct_local_vertical_diagram(length_m=4,left=base,right={"Vz":15.,"My":32/3},downward_uniform_kN_m=8)
    with pytest.raises(SpanDiagramError,match="positive span"):
        reconstruct_local_vertical_diagram(length_m=0,left=base,right=end,downward_uniform_kN_m=8)
    with pytest.raises(SpanDiagramError,match="finite numeric"):
        reconstruct_local_vertical_diagram(length_m=4,left=base,right=end,downward_uniform_kN_m=float("nan"))
    with pytest.raises(SpanDiagramError,match="bounded integer"):
        reconstruct_local_vertical_diagram(length_m=4,left=base,right=end,downward_uniform_kN_m=8,sample_divisions=1)

def test_actual_signed_FE_case_and_combination_all_beam_end_residuals(calculation):
    d=calculation["source_audited_signed_beam_diagrams"]
    assert calculation["source_total_gravity_kN"]==128.
    assert calculation["source_seismic_weight_kN"]==pytest.approx(111.2)
    assert calculation["native_element_uniform_resultants_kN"]==32.
    assert d["source_member_count"]==4
    assert d["signed_case_count"]==3
    assert d["signed_combination_count"]==2
    assert d["diagram_record_count"]==20
    assert d["all_J_cut_boundary_equilibrium_pass"] is True
    assert len({(x["kind"],x["case_id"],x["member_id"]) for x in d["diagrams"]})==20
    assert all(x["diagram"]["engineering_approval"] is False for x in d["diagrams"])
    assert all(max(abs(v) for v in x["diagram"]["end_boundary_residuals"].values())<1e-5
               for x in d["diagrams"])
    assert any(x["kind"]=="RAW" and x["case_id"]=="DL" and x["member_id"]=="BM1"
               and x["downward_uniform_signed_kN_m"]==8 for x in d["diagrams"])
    assert all(len(x["diagram"]["samples"])>=17 for x in d["diagrams"])

def test_concurrent_combination_preserves_linear_diagram_load_intensities(calculation):
    rows=calculation["source_audited_signed_beam_diagrams"]["diagrams"]
    by={(r["kind"],r["case_id"],r["member_id"]):r for r in rows}
    for bm in ("BM1","BM2","BM3","BM4"):
        g=by["RAW","DL",bm];l=by["RAW","LL",bm];hx=by["RAW","HX",bm]
        plus=by["COMBINATION","U_PLUS",bm];minus=by["COMBINATION","U_MINUS",bm]
        assert plus["downward_uniform_signed_kN_m"]==pytest.approx(
            1.2*g["downward_uniform_signed_kN_m"]+1.5*l["downward_uniform_signed_kN_m"]+hx["downward_uniform_signed_kN_m"])
        assert minus["downward_uniform_signed_kN_m"]==pytest.approx(
            1.2*g["downward_uniform_signed_kN_m"]+1.5*l["downward_uniform_signed_kN_m"]-hx["downward_uniform_signed_kN_m"])
        for fraction in (0.,0.5,1.):
            L=plus["diagram"]["length_m"]
            x=L*fraction
            def val(row,axis):
                v=row["diagram"]["cut_left"]
                w=row["downward_uniform_signed_kN_m"]
                return (v["Vz_kN"]-w*x if axis=="Vz_section_kN"
                        else v["My_kNm"]+v["Vz_kN"]*x-w*x*x/2)
            for axis in ("Vz_section_kN","My_sagging_positive_kNm"):
                assert val(plus,axis)==pytest.approx(
                    1.2*val(g,axis)+1.5*val(l,axis)+val(hx,axis),abs=1e-5)

def test_reject_tampered_signed_digest_and_changed_factors(calculation):
    from scripts.build_r5_uniform_beam_case import build as baseline
    old=baseline()
    a=build_signed_span_diagrams(model=old["source_signed_case_model"],
       solved=old["signed_FE"],raw_cases=old["source_signed_raw_cases"],
       combinations=old["source_signed_combinations"])
    assert a["diagram_record_count"]==20
    signed=copy.deepcopy(old["signed_FE"])
    signed["raw_cases"][0]["local_end_resisting_actions"]["BM1"]["I"]["My"]+=2
    with pytest.raises(SpanDiagramError,match="tampered signed"):
        build_signed_span_diagrams(model=old["source_signed_case_model"],solved=signed,
          raw_cases=old["source_signed_raw_cases"],combinations=old["source_signed_combinations"])
    combos=copy.deepcopy(old["source_signed_combinations"])
    combos[0]["components"][0]["factor"]+=0.1
    with pytest.raises(SpanDiagramError,match="source signed action bundle digest"):
        build_signed_span_diagrams(model=old["source_signed_case_model"],solved=old["signed_FE"],
          raw_cases=old["source_signed_raw_cases"],combinations=combos)

def test_seven_chapter_original_SAR_and_original_F3_hold(calculation):
    assert calculation["schema"]=="jp.structural.r5.source_signed_beam_span_SAR.v0.3"
    assert [x["id"] for x in calculation["chapters"]]==[f"{i:02d}" for i in range(1,8)]
    assert {x["id"] for c in calculation["chapters"] for x in c["modules"]}=={
        *(f"M{i:02d}" for i in range(1,17)),"S17","S18"}
    assert calculation["original_F3_failure"]=="NOT SAFE IN ONE WAY SHEAR"
    assert calculation["original_building_certified"] is False
    assert calculation["shell_diaphragm_FE_completed"] is False
    assert calculation["engineering_approval"] is False

def test_report_html_svg_and_csv_manifest_are_reproducible(tmp_path):
    d=emit(DEFAULT,tmp_path)
    m=json.loads((tmp_path/(PFX+"-manifest.json")).read_text())
    assert len(m["files"])==4 and m["engineering_approval"] is False
    for k,h in m["files"].items():
        assert hashlib.sha256((tmp_path/k).read_bytes()).hexdigest()==h
    data=json.loads((tmp_path/(PFX+".json")).read_text())
    assert data["schema"]==d["schema"]
    html=(tmp_path/(PFX+".html")).read_text()
    assert "NOT ENGINEERING APPROVED" in html
    assert "<svg" in html and "Chapter 05" in html
    assert "NOT SAFE IN ONE WAY SHEAR" in html
    stations=list(csv.DictReader((tmp_path/(PFX+"-stations.csv")).open()))
    assert len(stations)>=20*17
    assert len(list(csv.DictReader((tmp_path/(PFX+"-extrema.csv")).open())))==20
    site=(Path(__file__).resolve().parents[1]/"site/report.html").read_text()
    assert 'id="annex-r5-span-diagrams"' in site
    assert "reports/r5-beam-span-diagrams.html" in site
