"""Bounded mandatory RC seismic DETAILING PRECHECKS from NBC 105:2025 Annex A.

This is NOT RC flexural/shear/biaxial design and never calculates
a reinforcement schedule or structural member capacity. Functions accept
externally established actual geometry and bar lists. Advisory clauses
are never incorrectly converted to mandatory failures.

Official: https://ebps.kathmandu.gov.np/UploadFiles/NBC_105_2025_Sesmic_Design.pdf
Annex A clauses 4.1.1, 4.1.2(a), 4.2.1, 4.2.2, 4.4.4.
"""
from __future__ import annotations
import math
from collections.abc import Mapping, Sequence

CODE = "NBC 105:2025"
SOURCE = "https://ebps.kathmandu.gov.np/UploadFiles/NBC_105_2025_Sesmic_Design.pdf"

class RCPrecheckInputError(ValueError):
    """Required size/capacity/evidence is missing, invalid or unverifiable."""


def _pos(value: object, name: str) -> float:
    if isinstance(value,bool):raise RCPrecheckInputError(f"{name}: bool invalid")
    try:x=float(value)
    except (ValueError,TypeError) as exc:raise RCPrecheckInputError(f"{name}: number required") from exc
    if not math.isfinite(x) or x<=0:
        raise RCPrecheckInputError(f"{name}: finite positive value required")
    return x


def _result(clause: str, checks: Mapping[str,bool], advisories: Mapping[str,bool] | None=None) -> dict:
    return {"code":CODE,"source":SOURCE,"clause":clause,
            "check_results":dict(checks),
            "advisories":dict(advisories or {}),
            "status":"BOUNDED_PRECHECK_PASS" if all(checks.values()) else "FAIL",
            "engineering_approval":False}


def beam_geometry_precheck(width_mm: float, depth_mm: float, clear_span_mm: float) -> dict:
    """Annex A §4.1.1(b-c) mandatory; §4.1.1(a) 'preferably' is advisory."""
    b=_pos(width_mm,"width_mm")
    d=_pos(depth_mm,"depth_mm")
    L=_pos(clear_span_mm,"clear_span_mm")
    return _result("Annex A 4.1.1",
                   {"width_at_least_200mm":b>=200,
                    "depth_at_most_quarter_clear_span":d<=L/4},
                   {"preferred_width_to_depth_gt_0_3":b/d>.3})


def beam_min_longitudinal_precheck(top_bars_mm: Sequence[float], bottom_bars_mm: Sequence[float]) -> dict:
    """Annex A §4.1.2(a): at least two >=12 mm bars on each face.
    Flexural capacity, anchorage, lap, shear and other rules NOT checked.
    """
    def _face(values,face):
        if not isinstance(values,(tuple,list)):
            raise RCPrecheckInputError(f"{face}: explicit bar list required")
        return [_pos(v,f"{face}.bar") for v in values]
    top,bottom=_face(top_bars_mm,"top"),_face(bottom_bars_mm,"bottom")
    return _result("Annex A 4.1.2(a)",{
        "at_least_two_top_bars_ge_12mm":len([b for b in top if b>=12])>=2,
        "at_least_two_bottom_bars_ge_12mm":len([b for b in bottom if b>=12])>=2})


def column_geometry_precheck(
    min_dimension_mm: float, maximum_beam_longitudinal_bar_mm: float,
    other_dimension_mm: float
) -> dict:
    """Annex A §4.2.1(a-b) mandatory, §4.2.1(c) preference advisory."""
    mini=_pos(min_dimension_mm,"min_dimension_mm")
    maxi=_pos(other_dimension_mm,"other_dimension_mm")
    db=_pos(maximum_beam_longitudinal_bar_mm,"maximum_beam_longitudinal_bar_mm")
    if maxi<mini:raise RCPrecheckInputError("other_dimension_mm must be >= minimum dimension")
    return _result("Annex A 4.2.1",
                   {"minimum_dimension_300mm":mini>=300,
                    "minimum_dimension_20db":mini>=20*db},
                   {"preferred_width_depth_ratio_gt_0_45":mini/maxi>.45})


def column_longitudinal_steel_precheck(
    section_type: str, gross_area_mm2: float,
    bar_diameters_mm: Sequence[float]
) -> dict:
    """Annex A §4.2.2(a-d): bar count, rho 1–4%, minimum 12 mm.
    Does not establish design strength, demand/capacity interaction or ties.
    """
    if section_type not in {"RECTANGULAR","CIRCULAR"}:
        raise RCPrecheckInputError("section_type must be RECTANGULAR/CIRCULAR")
    Ag=_pos(gross_area_mm2,"gross_area_mm2")
    if not isinstance(bar_diameters_mm,(list,tuple)):
        raise RCPrecheckInputError("explicit bar list required")
    bars=[_pos(v,"bar_diam_mm") for v in bar_diameters_mm]
    steel=math.fsum(math.pi*b*b/4 for b in bars)
    rho=steel/Ag
    if not math.isfinite(rho):raise RCPrecheckInputError("bar area overflow")
    result=_result("Annex A 4.2.2",
                   {"minimum_bar_count":len(bars)>=(8 if section_type=="RECTANGULAR" else 6),
                    "longitudinal_ratio_min_0_01":rho>=.01,
                    "longitudinal_ratio_max_0_04":rho<=.04,
                    "minimum_bar_diameter_12mm":bool(bars) and min(bars)>=12})
    result.update({"provided_steel_area_mm2":steel,"provided_rho":rho})
    return result


def column_beam_moment_capacity_precheck(
    sum_column_Mc_kNm: float, sum_beam_Mb_kNm: float,
    *, roof_joint: bool, capacity_inputs_independently_verified: bool
) -> dict:
    """Annex A §4.4.4 >1.2, except roof joint waived.

    Demands and section capacities must come from a separate independently
    checked design engine, not inferred by this routine.
    """
    if not isinstance(roof_joint,bool) or not isinstance(capacity_inputs_independently_verified,bool):
        raise RCPrecheckInputError("roof_joint and evidence flags must be bool")
    if roof_joint:
        return {"code":CODE,"source":SOURCE,"clause":"Annex A 4.4.4",
                "status":"NOT_APPLICABLE_ROOF_JOINT","engineering_approval":False}
    if not capacity_inputs_independently_verified:
        raise RCPrecheckInputError("independently verified moment capacities required")
    Mc=_pos(sum_column_Mc_kNm,"sum_column_Mc_kNm")
    Mb=_pos(sum_beam_Mb_kNm,"sum_beam_Mb_kNm")
    row=_result("Annex A 4.4.4",{"sum_Mc_strictly_greater_than_1_2_sum_Mb":Mc>1.2*Mb})
    row["moment_capacity_ratio"]=Mc/Mb
    return row


def fail_closed_design_summary(checks: Sequence[Mapping]) -> dict:
    """No adopted member or worksheet marked PASS after ANY unsafe finding."""
    if not isinstance(checks,(list,tuple)) or not checks:
        raise RCPrecheckInputError("nonempty check evidence list required")
    fail,hold=[],[]
    for row in checks:
        if not isinstance(row,Mapping):
            raise RCPrecheckInputError("check must be mapping")
        cid=row.get("check_id")
        if not isinstance(cid,str) or not cid.strip():
            raise RCPrecheckInputError("check_id required")
        raw=row.get("status")
        if raw in ("FAIL","NOT SAFE","UNSAFE"):
            fail.append(cid)
        elif raw in ("PASS","BOUNDED_PRECHECK_PASS"):
            pass
        elif raw in ("HOLD","NOT_EVALUATED","SOLVER_RESULT_UNCHECKED","NOT_APPLICABLE_ROOF_JOINT"):
            hold.append(cid)
        else:
            raise RCPrecheckInputError(f"unsupported safety state: {raw!r}")
    status=("FAIL" if fail else "HOLD" if hold else "BOUNDED_PRECHECKS_PASS_FULL_DESIGN_NOT_EVALUATED")
    return {"status":status,"failed_check_ids":fail,"held_check_ids":hold,
            "engineering_approval":False,
            "accepted_design":False}
