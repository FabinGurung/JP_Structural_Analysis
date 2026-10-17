"""Strict NBC edition routing. DOES NOT implement code requirements or certify design."""
from __future__ import annotations
from collections.abc import Mapping

LATEST_VERIFIED = {"NBC 105": "2025", "NBC 205": "2024", "NBC 206": "2024"}
NEW_SEISMIC_SCOPE = "NEW_ENGINEERED_ANALYSIS"

class CodeBasisError(ValueError):
    pass

def validate_code_basis(run: Mapping[str, object]) -> dict[str, object]:
    """Check source identities and cross-edition gates; no numerical design rule admitted."""
    if not isinstance(run, Mapping):
        raise CodeBasisError("run basis must be mapping")
    scope = run.get("calculation_scope")
    if scope not in (NEW_SEISMIC_SCOPE, "HISTORICAL_REPORT_RECONCILIATION", "RUD_CANDIDATE_HOLD"):
        raise CodeBasisError("calculation_scope must be explicit")
    codes=run.get("code_set")
    refs=run.get("source_references")
    if not isinstance(codes, Mapping) or not isinstance(refs, Mapping):
        raise CodeBasisError("code_set and source_references are required")
    if codes.get("NBC 105") != "2025" and scope==NEW_SEISMIC_SCOPE:
        raise CodeBasisError("new seismic analysis must identify NBC 105:2025")
    if not codes:
        raise CodeBasisError("no code editions identified")
    for code, edition in codes.items():
        if not isinstance(code,str) or not isinstance(edition,str) or not edition.strip():
            raise CodeBasisError("malformed code / edition")
        if code in LATEST_VERIFIED and scope==NEW_SEISMIC_SCOPE and LATEST_VERIFIED[code]!=edition:
            raise CodeBasisError(f"{code} edition is not the verified current selection")
        if not isinstance(refs.get(code),str) or not refs[code].strip():
            raise CodeBasisError(f"missing source identity: {code}")
    if "NBC 205" in codes and scope==NEW_SEISMIC_SCOPE:
        raise CodeBasisError("NBC 205:2024 RUD (based on NBC105:2020) requires a separate eligibility/cross-edition engineering reconciliation")
    clauses=run.get("registered_code_clauses",[])
    if not isinstance(clauses,list):
        raise CodeBasisError("registered_code_clauses must be array")
    for row in clauses:
        if not isinstance(row,Mapping) or not all(isinstance(row.get(k),str) and row[k].strip() for k in ("code","edition","clause","source_file_or_url")):
            raise CodeBasisError("clause requires exact code, edition, clause, provider URL")
        if row["code"] not in codes or row["edition"] != codes[row["code"]]:
            raise CodeBasisError("clause edition is not consistent with selection")
    return {"status":"CODE_EDITION_IDENTITIES_PASS_ONLY",
            "calculation_scope":scope,
            "code_editions":dict(sorted(codes.items())),
            "code_compliance":"NOT_EVALUATED",
            "engineer_signoff":"NOT_EVALUATED",
            "verified_clause_values":0}
