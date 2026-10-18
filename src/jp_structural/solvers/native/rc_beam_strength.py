"""Bounded IS 456:2000 RC beam flexure and vertical-stirrup shear calculations.

Government-hosted IS 456:2000 with amendments:
https://wriddodoti.gov.np/uploads/blog/20230331071217_IS-456-with-all-ammendments.pdf
BIS confirms IS 456:2000 as published, reviewed in 2025.
Source authority is a code edition, NOT legacy spreadsheet numbers.

Scope: singly-reinforced, RECTANGULAR, normal-weight concrete flexure with
Fe415/Fe500 tension steel and separately supplied positive design moment;
vertical stirrup shear only, with SOURCE-SUPPLIED Table 19 tau_c.
NO double reinforcement, T/L sections, axial loads, torsion, load combinations,
cracked serviceability, ductile capacity design, anchorage, curtailment, column
interaction, or material/structural-engineering approval is implied.

All geometry mm, area mm², stress MPa=N/mm², forces kN, moment kN·m.
"""
from __future__ import annotations

import math

SOURCE = "https://wriddodoti.gov.np/uploads/blog/20230331071217_IS-456-with-all-ammendments.pdf"
CODE = "IS 456:2000 (published edition, amendments subject to source audit)"
FLEXURE_ID = "JP-RC-M08-FLEXURE-001"
SHEAR_ID = "JP-RC-M08-VERTICAL-SHEAR-002"
_XU_RATIO = {415: 0.48, 500: 0.46}
_TAUC_MAX = {20: 2.8, 25: 3.1, 30: 3.5, 35: 3.7, 40: 4.0}

class RCBeamInputError(ValueError):
    """Fail-closed numerical, geometry or unsupported-code input."""


def _num(value: object, name: str, *, zero: bool = False) -> float:
    if isinstance(value, bool):
        raise RCBeamInputError(f"{name}: boolean not permitted")
    try:
        n = float(value)
    except (TypeError, ValueError) as exc:
        raise RCBeamInputError(f"{name}: numeric value required") from exc
    if not math.isfinite(n) or (n < 0 if zero else n <= 0):
        raise RCBeamInputError(f"{name}: finite {'nonnegative' if zero else 'positive'} value required")
    return n


def _grade(grade: object, supported: set[int], name: str) -> int:
    f = _num(grade, name)
    if int(f) != f or int(f) not in supported:
        raise RCBeamInputError(f"{name}: only explicitly indexed grades {sorted(supported)}")
    return int(f)


def _section(b: object, d: object, D: object) -> tuple[float, float, float]:
    b = _num(b, "width_mm")
    d = _num(d, "effective_depth_mm")
    D = _num(D, "overall_depth_mm")
    if d >= D:
        raise RCBeamInputError("effective_depth_mm must be smaller than overall_depth_mm")
    if not math.isfinite(b * D):
        raise RCBeamInputError("section overflow")
    return b, d, D


def _mu(As: float, b: float, d: float, fck: int, fy: int) -> tuple[float, float]:
    # Fig.22 / Cl.38.1 rectangular compression block
    xu = (0.87 * fy * As) / (0.36 * fck * b)
    mu = 0.87 * fy * As * (d - 0.42 * xu) / 1_000_000
    if not (math.isfinite(xu) and math.isfinite(mu)):
        raise RCBeamInputError("moment calculation overflow")
    return xu, mu


def rectangular_singly_reinforced_flexure(
    *, width_mm: float, effective_depth_mm: float, overall_depth_mm: float,
    fck_MPa: int, fy_MPa: int, tension_steel_area_mm2: float,
    factored_moment_kNm: float,
) -> dict:
    """Cl. 38.1/Fig. 22; Cl.26.5.1.1. No allowable capacity for over-reinforced section.

    x_u=0.87fy Ast/(0.36fck b); Mu=0.87fy Ast(d-0.42xu).
    Values are computed in N·mm, then divided by 10^6 to kN·m.
    """
    b, d, D = _section(width_mm, effective_depth_mm, overall_depth_mm)
    fck = _grade(fck_MPa, set(_TAUC_MAX), "fck_MPa")
    fy = _grade(fy_MPa, set(_XU_RATIO), "fy_MPa")
    Ast = _num(tension_steel_area_mm2, "tension_steel_area_mm2")
    demand = _num(factored_moment_kNm, "factored_moment_kNm", zero=True)
    xu_limit = _XU_RATIO[fy] * d
    ast_max_neutral = 0.36 * fck * b * xu_limit / (0.87 * fy)
    ast_min = .85 * b * d / fy
    ast_max_total = .04 * b * D
    mu_limit = .36 * fck * b * xu_limit * (d - .42 * xu_limit) / 1_000_000
    xu, mu = _mu(Ast, b, d, fck, fy)
    if not all(math.isfinite(x) for x in (ast_max_neutral,ast_min,ast_max_total,mu_limit)):
        raise RCBeamInputError("capacity bounds overflow")
    checks = {
        "minimum_tension_steel": Ast >= ast_min,
        "max_steel_area_0_04_bD": Ast <= ast_max_total,
        "under_reinforced_xu_limit": xu <= xu_limit * (1 + 1e-12),
        "flexural_capacity_vs_demand": mu >= demand if xu <= xu_limit*(1+1e-12) else False,
    }
    return {
        "formula_id": FLEXURE_ID, "edition":CODE, "source":SOURCE,
        "clauses": ["26.5.1.1", "38.1/Fig.22", "Annex G neutral-axis limiting ratios"],
        "scope":"SINGLY_REINFORCED_RECTANGULAR_POSITIVE_FLEXURE",
        "geometry_mm":{"b":b,"d":d,"D":D},
        "grades_MPa":{"fck":fck,"fy":fy},
        "Ast_provided_mm2":Ast,"Ast_min_mm2":ast_min,
        "Ast_max_by_neutral_axis_mm2":ast_max_neutral,
        "Ast_max_0_04_bD_mm2":ast_max_total,
        "neutral_axis_xu_mm":xu,"neutral_axis_limit_mm":xu_limit,
        "max_singly_reinforced_moment_kNm":mu_limit,
        "nominal_design_moment_capacity_kNm":mu if checks["under_reinforced_xu_limit"] else None,
        "factored_moment_kNm":demand,
        "checks":checks,
        "status":"BOUNDED_FLEXURE_PRECHECK_PASS" if all(checks.values()) else "FAIL",
        "full_RC_design_complete":False, "engineering_approval":False,
    }


def required_singly_reinforced_steel_area(
    *, width_mm: float, effective_depth_mm: float, overall_depth_mm: float,
    fck_MPa: int, fy_MPa: int, factored_moment_kNm: float,
) -> dict:
    """Deterministic numerical root for Ast to resist positive uniaxial Mu.

    Uses bounded bisection rather than a potentially cancellation-sensitive
    quadratic. Returns required steel AREA only; NOT bar count or detailing.
    """
    b, d, D = _section(width_mm,effective_depth_mm,overall_depth_mm)
    fck=_grade(fck_MPa,set(_TAUC_MAX),"fck_MPa")
    fy=_grade(fy_MPa,set(_XU_RATIO),"fy_MPa")
    demand=_num(factored_moment_kNm,"factored_moment_kNm",zero=True)
    limit_Ast=.36*fck*b*(_XU_RATIO[fy]*d)/(.87*fy)
    limit_Mu=_mu(limit_Ast,b,d,fck,fy)[1]
    min_Ast=.85*b*d/fy
    max_As=.04*b*D
    if not all(math.isfinite(v) for v in (limit_Ast,limit_Mu,min_Ast,max_As)):
        raise RCBeamInputError("limiting design bounds overflow")
    if demand>limit_Mu*(1+1e-12) or min_Ast>min(limit_Ast,max_As):
        return {"formula_id":FLEXURE_ID,"edition":CODE,"source":SOURCE,
                "status":"FAIL_SINGLY_REINFORCED_CAPACITY", "required_Ast_mm2":None,
                "limit_Mu_kNm":limit_Mu, "engineering_approval":False}
    lo,hi=0.,limit_Ast
    for _ in range(90):
        mid=(lo+hi)/2
        if _mu(mid,b,d,fck,fy)[1] < demand:lo=mid
        else:hi=mid
    ast=max(hi,min_Ast)
    if ast>max_As:
        return {"formula_id":FLEXURE_ID,"edition":CODE,"source":SOURCE,
                "status":"FAIL_MAX_STEEL","required_Ast_mm2":None,
                "limit_Mu_kNm":limit_Mu,"engineering_approval":False}
    return {
        "formula_id":FLEXURE_ID,"edition":CODE,"source":SOURCE,
        "status":"CANDIDATE_AREA_ONLY_NOT_BAR_DESIGN",
        "required_Ast_mm2":ast,"limit_Mu_kNm":limit_Mu,
        "required_area_includes_minimum_steel":True,
        "engineering_approval":False,
    }


def vertical_stirrup_shear_check(
    *, width_mm: float, effective_depth_mm: float, fck_MPa: int,
    factored_shear_kN: float,
    table19_concrete_shear_strength_MPa: float,
    table19_lookup_source_id: str,
    stirrup_fy_MPa: float, stirrup_legs: int,
    stirrup_diameter_mm: float, provided_spacing_mm: float,
) -> dict:
    """Cl.40.2–40.4, Table 20, Cl.26.5.1.5/6: conservative preliminary shear.

    Table 19 tau_c MUST be sourced externally from the actual concrete grade,
    percentage of tension reinforcement, and applicable analysis convention.
    A caller-provided value, even with a string source ID, is NOT machine-verified,
    therefore code-complete status always remains HOLD unless physical checks FAIL.
    """
    b=_num(width_mm,"width_mm")
    d=_num(effective_depth_mm,"effective_depth_mm")
    fck=_grade(fck_MPa,set(_TAUC_MAX),"fck_MPa")
    Vu=_num(factored_shear_kN,"factored_shear_kN",zero=True)
    tc=_num(table19_concrete_shear_strength_MPa,"table19_concrete_shear_strength_MPa")
    if not isinstance(table19_lookup_source_id,str) or not table19_lookup_source_id.strip():
        raise RCBeamInputError("Table19 lookup must have a nonempty evidence ID")
    fy=_num(stirrup_fy_MPa,"stirrup_fy_MPa")
    if fy>415:
        raise RCBeamInputError("Cl.40.4 stirrup design fy cannot exceed 415 MPa")
    if not isinstance(stirrup_legs,int) or isinstance(stirrup_legs,bool) or stirrup_legs<2:
        raise RCBeamInputError("vertical stirrup legs must be integer >=2")
    phi=_num(stirrup_diameter_mm,"stirrup_diameter_mm")
    spacing=_num(provided_spacing_mm,"provided_spacing_mm")
    tcmax=_TAUC_MAX[fck]
    if tc>tcmax:
        raise RCBeamInputError("Table19 tau_c cannot exceed Table20 tau_c,max")
    av=stirrup_legs*math.pi*phi**2/4
    Vconcrete=tc*b*d/1000
    Vstirrups=.87*fy*av*d/spacing/1000
    v_required=max(0.,Vu-Vconcrete)
    tau_v=Vu*1000/(b*d)
    s_max=min(.75*d,300.)
    Av_by_s=av/spacing
    minimum_Av_by_s=.4*b/(.87*fy)
    check={
        "nominal_shear_below_table20_max":tau_v<=tcmax,
        "provided_stirrups_cover_residual":Vstirrups>=v_required*(1-1e-12),
        "maximum_stirrup_spacing":spacing<=s_max,
        "minimum_shear_steel":Av_by_s>=minimum_Av_by_s,
    }
    vals=(av,Vconcrete,Vstirrups,v_required,tau_v,s_max,Av_by_s,minimum_Av_by_s)
    if not all(math.isfinite(v) for v in vals):
        raise RCBeamInputError("shear strength calculation overflow")
    return {
        "formula_id":SHEAR_ID,"edition":CODE,"source":SOURCE,
        "clauses":["26.5.1.5","26.5.1.6","40.2/Table19","40.2.3/Table20","40.4"],
        "scope":"VERTICAL_STIRRUPS_NO_TORSION_NO_AXIAL_FORCE",
        "concrete_tau_c_MPa":tc,"table19_lookup_source_id":table19_lookup_source_id,
        "table19_numerical_lookup_machine_verified":False,
        "tau_c_max_MPa":tcmax,"applied_tau_v_MPa":tau_v,
        "concrete_shear_contribution_kN":Vconcrete,
        "stirrup_shear_capacity_kN":Vstirrups,
        "stirrup_shear_demand_kN":v_required,
        "stirrup_area_mm2":av,"stirrup_spacing_mm":spacing,
        "maximum_spacing_mm":s_max,"minimum_Asv_per_spacing_mm2_per_mm":minimum_Av_by_s,
        "checks":check,
        "status":"FAIL" if not all(check.values()) else "HOLD_TABLE19_NUMERIC_LOOKUP",
        "full_RC_design_complete":False,"engineering_approval":False,
    }


# Table 19 transcribed from the source PDF at printed page 73.
# Column values are MPa for M20/M25/M30/M35/M40+; no M15 RC design
# is admitted in this bounded engine. Reference is kept as code/table,
# not as a client-model assumption.
_TABLE19 = {
    20: ((.15,.28),(.25,.36),(.50,.48),(.75,.56),(1.,.62),(1.25,.67),(1.5,.72),(1.75,.75),(2.,.79),(2.25,.81),(2.5,.82),(2.75,.82),(3.,.82)),
    25: ((.15,.29),(.25,.36),(.50,.49),(.75,.57),(1.,.64),(1.25,.70),(1.5,.74),(1.75,.78),(2.,.82),(2.25,.85),(2.5,.88),(2.75,.90),(3.,.92)),
    30: ((.15,.29),(.25,.37),(.50,.50),(.75,.59),(1.,.66),(1.25,.71),(1.5,.76),(1.75,.80),(2.,.84),(2.25,.88),(2.5,.91),(2.75,.94),(3.,.96)),
    35: ((.15,.29),(.25,.37),(.50,.50),(.75,.59),(1.,.67),(1.25,.73),(1.5,.78),(1.75,.82),(2.,.86),(2.25,.90),(2.5,.93),(2.75,.96),(3.,.99)),
    40: ((.15,.30),(.25,.38),(.50,.51),(.75,.60),(1.,.68),(1.25,.74),(1.5,.79),(1.75,.84),(2.,.88),(2.25,.92),(2.5,.95),(2.75,.98),(3.,1.01)),
}


def conservative_table19_shear_strength(
    *, fck_MPa: int, tension_steel_percentage: float
) -> dict:
    """Table 19 source-table lookup, deliberately floors steel-% to prior row.

    Flooring never returns a higher tau_c than linear interpolation would
    produce for these monotonic table rows. Table says >=3.0 row may be used
    for higher supplied percentages. This does NOT verify bar continuation,
    bond, development, moment reversal, axial force, or section adequacy.
    """
    fck=_grade(fck_MPa,set(_TABLE19),"fck_MPa")
    percent=_num(tension_steel_percentage,"tension_steel_percentage")
    rows=_TABLE19[fck]
    row=rows[0]
    for candidate in rows:
        if candidate[0]>percent+1e-12:break
        row=candidate
    return {"formula_id":"JP-RC-M08-IS456-TABLE19-003","edition":CODE,
            "source":SOURCE,"clause":"40.2.1/Table 19",
            "fck_MPa":fck,"provided_tension_steel_pct":percent,
            "selected_floor_tension_steel_pct":row[0],
            "tau_c_MPa":row[1],
            "method":"TABLE19_LOWER_OR_EQUAL_STEEL_PERCENT_ROW",
            "numerical_table_lookup_verified":True,
            "safety_scope":"CONSERVATIVE_SHEAR_COEFFICIENT_ONLY"}


def vertical_stirrup_shear_from_steel(
    *, width_mm: float, effective_depth_mm: float, fck_MPa: int,
    tension_steel_area_mm2: float, factored_shear_kN: float,
    stirrup_fy_MPa: float, stirrup_legs: int,
    stirrup_diameter_mm: float, provided_spacing_mm: float,
) -> dict:
    """Bounded Table19→Cl40.4 checker with no external manually typed tau_c.

    The caller must independently establish tension steel continuity beyond
    the critical section per Table 19's note. Does not complete anchorage,
    capacity shear, high-seismic ductile detailing, torsion or axial effects.
    """
    b=_num(width_mm,"width_mm")
    d=_num(effective_depth_mm,"effective_depth_mm")
    Ast=_num(tension_steel_area_mm2,"tension_steel_area_mm2")
    p=100*Ast/(b*d)
    if not math.isfinite(p):raise RCBeamInputError("steel percentage overflow")
    lookup=conservative_table19_shear_strength(fck_MPa=fck_MPa,tension_steel_percentage=p)
    result=vertical_stirrup_shear_check(
        width_mm=b,effective_depth_mm=d,fck_MPa=fck_MPa,
        factored_shear_kN=factored_shear_kN,
        table19_concrete_shear_strength_MPa=lookup["tau_c_MPa"],
        table19_lookup_source_id="IS456-2000-TABLE19-LOWER-ROW",
        stirrup_fy_MPa=stirrup_fy_MPa,stirrup_legs=stirrup_legs,
        stirrup_diameter_mm=stirrup_diameter_mm,provided_spacing_mm=provided_spacing_mm)
    result["table19_lookup"]=lookup
    result["table19_numerical_lookup_machine_verified"]=True
    if result["status"]=="HOLD_TABLE19_NUMERIC_LOOKUP":
        result["status"]="BOUNDED_SHEAR_NUMERIC_CHECK_PASS_NOT_FULL_DESIGN"
    result["unverified_inputs_and_design"]=[
        "Actual tension bar continuity/development beyond critical shear section",
        "Ductile shear based on probable flexural strength per NBC 105:2025",
        "Combined torsion, axial load, frame load-combination and support-region shear",
        "Detailing, anchorages, curtailment, and independent whole-structure benchmarks",
    ]
    return result
