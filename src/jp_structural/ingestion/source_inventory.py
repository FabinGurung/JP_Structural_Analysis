"""Source inventory and hashing utilities."""
from __future__ import annotations
import hashlib, mimetypes
from datetime import date
from pathlib import Path
from typing import Any
from jp_structural.model.ids import stable_id

def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024*1024), b""): h.update(chunk)
    return h.hexdigest()

def inventory_file(path: Path, *, source_origin: str, authority_role: str, classification: str="private", parser: str|None=None, parser_version: str|None=None, received_date: str|None=None) -> dict[str,Any]:
    resolved=path.resolve(); stat=resolved.stat(); digest=sha256_file(resolved)
    return {"file_id":stable_id("SRC",digest),"original_filename":path.name,"file_type":mimetypes.guess_type(path.name)[0] or "application/octet-stream","size_bytes":stat.st_size,"sha256":digest,"source_origin":source_origin,"received_date":received_date or date.today().isoformat(),"authority_role":authority_role,"classification":classification,"parser":parser,"parser_version":parser_version,"ingestion_status":"INVENTORIED"}
