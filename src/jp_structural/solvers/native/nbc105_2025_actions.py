"""Bounded, source-traced NBC 105:2025 seismic action rules.

Source: Government of Nepal NBC 105:2025 second revision, current code
https://ebps.kathmandu.gov.np/UploadFiles/NBC_105_2025_Sesmic_Design.pdf
ONLY rules below whose pages/clauses were independently checked are admitted.
No soil class, Z, I, code applicability or site dimensions are guessed.
Structural analysis/design approval is a separate gate.
"""
from __future__ import annotations
from collections.abc import Mapping, Sequence
import math

from jp_structural.qa.nbc_code_basis import validate_code_basis, CodeBasisError
from jp_structural.solvers.native.equivalent_lateral import vertical_force_distribution

SOURCE_URL = "https://ebps.kathmandu.gov.np/UploadFiles/NBC_105_2025_Sesmic_Design.pdf"
CODE_EDITION = "NBC 105:2025"
# Table 4-1 (printed p24, PDF p43): ESM plateaus, Ta=0 in ESM.
_ESM_PLATEAUS = {
    "A": (0.5, 2.5), "B": (0.7, 2.5),
    "C": (1.0, 2.5), "D": (2.0, 2.25),
}
# Table 5-1 (printed p31, PDF p51).
_LIVE_FACTORS = {
    "DEAD": 1.0,
    "STORAGE_LIVE": 0.60,
    "OTHER_LIVE": 0.30,
    "ROOF_LIVE": 0.0,
}

class NBCActionError(ValueError):
    """Unsupported code rule or missing explicit adopted source input."""


def _positive(value: object, field: str) -> float:
    if isinstance(value, bool):
        raise NBCActionError(f"{field}: not a number")
    try: number=float(value)
    except (ValueError, TypeError) as exc:
        raise NBCActionError(f"{field}: numeric input required") from exc
    if not math.isfinite(number) or number <= 0:
        raise NBCActionError(f"{field}: finite positive input required")
    return number


def _source_id(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise NBCActionError(f"{name}: source/evidence ID required")
    return value


def _check_basis(basis: Mapping) -> None:
    try:
        result=validate_code_basis(basis)
    except (CodeBasisError, TypeError, AttributeError) as exc:
        raise NBCActionError(f"Invalid NBC edition selection: {exc}") from exc
    if result.get("calculation_scope") != "NEW_ENGINEERED_ANALYSIS" or result["code_editions"].get("NBC 105")!="2025":
        raise NBCActionError("NBC 105:2025 engineered analysis basis is mandatory")
    url=basis.get("source_references",{}).get("NBC 105","")
    if url != SOURCE_URL and not url.startswith("https://dudbc.gov.np/") and not url.startswith("https://www.dudbc.gov.np/"):
        raise NBCActionError("NBC 105 source must be an identified official government URL")


def live_seismic_weight_factor(category: str) -> dict:
    """Table 5-1, together with dead load participation."""
    if category not in _LIVE_FACTORS:
        raise NBCActionError(f"unsupported seismic-weight category: {category!r}")
    return {"code":CODE_EDITION,"clause":"5.2/Table 5-1",
            "source":SOURCE_URL,"category":category,
            "participation_factor":_LIVE_FACTORS[category]}


def apply_verified_live_factors(components: Sequence[Mapping], basis: Mapping) -> list[dict]:
    """Create load-assembly records; reject mismatched caller-supplied factors.

    Does not infer category from project occupancy and does not assign loads.
    """
    _check_basis(basis)
    if not isinstance(components,(list,tuple)) or not components:
        raise NBCActionError("source components required")
    result=[]
    for item in components:
        if not isinstance(item,Mapping):
            raise NBCActionError("component must be mapping")
        row=dict(item)
        factor=live_seismic_weight_factor(row.get("load_category"))["participation_factor"]
        if "participation_factor" in row:
            try: given=float(row["participation_factor"])
            except (TypeError,ValueError) as exc:raise NBCActionError("invalid supplied factor") from exc
            if not math.isfinite(given) or not math.isclose(given,factor,rel_tol=0,abs_tol=1e-12):
                raise NBCActionError("caller-supplied factor conflicts with NBC 105:2025 5.2")
        row["participation_factor"]=factor
        result.append(row)
    return result


def rc_frame_design_period(height_m: float, rayleigh_period_s: float) -> dict:
    """RC moment resisting frame only: 5.1.2 kt=0.075, H^.75;
    5.1.3 factor=1.25; 5.1 compare and adopt lesser Rayleigh period.
    """
    h=_positive(height_m,"height_m")
    rayleigh=_positive(rayleigh_period_s,"rayleigh_period_s")
    empirical=0.075*h**0.75
    amended=1.25*empirical
    if not math.isfinite(amended):raise NBCActionError("period calculation overflow")
    return {"code":CODE_EDITION,"clauses":["5.1.1","5.1.2","5.1.3"],
            "source":SOURCE_URL,"structural_system":"RC_MOMENT_RESISTING_FRAME",
            "empirical_period_s":empirical,"amplified_empirical_period_s":amended,
            "rayleigh_period_s":rayleigh,"adopted_design_period_s":min(amended,rayleigh)}


def esm_plateau_shape_factor(soil_type: str, design_period_s: float) -> dict:
    """Verified constant branch only. All unverified branches FAIL CLOSED.

    Equivalent Static Method (ESM) has Ta=0, unlike modal spectra.
    """
    t=_positive(design_period_s,"design_period_s")
    if soil_type not in _ESM_PLATEAUS:
        raise NBCActionError("soil type must be one of A/B/C/D and source classified")
    tc,peak=_ESM_PLATEAUS[soil_type]
    if t>tc:
        raise NBCActionError("period exceeds independently verified ESM plateau; full spectral Eq 4.1(2) not yet implemented")
    return {"code":CODE_EDITION,"clause":"4.1.2/Table 4-1",
            "source":SOURCE_URL,"analysis_method":"ESM",
            "soil_type":soil_type,"period_s":t,"plateau_Tc_s":tc,
            "spectral_shape_Ch":peak}


def rc_mrf_esm_design_coefficients(
    shape_factor: float, seismic_zoning_Z: float, importance_I: float
) -> dict:
    """Table 5-2 RC moment resisting frame: Rmu=4, O_u=1.5, O_s=1.25.
    ULS: 6.1.1; SLS: 4.2 and 6.1.2.
    Source-cited arithmetic only, not a site or structure approval.
    """
    ch=_positive(shape_factor,"shape_factor")
    Z=_positive(seismic_zoning_Z,"seismic_zoning_Z")
    I=_positive(importance_I,"importance_I")
    elastic=ch*Z*I
    if not math.isfinite(elastic):raise NBCActionError("spectral input overflow")
    return {"code":CODE_EDITION,
            "clauses":["4.1.1","4.2","5.3.2","5.3.3/Table 5-2","6.1.1","6.1.2"],
            "source":SOURCE_URL,"structural_system":"RC_MOMENT_RESISTING_FRAME",
            "C_elastic":elastic,"Cd_uls":elastic/(4*1.5),
            "Cd_sls":0.2*elastic/1.25,
            "Rmu":4.,"Omega_uls":1.5,"Omega_sls":1.25}


def period_vertical_distribution_exponent(period_s: float) -> float:
    """Section 6.3 exponent k: 1 up to T=.5; 2 at T=2.5 and above."""
    t=_positive(period_s,"period_s")
    if t<=0.5:return 1.
    if t>=2.5:return 2.
    return 1.+(t-0.5)/2.


def seismic_story_forces(
    assembly: Mapping, elevations_m: Mapping[str,float],
    design_coefficient: float, design_period_s: float
) -> dict:
    """§§6.2–6.3. Inputs MUST be the audited load-to-mass assembly.
    No fabricated story weights, mass fractions or zoning.
    """
    if not isinstance(assembly,Mapping) or assembly.get("schema")!="jp.structural.load_mass_assembly.v0.1":
        raise NBCActionError("verified load-to-mass assembly required")
    coef=_positive(design_coefficient,"design_coefficient")
    period=_positive(design_period_s,"design_period_s")
    w=_positive(assembly.get("total_seismic_weight_kN"),"total_seismic_weight_kN")
    if not isinstance(elevations_m,Mapping):
        raise NBCActionError("explicit storey elevation mapping required")
    rows=assembly.get("storeys",[])
    if not rows or set(elevations_m)!={x["storey_id"] for x in rows}:
        raise NBCActionError("storey elevation and allocated mass source mismatch")
    levels=[{"id":r["storey_id"],"seismic_weight":_positive(r["seismic_weight_kN"],"story seismic weight"),
             "height_above_base":_positive(elevations_m[r["storey_id"]],"story elevation")}
            for r in rows]
    if not math.isclose(math.fsum(x["seismic_weight"] for x in levels),w,rel_tol=1e-10,abs_tol=1e-8):
        raise NBCActionError("story seismic weights do not sum to assembly source")
    V=coef*w
    if not math.isfinite(V):raise NBCActionError("base shear overflow")
    k=period_vertical_distribution_exponent(period)
    forces=vertical_force_distribution(levels,V,k)
    if not math.isclose(math.fsum(x["lateral_force"] for x in forces),V,rel_tol=1e-10,abs_tol=1e-8):
        raise NBCActionError("seismic floor forces fail horizontal balance")
    return {"code":CODE_EDITION,"clauses":["5.2","6.2","6.3"],"source":SOURCE_URL,
            "status":"SOURCE_ALIGNED_EQUILIBRIUM_PASS_NOT_APPROVED_DESIGN",
            "base_shear_kN":V,"seismic_weight_kN":w,"height_exponent":k,"levels":forces}


def accidental_torsion_pairs(lateral_force_kN: float, perpendicular_plan_dimension_m: float) -> dict:
    """§5.6: ±0.05*b; reports ±F*e, NOT finished FE torsional analysis."""
    f=_positive(lateral_force_kN,"lateral_force_kN")
    b=_positive(perpendicular_plan_dimension_m,"perpendicular_plan_dimension_m")
    e=.05*b
    M=f*e
    if not math.isfinite(M):raise NBCActionError("torsion overflow")
    return {"code":CODE_EDITION,"clause":"5.6","source":SOURCE_URL,
            "eccentricity_m":e,"torques_kNm":[-M,M],
            "state":"TORQUE_ACTION_GENERATED_NOT_FE_APPLIED"}


def check_design_interstory_drift(
    design_interstory_displacement_m: float, storey_height_m: float,
    limit_state: str, *, design_displacement_verified: bool
) -> dict:
    """§5.5.3: 0.025 ULS, 0.006 SLS.
    The input must be the correct design deflection under §5.5.1,
    including required ULS displacement scaling, never raw solver u.
    """
    if design_displacement_verified is not True:
        raise NBCActionError("verification of design (not raw analysis) displacement required")
    d=_positive(design_interstory_displacement_m,"design_interstory_displacement_m")
    h=_positive(storey_height_m,"storey_height_m")
    limits={"ULS":.025,"SLS":.006}
    if limit_state not in limits:
        raise NBCActionError("limit state must be ULS/SLS")
    drift=d/h
    return {"code":CODE_EDITION,"clause":"5.5.3","source":SOURCE_URL,
            "limit_state":limit_state,"drift_ratio":drift,
            "code_limit_ratio":limits[limit_state],"result":"PASS" if drift<=limits[limit_state] else "FAIL"}


def mrsm_base_shear_scaling(
    equivalent_static_base_shear_kN: float, modal_base_shear_kN: float
) -> dict:
    """§7.5 forces/reactions scale when VR<V, drift & displacement DO NOT."""
    v=_positive(equivalent_static_base_shear_kN,"equivalent_static_base_shear_kN")
    vr=_positive(modal_base_shear_kN,"modal_base_shear_kN")
    factor=max(1.,v/vr)
    if not math.isfinite(factor):raise NBCActionError("modal scale overflow")
    return {"code":CODE_EDITION,"clause":"7.5","source":SOURCE_URL,
            "member_force_factor":factor,"storey_shear_factor":factor,
            "base_reaction_factor":factor,
            "drift_factor":1.,"displacement_factor":1.,
            "code_limit":"No claim that modal mass sufficiency or missing-mass correction is satisfied"}
