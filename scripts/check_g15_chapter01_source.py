#!/usr/bin/env python3
"""Independent source-to-report gate: de-identified Chapter 1 evidence.

A reported source observation is not a verified physical-model input.
"""
from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    source=ROOT/"site/data/g15-chapter01-source-review.v0.1.json"
    d=json.loads(source.read_text(encoding="utf-8"))
    assert d["schema"]=="jp.structural.g15.chapter01.source_review.v0.1"
    assert d["source"]["sha256"]=="f122904444a2e2f75230d9d4e41da0093d050da25c6e8140c86d466b7e37cc52"
    a=d["acceptance"]; v=d["evidence"];g=d["acceptance_gates"]
    assert a["original_subsections"]==["1.1","1.2","1.3"]
    assert len(v)==a["source_records_reviewed"]==20
    assert len(g)==a["open_obligations"]==7 and a["accepted_obligations"]==0
    assert all(x["status"]=="OPEN" for x in g)
    assert not any(a[k] for k in ("chapter_engineering_accepted","source_geometry_verified",
      "original_ETABS_model_verified","physical_project_verified","engineering_approval"))
    assert a["source_F3_one_way_shear"]=="NOT SAFE IN ONE WAY SHEAR"
    assert sorted(set(x["section"] for x in v))==["1.1","1.2","1.3"]
    assert len({x["id"] for x in v})==len(v)
    for x in v:
        assert x["status"] in {"SOURCE_REPORTED","SOURCE_REPORTED_UNVERIFIED","SOURCE_CONFLICT",
          "CURRENT_ENGINE_RESULT","ENGINEERING_HOLD"}
        assert all(isinstance(x[k],str) and len(x[k].strip())>4 for k in
                   ("field","value","citation","uncertainty"))
    assert sum(x["status"]=="SOURCE_CONFLICT" for x in v)>=3
    assert any("Kathmandu" in x["value"] for x in v) and any("Pokhara" in x["value"] for x in v)
    assert any("14 in" in x["value"] for x in v)
    assert not any(x["status"]=="VERIFIED_ORIGINAL_MODEL" for x in v)
    page=(ROOT/"site/report.html").read_text(encoding="utf-8")
    assert page.index('id="toc-1-1"')<page.index('id="toc-1-2"')<page.index('id="toc-1-3"')
    for anchor in ("c01-executive","c01-modelling","c01-structure","chapter-01-gates"):
        assert page.count('id="'+anchor+'"')==1
    assert page.count("NOT SAFE IN ONE WAY SHEAR")>=2
    assert "g15-chapter01-source-review.v0.1.json" in page
    assert "0 of 7 acceptance requirements" in page
    assert 'id="chapter-02"' in page and 'id="report-contents"' in page
    assert "data-guild-route=\"report\"" in page
    assert "OpenSees" in page
    forbidden=("Sankalpchhetri143","9867589749","83071 Civil","Name of the Structural Designer",
          "Name of the Counsulting Firm")
    public=page+dumps(d)
    assert not any(token in public for token in forbidden)
    return d

def dumps(d):
    return json.dumps(d,ensure_ascii=False,sort_keys=True)

if __name__=="__main__":
    result=check()
    print("G15_CHAPTER01_SOURCE_REVIEW_PASS",
          len(result["evidence"]),len(result["acceptance_gates"]),
          "GATES_OPEN_NO_ENGINEERING_APPROVAL")
