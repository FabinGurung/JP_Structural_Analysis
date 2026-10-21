"""Private 3D service safety checks. Never bundle confidential model or secrets."""
import importlib.util
import pathlib
import pytest

ROOT=pathlib.Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location("g15_secure_api",ROOT/"secure-studio"/"api.py")
api=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(api)

def test_default_private_api_fails_closed(monkeypatch):
    monkeypatch.delenv("JP_STUDIO_SERVER_TOKEN",raising=False)
    monkeypatch.delenv("JP_G15_PRIVATE_ZIP_PATH",raising=False)
    with pytest.raises(Exception):
        api.access("Bearer testing")
    assert api.source_path() is None

def test_strict_client_edit_schema():
    obj=api.Scenario.model_validate({"beam_width_mm":315,"wall_proxy":True})
    assert obj.beam_width_mm==315
    assert obj.bridges is True
    assert obj.footprint_proxy=="COLUMN_CONVEX_HULL"
    with pytest.raises(Exception):
        api.Scenario.model_validate({"source_path":"/etc/passwd"})
    with pytest.raises(Exception):
        api.Scenario.model_validate({"beam_width_mm":100})

def test_no_optional_auth_leak_in_static_files():
    for path in ["index.html","studio.js","studio.css"]:
        text=(ROOT/"secure-studio"/path).read_text(encoding="utf-8")
        assert "PRIVATE_ZIP_SHA" not in text
        assert "JP_STUDIO_SERVER_TOKEN" not in text
    backend=(ROOT/"secure-studio"/"api.py").read_text(encoding="utf-8")
    assert 'hashlib.sha256' in backend
    assert 'check' not in str(api.source_path()) or api.source_path() is None
