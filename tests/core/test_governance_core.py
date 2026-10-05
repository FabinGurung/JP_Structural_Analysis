from pathlib import Path
from tempfile import TemporaryDirectory

from jp_structural.ingestion.source_inventory import inventory_file
from jp_structural.model.ids import stable_id
from jp_structural.qa.pre_solve import run_pre_solve_qa


def test_stable_id_is_deterministic_and_opaque():
    a=stable_id("NOD","private-display-label")
    b=stable_id("NOD","private-display-label")
    assert a==b and a.startswith("NOD-")
    assert "private" not in a.lower()


def test_source_inventory_hashes_bytes():
    with TemporaryDirectory() as d:
        p=Path(d)/"model.e2k"; p.write_bytes(b"abc")
        inv=inventory_file(p,source_origin="test",authority_role="fixture",classification="sanitized")
        assert inv["sha256"]=="ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
        assert inv["file_id"].startswith("SRC-")


def test_pre_solve_qa_fails_closed_on_unresolved_design_basis():
    model={"units":{"force":"N","length":"mm"},"nodes":[],"materials":[],"sections":[],"load_patterns":[],"mass_source":{}}
    out=run_pre_solve_qa(model)
    assert out["status"]=="UNRESOLVED"
    assert out["blocking"] is True
