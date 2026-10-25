from scripts.check_g15_chapter01_source import check
def test_chapter1_original_source_and_acceptance_gates():
 d=check()
 assert d["acceptance"]["accepted_obligations"]==0
 assert d["acceptance"]["chapter_engineering_accepted"] is False

def test_issues_are_reported_not_silently_corrected():
 d=check()
 conf={r["field"]:r for r in d["evidence"] if r["status"]=="SOURCE_CONFLICT"}
 assert "Building occupancy" in conf
 assert "Seismic zone reference" in conf
 assert "Listed column width" in conf
 assert "Referenced seismic code" in conf
 assert any(r["status"]=="CURRENT_ENGINE_RESULT" for r in d["evidence"])
 assert all(r["citation"] for r in d["evidence"])

def test_source_narrative_and_solver_narrative_have_distinct_roles():
 d=check()
 text=__import__("pathlib").Path(__file__).resolve().parents[1].joinpath("site/report.html").read_text()
 assert "What the original report says:" in text
 assert "Our reproducible method:" in text
 assert "response-spectrum methods" in text or "response-spectrum analysis" in text
 assert "§§1.1–1.3" in text
 assert "0 of 7 acceptance requirements" in text
