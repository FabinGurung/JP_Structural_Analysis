"""A single synced solver explanation, safe visual fallback and ETABS/DB source linking."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def test_all_views_and_provenance_inputs():
 h=(ROOT/"site/more.html").read_text()
 for v in ("guide-fem-triad","fem-three","fem-svg","fem-numbers",
           "fem-manual-i","fem-manual-u","fem-manual-m","guide-etabs-workflow",
           "guide-data-design","guide-code-library","fem-code-rows"):
  assert h.count('id="'+v+'"')==1,v
 assert h.count('data-fem-part=')>=5
 assert "Three.js" in h and "SVG" in h and "NOT" in h
 assert "not recovered truths about our G+1.5 building" in h
def test_js_uses_genuine_numeric_payload_and_threejs_fallback():
 s=(ROOT/"site/fem-triad.js").read_text()
 for v in ("opensees-cantilever-learning.v0.1.json","fem-workflow-map.v0.1.json",
          "nbc105-verified-rule-inventory.v0.1.json","engineering_approval!==false",
          "project_model_used!==false","independent_hand","setAttribute","Three.js","await import","catch(e)"):
  assert v in s,v
 assert (ROOT/"site/more-guide.css").read_text().count("guide-fem-two")>=2
def test_chapter2_retains_ambiguous_inputs_and_original_report_chapters():
 s=(ROOT/"site/report.html").read_text()
 a=s.index('id="chapter-02"');b=s.index('id="chapter-03"')
 assert 'id="chapter-02-input-provenance"' in s[a:b]
 assert "more.html#guide-fem-triad" in s[a:b]
 assert "NOT VERIFIED" in s[a:b]
 assert 'id="chapter-01"' in s and 'id="chapter-06"' in s
 assert "NOT SAFE IN ONE WAY SHEAR" in s
