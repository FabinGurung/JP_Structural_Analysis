import pytest
from jp_structural.qa.nbc_code_basis import CodeBasisError, validate_code_basis

def candidate():
    return {"calculation_scope":"NEW_ENGINEERED_ANALYSIS",
            "code_set":{"NBC 105":"2025","NBC 206":"2024"},
            "source_references":{"NBC 105":"https://dudbc.gov.np/pages/building-code/",
                                "NBC 206":"https://ebps.kathmandu.gov.np/UploadFiles/NBC206Amended.pdf"},
            "registered_code_clauses":[]}

def test_current_source_identity_passes_without_design_claim():
    out=validate_code_basis(candidate())
    assert out["status"]=="CODE_EDITION_IDENTITIES_PASS_ONLY"
    assert out["code_compliance"]=="NOT_EVALUATED"
    assert out["verified_clause_values"]==0

@pytest.mark.parametrize(("code","edition"),[("NBC 105","2020"),("NBC 206","2003"),("NBC 206","2015")])
def test_old_editions_fail_for_new_analysis(code,edition):
    r=candidate();r["code_set"][code]=edition
    with pytest.raises(CodeBasisError):
        validate_code_basis(r)

def test_no_raw_source_reference_no_acceptance():
    r=candidate();del r["source_references"]["NBC 105"]
    with pytest.raises(CodeBasisError):validate_code_basis(r)

def test_nbc205_compatibility_gate():
    r=candidate()
    r["code_set"]["NBC 205"]="2024"
    r["source_references"]["NBC 205"]="https://dudbc.gov.np/content/13279/nepal-national-building-code-nbc-205--2024/"
    with pytest.raises(CodeBasisError):validate_code_basis(r)

def test_future_code_clause_cannot_cross_editions():
    r=candidate()
    r["registered_code_clauses"]=[{"code":"NBC 105","edition":"2020","clause":"5","source_file_or_url":"provider"}]
    with pytest.raises(CodeBasisError):validate_code_basis(r)
