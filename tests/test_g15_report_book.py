"""Continuous-scroll report book preserves all original engine components.

This test checks the public HTML structure and browser integration independently
from calculations. The source/solver checks remain in existing Gate21 QA.
"""
from html.parser import HTMLParser
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/"site"

class Inspect(HTMLParser):
 def __init__(self):
  super().__init__();self.ids=[];self.links=[];self.scripts=[]
 def handle_starttag(self,tag,attrs):
  d=dict(attrs)
  if "id" in d:self.ids.append(d["id"])
  if tag=="a" and "href" in d:self.links.append(d["href"])
  if tag=="script" and "src" in d:self.scripts.append(d["src"])

def test_report_is_one_continuous_chaptered_document():
 html=(SITE/"report.html").read_text()
 s=Inspect();s.feed(html)
 assert s.ids.index("report-top")<s.ids.index("report-contents")
 numbers=[f"chapter-{i:02d}" for i in range(1,8)]
 assert all(x in s.ids for x in numbers)
 assert [s.ids.index(i) for i in numbers]==sorted(s.ids.index(i) for i in numbers)
 assert len(s.ids)==len(set(s.ids))
 assert len([x for x in s.links if x.startswith("#chapter-")])>=7
 assert "report-book.js" in s.scripts
 assert (SITE/"report-book.css").is_file()
 assert html.count('class="rb-chapter"')==7

def test_previous_report_evidence_and_navigation_retained():
 html=(SITE/"report.html").read_text()
 s=Inspect();s.feed(html)
 for id in ("m09-report-case","d2-trace","gate05-report","gate06-report","gate21-report-engine"):
  assert id in s.ids, "Legacy source evidence removed: "+id
 for token in ('data-m09-view="report"','data-d2-view="report"',
  'data-sp16-benchmark="report"','data-gate05-demo="report"',
  'data-gate06-demo="report"','F3','NOT SAFE IN ONE WAY SHEAR'):
  assert token in html
 for path in ("g15-3d.html","project-lab.html#lab-gate20","reports/g15-gate21-calculation-report.html"):
  assert path in html

def test_all_chapters_have_internal_links_and_machine_data_checks():
 html=(SITE/"report.html").read_text()
 script=(SITE/"report-book.js").read_text()
 for i in range(1,8):
  assert f'id="chapter-{i:02d}"' in html
  assert f'href="#chapter-{i:02d}"' in html
 assert "reports/g15-gate21-report.v0.1.json" in script
 for flag in ('engineering_approval!==false','F3_verdict!=="NOT SAFE IN ONE WAY SHEAR"',
  'model_ETABS_source_verified!==false','signed_end_action_count!==825','source_gates_open!==15'):
  assert flag in script
 assert "IntersectionObserver" in script
 assert "textContent" in script

def test_report_export_print_and_source_privacy():
 html=(SITE/"report.html").read_text()
 assert 'id="rb-print"' in html
 assert 'data-guild-route="report"' in html
 assert "Original revised" in html
 assert "OpenSeesPy" in html
 assert "Original report" in html or "original report" in html
 assert '<img src="https://drive.google.com/' not in html
 assert "source-reported" in html.lower()
