"""Feynman-style More guide: one-page explanation of verified workflow and limits."""
from html.parser import HTMLParser
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/"site"
LESSONS=("guide-map","guide-3d","guide-run","guide-lab","guide-skills","guide-machines")

class Parse(HTMLParser):
 def __init__(self):
  super().__init__();self.ids=[];self.links=[];self.css=[];self.mains=0;self.details=0
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if "id" in a:self.ids.append(a["id"])
  if tag=="a" and "href" in a:self.links.append(a["href"])
  if tag=="link" and a.get("rel")=="stylesheet":self.css.append(a.get("href"))
  if tag=="main":self.mains+=1
  if tag=="details":self.details+=1

def test_more_is_self_contained_learning_guide():
 h=(SITE/"more.html").read_text(encoding="utf-8")
 p=Parse();p.feed(h)
 assert p.mains==1
 assert "How our structural engineering" in h
 assert all(x in p.ids for x in LESSONS)
 assert [p.ids.index(x) for x in LESSONS]==sorted(p.ids.index(x) for x in LESSONS)
 assert len(p.ids)==len(set(p.ids))
 assert p.details>=8
 assert p.css==["styles.css","more-guide.css"]
 assert (SITE/"more-guide.css").is_file()
 assert "guide-glossary" in p.ids and "guide-selftest" in p.ids

def test_learnings_are_grounded_and_dont_claim_structural_approval():
 h=(SITE/"more.html").read_text(encoding="utf-8")
 for s in ("23","92","165","825","816","15","18","5","0","NOT SAFE IN ONE WAY SHEAR",
           "OpenSees","GitHub Actions","GitHub Pages","3D Structural Studio",
           "Project Lab","Calculation Coverage","Sanitized two-span beam",
           "Fe","Assumption"):
  if s=="Fe":continue
  assert s.lower() in h.lower(),s
 assert "teaching numbers" in h
 assert "not" in h.lower()
 assert h.index("guide-resources")>h.index("guide-selftest")
 assert "guide-caution" in h
 assert h.count('<a href="g15-3d.html"')==1
 assert h.count('<a href="analysis-studio.html"')==1
 assert h.count('<a href="project-lab.html"')==1

def test_in_page_figures_and_question_prompts():
 h=(SITE/"more.html").read_text(encoding="utf-8")
 assert h.count("<figure")>=4
 assert h.count('<details class="guide-check">')>=10
 assert "guide-skill-grid" in h
 assert "0.10 × 300 = 30 kN" in h
 assert "GitHub stores the instructions" in h
 assert "CSS" not in h[:500]
 assert 'id="guide-resources"' in h

def test_primary_navigation_remains_only_home_report_more():
 h=(SITE/"more.html").read_text()
 nav=h.split('<nav class="navigation" aria-label="Primary navigation">',1)[1].split("</nav>",1)[0]
 for f in ("index.html","report.html","more.html"):assert 'href="'+f+'"' in nav
 for old in ("g15-3d.html","project-lab.html","analysis-studio.html","calculation-coverage.html"):
  assert 'href="'+old+'"' not in nav
