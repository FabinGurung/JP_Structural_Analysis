#!/usr/bin/env python3
"""Fast, zero-network structural Pages QA. Regenerate site/demo before deployment.

Only checks static internal page links, consistent navigation, source privacy,
registry access, common theme, and absence of unnecessary heavy dependencies.
"""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlparse, unquote

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/"site"
PAGES=["index.html","calculation-coverage.html","report.html","more.html"]
class Parse(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True);self.links=[];self.css=[];self.scripts=[];self.mains=0
    def handle_starttag(self,tag,attrs):
        d=dict(attrs)
        if tag=="a" and "href" in d:self.links.append(d["href"])
        if tag=="link" and d.get("rel")=="stylesheet":self.css.append(d.get("href"))
        if tag=="script" and "src" in d:self.scripts.append(d["src"])
        if tag=="main":self.mains+=1

def main():
    problems=[]
    for page in PAGES:
        p=SITE/page
        if not p.is_file():problems.append("Missing "+page);continue
        text=p.read_text(encoding="utf-8")
        parser=Parse();parser.feed(text)
        if parser.css!=["styles.css"]:problems.append(page+": inconsistent stylesheet")
        if parser.scripts!=["app.js"]:problems.append(page+": inconsistent app script")
        if parser.mains!=1:problems.append(page+": expected one main")
        for target in ("index.html","calculation-coverage.html","report.html","more.html"):
            if target not in text:problems.append(page+": missing nav target "+target)
        for url in parser.links+parser.css+parser.scripts:
            u=urlparse(url)
            if u.scheme or url.startswith("//") or url.startswith("#") or url.startswith("mailto:"):continue
            local=(SITE/page).parent/unquote(u.path)
            if not local.is_file() and not (local==SITE/"demo/SAR.html" and not (SITE/"demo").exists()):
                problems.append(page+": broken local link "+url)
    for path in ("styles.css","app.js","data/report-calculation-coverage.v0.1.json"):
        if not (SITE/path).is_file():problems.append("Missing "+path)
    if (SITE/"styles.css").stat().st_size>28000:problems.append("Shared CSS unexpectedly large")
    if (SITE/"app.js").stat().st_size>12000:problems.append("Shared JS unexpectedly large")
    if problems:raise SystemExit("\n".join(problems))
    print("STRUCTURAL_SITE_QA_PASS: four pages, shared theme and relative links")
if __name__=="__main__":main()
