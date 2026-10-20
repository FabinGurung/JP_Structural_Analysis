"""NBC 105:2025 bounded elastic equivalent-static load distribution.

Source: official NBC 105:2025, clauses 5.2, 5.5, 5.6, 6.1 to 6.4.
This module computes code equations only. It does not independently verify
seismic zoning, Vs30, response-spectrum period, effective member stiffness,
accidental eccentricity, diaphragm eccentricity or source FE geometry.
No construction safety approval is represented.
"""
from __future__ import annotations
import math
from collections.abc import Mapping, Sequence

class ESMInputError(ValueError):
    """Reject missing or nonphysical code inputs."""

def _pos(value, label):
    if isinstance(value, bool):
        raise ESMInputError(label + " must be a positive real number")
    try:
        n=float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ESMInputError(label + " must be numeric") from exc
    if not math.isfinite(n) or n<=0:
        raise ESMInputError(label + " must be finite and positive")
    return n

def period_exponent(T_seconds):
    """NBC 105:2025 clause 6.3: k=1 below 0.5s; k=2 above 2.5s."""
    t=_pos(T_seconds,"T_seconds")
    if t<=.5:return 1.0
    if t>=2.5:return 2.0
    return 1.0+(t-.5)/2.0

def design_coefficients(*, elastic_horizontal_C, ductility_Rmu,
                        overstrength_ULS, elastic_SLS_Cs, overstrength_SLS):
    """NBC105:2025 6.1: Cd,ULS=C/(Rmu*Omega_u), Cd,SLS=Cs/Omega_s."""
    c=_pos(elastic_horizontal_C,"elastic_horizontal_C")
    r=_pos(ductility_Rmu,"ductility_Rmu")
    ou=_pos(overstrength_ULS,"overstrength_ULS")
    cs=_pos(elastic_SLS_Cs,"elastic_SLS_Cs")
    os=_pos(overstrength_SLS,"overstrength_SLS")
    return {"ULS":c/(r*ou),"SLS":cs/os,
            "code":"NBC105:2025","clauses":["6.1.1","6.1.2"],
            "seismic_input_verification":"CALLER_SUPPLIED_NOT_INDEPENDENTLY_VERIFIED"}

def equivalent_static_floor_forces(*, floor_weights_kN: Sequence[float],
                                  floor_heights_m: Sequence[float],
                                  period_seconds: float, design_coefficient: float):
    """NBC105:2025 6.2/6.3 floor forces from explicit seismic weights and heights.

    Floors and masses must be supplied in ascending elevation order.
    Do not use this as a proxy for coupled model/drift/ductile design.
    """
    if (not isinstance(floor_weights_kN,(tuple,list)) or
        not isinstance(floor_heights_m,(tuple,list)) or
        len(floor_weights_kN)!=len(floor_heights_m) or not floor_weights_kN):
        raise ESMInputError("matching nonempty floor weights and heights required")
    weights=[_pos(x,"floor_weight_kN") for x in floor_weights_kN]
    heights=[_pos(x,"floor_height_m") for x in floor_heights_m]
    if any(b<=a for a,b in zip(heights,heights[1:])):
        raise ESMInputError("heights must be strictly increasing")
    cd=_pos(design_coefficient,"design_coefficient")
    t=_pos(period_seconds,"period_seconds")
    exponent=period_exponent(t)
    weighted=[w*h**exponent for w,h in zip(weights,heights)]
    V=math.fsum(weights)*cd
    denominator=math.fsum(weighted)
    forces=[V*p/denominator for p in weighted]
    if not math.isclose(math.fsum(forces),V,rel_tol=1e-12,abs_tol=1e-9):
        raise ESMInputError("floor-force equilibrium failed")
    return {"code":"NBC105:2025",
            "clauses":["6.2(1)","6.3(1)","6.4"],
            "period_s":t,"distribution_exponent":exponent,
            "seismic_weight_kN":math.fsum(weights),
            "base_shear_kN":V,"floor_heights_m":heights,
            "floor_seismic_weights_kN":weights,
            "floor_forces_kN":forces,
            "accidental_eccentricity_applied":False,
            "drift_and_detailing_verified":False,
            "status":"NUMERICALLY_BALANCED_DISTRIBUTION_ONLY",
            "engineering_approval":False}

def signed_case_combination(components: Mapping[str,Sequence[float]],
                            factors: Mapping[str,float]):
    """Sum concurrent signed components before enveloping. Never add peaks."""
    if not isinstance(components,Mapping) or not isinstance(factors,Mapping) or not factors:
        raise ESMInputError("nonempty source case mapping and factors required")
    ids=list(factors)
    if any(i not in components for i in ids):
        raise ESMInputError("unknown source load case")
    widths=[len(components[i]) for i in ids]
    if len(set(widths))!=1 or widths[0]==0:
        raise ESMInputError("all components require identical nonempty width")
    values=[]
    for k in range(widths[0]):
        terms=[]
        for i in ids:
            f=factors[i]
            if isinstance(f,bool):
                raise ESMInputError("nonfinite combination factor")
            try:f=float(f)
            except (TypeError,ValueError,OverflowError) as exc:
                raise ESMInputError("nonfinite combination factor") from exc
            if not math.isfinite(f):
                raise ESMInputError("nonfinite combination factor")
            v=components[i][k]
            if isinstance(v,bool):
                raise ESMInputError("nonfinite signed case force")
            try:v=float(v)
            except (TypeError,ValueError,OverflowError) as exc:
                raise ESMInputError("nonfinite signed case force") from exc
            if not math.isfinite(v):
                raise ESMInputError("nonfinite signed case force")
            terms.append(f*v)
        values.append(math.fsum(terms))
    return values

def bounded_story_drift(*, elastic_interstory_delta_m, story_height_m,
                       limit_state, ductility_Rmu, source_model_stiffness_verified=False,
                       accidental_eccentricity_verified=False,
                       mass_and_geometry_verified=False):
    """NBC105:2025 5.5.1,5.5.3 — precheck, never a default PASS.

    2025 ULS design displacement = Rmu * elastic displacement, ULS drift
    limit 0.025; SLS limit 0.006 without multiplication.
    Incomplete effective stiffness/eccentricity/model provenance means HOLD.
    """
    delta=_pos(elastic_interstory_delta_m,"elastic_interstory_delta_m")
    height=_pos(story_height_m,"story_height_m")
    r=_pos(ductility_Rmu,"ductility_Rmu")
    if limit_state not in ("ULS","SLS"):
        raise ESMInputError("limit_state must be ULS or SLS")
    for flag in (source_model_stiffness_verified,accidental_eccentricity_verified,mass_and_geometry_verified):
        if not isinstance(flag,bool):
            raise ESMInputError("verification flags must be boolean")
    demand=(r if limit_state=="ULS" else 1.)*delta/height
    limit=.025 if limit_state=="ULS" else .006
    numerical_excess=demand>limit
    verified=(source_model_stiffness_verified and accidental_eccentricity_verified
              and mass_and_geometry_verified)
    status=("NUMERICAL_LIMIT_EXCEEDED_ENGINEERING_REVIEW" if numerical_excess
            else "NUMERICALLY_WITHIN_LIMIT_BUT_EVIDENCE_HOLD" if not verified
            else "BOUNDED_NUMERIC_PASS_SOURCE_GATES_RECORDED")
    return {"code":"NBC105:2025","clauses":["5.5.1","5.5.3","5.6"],
            "limit_state":limit_state,"elastic_delta_m":delta,
            "story_height_m":height,"ductility_Rmu":r,
            "calculated_design_drift_ratio":demand,"numerical_limit":limit,
            "numerical_limit_exceeded":numerical_excess,
            "source_model_stiffness_verified":source_model_stiffness_verified,
            "accidental_eccentricity_verified":accidental_eccentricity_verified,
            "mass_and_geometry_verified":mass_and_geometry_verified,
            "status":status,"engineering_approval":False}
