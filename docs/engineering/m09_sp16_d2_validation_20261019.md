# M09 original SP16 and Phase D2 validation record (19 October 2026)

## Status
**PARTIAL/HOLD** for structural safety; **PASS** for scoped static signed elastic
member-response extraction and signed combination arithmetic. No real project
or independent professional code approval.

### SP16 original-chart source and edition conflict

- Archive entry: https://archive.org/details/gov.in.is.sp.16.1980
- Scanned PDF: https://archive.org/download/gov.in.is.sp.16.1980/is.sp.16.1980.pdf
- Metadata flags SP16:1980 **withdrawn**; title explicitly refers to IS456:1978.
- The scanned PDF could not be fetched via this session's supported download
  or PDF screenshot path. The original Chart 31 coordinates therefore have
  **not** been visually inspected and independently digitized; direct original
  Chart 31 audit stays HOLD. Never label the original chart VERIFIED on the
  strength of derivative calculations.
- Two SP16 Chart 31-related independent worked calculations: 
  https://www.sefindia.org/forum/viewtopic.php?t=1979 
  at Pu/fckbD 0.25 / 0.44; normalized moments .081575 / .028979.
  Unit tests agree within declared tolerance, **not digitized chart QA**.
- Fe415/Fe500 stress points are independently compared with published Table A
  reproduction, not a chart-certified full material or detail approval.
- The new IS456:2000/2000 amendments code basis versus the historical 1978
  SP16 edition must be reconciled clause by clause before asserting parity.

### D2 contract and risks

- Source: https://opensees.github.io/OpenSeesDocumentation/user/manual/model/elements/elasticBeamColumn.html
- 3D elasticBeamColumn `eleResponse(tag,'localForce')` i/j local end
  resisting actions in [N,Vy,Vz,T,My,Mz] order; explicit kN/m/s basis.
- A signed load combination is an algebraic sum of **same member, same end,
  same component**. It is not a sum of peak absolute values from different
  combinations and does not manufacture a coherent signed CQC/SRSS pattern.
- Six global F/M equilibrium components are independently checked for each
  isolated nodal linear-static case.
- M08 receives signed-to-magnitude end shears after combination and **separate
  source-identified beam hinge strengths**; strength capacity remains external.
- M09 receives compression-positive Pu and two signed mapped local moments
  from each *same combination* and end; explicit bar coordinates, section and
  member-source identity required; tension, 2nd order/slenderness, site/detail
  acceptance remain unsupported.
- M10 receives column end shear from its **connected** column member and the
  explicit connected joint beam; all reinforcement, geometry and confinement
  class are **source-defined**; joint shear is not full seismic joint acceptance.
- No internal or external force envelopes should be interpreted as a
  fully code-compliant nonlinear RC capacity design.

### To close remaining source/chart gates

Secure readable authentic SP16 edition Chart 31 page; independently read
the actual plotted curves for verified bar distribution p/fck and d'/D,
document axis scaling and digitization uncertainty, then record immutable
chart ordinate fixtures and comparisons; validate IS456 amendments and
NBC105:2025 Annex A detailing, actual FE signed seismic combinations,
P-Delta and source report traceability.
