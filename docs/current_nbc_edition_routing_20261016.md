# Verified current NBC code-basis routing (2026-10-16)

**Candidate on post-Seq9 feature branch. This is not part of the frozen A9 Seq9 release.**

## Authoritative government catalogue

- NBC 105:2025 (second revision): https://dudbc.gov.np/pages/building-code/
- NBC 205:2024 (RUD for eligible low-rise RC without masonry infill): https://dudbc.gov.np/content/13279/nepal-national-building-code-nbc-205--2024/
- NBC 206:2024 (architectural): https://dudbc.gov.np/content/13278/nepali-national-building-code-nbc-206--2024/
- NBC 206:2024 full PDF independently accessible from Kathmandu eBPS: https://ebps.kathmandu.gov.np/UploadFiles/NBC206Amended.pdf

NBC 103/104/106/108/110 are catalogued; existing government PDFs in the private source Drive bear 1994 edition covers. **No later dated version of those five has been independently verified in this run.** Never invent a revision year.

The private source authority contains full existing source text/page/QA extraction packages for NBC105:2025, NBC205:2024 and NBC103:1994; the remaining four older texts have raw text-layer JSONL and 206:2024 has a source-aligned government PDF online section index. Resolve these against the existing Drive code index, not by copying proprietary/legal source documents into public Git.

### Strict block
NBC205:2024 itself states that its RUD configurations were designed against NBC105:2020. Therefore never assume an NBC205:2024 RUD design is automatically reconciled to NBC105:2025. The engine code-basis validator rejects automatic admission to an engineered seismic analysis. It only validates code identities/evidence references, NOT seismic coefficients, load factors or regulatory compliance. Detailed clause adoption needs exact pages/tables, current legal applicability, and independent engineering review.

### Code selection vs historical report
New controlled seismic work: NBC105:2025. Historical report's 2020 clauses remain tagged as historical evidence; no computation of the previous structural report is automatically upgraded. Municipal building bylaws and actual project permit timeframe still require independent resolution.

The source package is stored privately in the pre-existing `01_NBC_NATIONAL` library, not duplicated into this public repository. Frozen milestone `a9-seq9-phase-c-20261015` remains untouched.
