"""Fail CI on obvious private/source-file publication hazards."""
from __future__ import annotations
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BLOCKED_SUFFIXES={".edb",".e2k",".s2k",".pfx",".p12",".key"}
SECRET_PATTERNS=[
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"ghp_[A-Za-z0-9]{30,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{30,}"),
]
ALLOW_E2K_FIXTURE_PATHS={"tests/ingestion/test_e2k_inventory.py","tests/normalization/test_e2k_normalizer.py"}

problems=[]
for p in ROOT.rglob("*"):
    if not p.is_file() or ".git" in p.parts:
        continue
    rel=p.relative_to(ROOT).as_posix()
    if p.suffix.lower() in BLOCKED_SUFFIXES and rel not in ALLOW_E2K_FIXTURE_PATHS:
        problems.append(f"blocked source-like file extension: {rel}")
    if p.stat().st_size > 2_000_000:
        continue
    try: text=p.read_text(encoding="utf-8")
    except UnicodeDecodeError: continue
    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            problems.append(f"secret-like content: {rel}")

if problems:
    raise SystemExit("\n".join(problems))
print("public-data safety scan: PASS")
