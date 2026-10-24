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
 assert "6 chapters + annex" in html
 assert "2.0 General Data for Structural Analysis" in html

def test_report_chapters_are_clean_and_experiments_preserved_in_more():
 html=(SITE/"report.html").read_text()
 more=(SITE/"more.html").read_text()
 for id in ("m09-report-case","d2-trace","gate05-report","gate06-report","gate21-report-engine"):
  assert ('id="'+id+'"') not in html
  assert more.count('id="'+id+'"')==1, "R&D evidence missing or duplicated: "+id
 assert 'id="guide-rd-shelf"' in more
 assert 'id="chapter-01-input-check"' in html
 assert 'data-m09-view="more"' in more
 assert 'data-d2-view="more"' in more
 assert "F3" in html and "NOT SAFE IN ONE WAY SHEAR" in html
 assert "reports/g15-gate21-calculation-report.html" in html
 assert "g15-3d.html" in html

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


def test_original_pdf_table_of_contents_and_simplified_navigation():
 from html.parser import HTMLParser
 html=(SITE/"report.html").read_text()
 parsed=Inspect();parsed.feed(html)
 sections=["toc-1-1","toc-1-2","toc-1-3","toc-2-1","toc-2-2","toc-2-3","toc-2-4","toc-2-5","toc-2-6","toc-2-6-1","toc-2-6-2","toc-2-6-3","toc-2-6-4","toc-2-6-5","toc-2-7","toc-2-8","toc-4-1","toc-4-2","toc-4-2-1","toc-4-2-2","toc-5-1","toc-5-2","toc-5-3","toc-5-4","toc-5-5","toc-5-6","toc-5-7","toc-5-8","toc-5-9","toc-5-10","toc-5-11","toc-5-12","toc-5-13","toc-5-14","toc-6-1","toc-6-2","toc-6-3","toc-6-4","toc-6-5"]
 assert all(i in parsed.ids for i in sections)
 assert len(sections)==len(set(sections))
 order=[parsed.ids.index("chapter-"+str(i).zfill(2)) for i in range(1,8)]
 assert order==sorted(order)
 assert 'id="report-contents"' in html and 'rb-original-toc' in html
 assert "Original report" in html or "original report" in html
 for p in ("index.html","report.html","more.html","project-lab.html","analysis-studio.html","g15-3d.html","calculation-coverage.html"):
  page=(SITE/p).read_text()
  nav=page.split('<nav class="navigation" aria-label="Primary navigation">',1)[1].split("</nav>",1)[0]
  for expected in ("index.html","report.html","more.html"):assert 'href="'+expected+'"' in nav
  for hidden in ("project-lab.html","g15-3d.html","analysis-studio.html","calculation-coverage.html"):assert 'href="'+hidden+'"' not in nav
