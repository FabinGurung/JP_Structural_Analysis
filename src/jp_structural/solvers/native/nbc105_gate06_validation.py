"""NBC105:2025 Gate06 bounded post-solve helpers (never design approval).

Tested public source algorithms only. PRIVATE G15 geometry, loads and member
actions are held in governed Drive; all samples generated for Pages are
synthetic, not transformed real-project values.

NBC105:2025 §3.4 Table3-1: cracked flexural EI only. §5.2: seismic
weight DL + live factors, roof live zero. §5.6: Mz=±0.05bF for the
orthogonal plan dimension, with explicit eccentricity and load signs.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
import math

class Gate06InputError(ValueError):
    """Reject missing, unsupported, inconsistent engineering input."""


def _number(v, key, *, allow_zero=False):
    if isinstance(v,bool):
        raise Gate06InputError(key+" must be a real number")
    try: z=float(v)
    except (ValueError,TypeError,OverflowError) as exc:
        raise Gate06InputError(key+" must be a real number") from exc
    if not math.isfinite(z) or (z<0 if allow_zero else z<=0):
        raise Gate06InputError(key+" out of valid numeric range")
    return z


def effective_EI_ratios(*, limit_state, include_torsion_reduction=False,
                        beam_torsion_is_compatibility=None):
    """NBC 105:2025 §3.4 Table3-1. No blanket GJ or EA reduction."""
    if limit_state not in ("ULS","SLS","GROSS"):
        raise Gate06InputError("ULS/SLS/GROSS only")
    if not isinstance(include_torsion_reduction,bool):
        raise Gate06InputError("boolean torsion-reduction selection required")
    if include_torsion_reduction and beam_torsion_is_compatibility is not True:
        raise Gate06InputError("10% GJ is only justified for proven compatibility torsion")
    beam,col = {"GROSS":(1.,1.),"ULS":(.35,.70),"SLS":(.70,.90)}[limit_state]
    return {"limit_state":limit_state,"beam_flexural_EI_over_EcIg":beam,
      "column_flexural_EI_over_EcIg":col,
      "axial_EA_ratio":1.,
      "beam_torsional_GJ_ratio":.1 if include_torsion_reduction else 1.,
      "beam_torsion_assumption":"PROVEN_COMPATIBILITY" if include_torsion_reduction
          else "NOT_REDUCED_UNKNOWN_TORSIONAL_CLASSIFICATION",
      "code":"NBC105:2025","clause":"3.4 Table 3-1",
      "engineering_approval":False}


def signed_eccentric_floor_wrenches(*, floor_forces_kN: Sequence[float],
                                    axis, orthogonal_plan_breadth_m,
                                    eccentricity_sign, load_direction_sign=1):
    """One simultaneous horizontal F and ± eccentric Mz per floor.

    The +Mz definition is X×Fy−Y×Fx. Return global load components, not
    a solver-independent way of distributing torsion among physical nodes.
    Caller must verify diaphragm/force point and its in-plane stiffness.
    """
    if axis not in ("X","Y"):
        raise Gate06InputError("axis must be X or Y")
    if eccentricity_sign not in (-1,1) or isinstance(eccentricity_sign,bool):
        raise Gate06InputError("eccentricity_sign must be +1/-1")
    if load_direction_sign not in (-1,1) or isinstance(load_direction_sign,bool):
        raise Gate06InputError("load_direction_sign must be +1/-1")
    breadth=_number(orthogonal_plan_breadth_m,"orthogonal_plan_breadth_m")
    if not isinstance(floor_forces_kN,(list,tuple)) or not floor_forces_kN:
        raise Gate06InputError("nonempty source-labeled floor forces required")
    forces=[_number(v,"floor_forces_kN",allow_zero=True) for v in floor_forces_kN]
    e=.05*breadth
    rows=[]
    for i,v in enumerate(forces,1):
        f=load_direction_sign*v
        # Eccentricity sign is the coordinate-offset sign, not an invented
        # absolute envelope. Positive x offset under +Y gives +Mz;
        # positive y offset under +X gives -Mz.
        mz=(1 if axis=="Y" else -1)*eccentricity_sign*e*f
        rows.append({"level_index":i,"Fx_kN":f if axis=="X" else 0.,
          "Fy_kN":f if axis=="Y" else 0.,"Mz_kNm":mz})
    return {"axis":axis,"orthogonal_plan_breadth_m":breadth,
      "eccentricity_m":e,"eccentricity_sign":eccentricity_sign,
      "loading_sign":load_direction_sign,
      "level_wrenches":rows,
      "sum_signed_Fx_kN":math.fsum(row["Fx_kN"] for row in rows),
      "sum_signed_Fy_kN":math.fsum(row["Fy_kN"] for row in rows),
      "sum_signed_applied_Mz_kNm":math.fsum(row["Mz_kNm"] for row in rows),
      "distribution_to_connected_frame_nodes_verified":False,
      "verified_rigid_diaphragm":False,"engineering_approval":False,
      "code":"NBC105:2025","clause":"5.6"}


def reconcile_trial_seismic_weight(*, source_W_kN, member_dead_kN,
                                   floor_extra_dead_kN, nonroof_live_kN,
                                   roof_live_kN=0., live_factor_nonroof=.3):
    """Keep the mass shortfall visible rather than forcing the model to fit.

    Roof imposed load factor is ALWAYS 0 under NBC105:2025 §5.2 Table5-1.
    Source mass may include unmodeled walls/foundations/other geometry;
    no missing category is reverse-invented from the residual.
    """
    src=_number(source_W_kN,"source_W_kN")
    dead=_number(member_dead_kN,"member_dead_kN",allow_zero=True)
    extra=_number(floor_extra_dead_kN,"floor_extra_dead_kN",allow_zero=True)
    live=_number(nonroof_live_kN,"nonroof_live_kN",allow_zero=True)
    _number(roof_live_kN,"roof_live_kN",allow_zero=True)
    if isinstance(live_factor_nonroof,bool):
        raise Gate06InputError("live_factor must be real")
    factor=_number(live_factor_nonroof,"live_factor_nonroof",allow_zero=True)
    if factor not in (.3,.6):
        raise Gate06InputError("NBC105 Table5-1 accepts 0.3 other or 0.6 storage")
    trial=math.fsum((dead,extra,live*factor))
    gap=src-trial
    return {"source_reported_W_kN":src,"reconstructed_trial_W_kN":trial,
      "member_dead_kN":dead,"floor_extra_dead_kN":extra,
      "seismic_nonroof_live_kN":live*factor,
      "roof_live_factor":0.,
      "residual_source_minus_trial_kN":gap,
      "absolute_difference_fraction":abs(gap)/src,
      "source_to_trial_mass_closed":False,
      "missing_components_inferred":False,
      "status":"SOURCE_MASS_MISMATCH_REQUIRES_TRIBUTARY_MODEL_AUDIT",
      "engineering_approval":False,"code":"NBC105:2025","clause":"5.2 Table 5-1"}


def governing_signed_component(*, member_id: str, component: str,
                               combination_actions: Sequence[Mapping]):
    """Select one signed resultant from a specific same-case end 12-vector.

    The governing 12-vector is from the SAME concurrent combination. It is
    never the assembled absolute maxima of physically unrelated cases.
    """
    keys=("Ni","Vyi","Vzi","Ti","Myi","Mzi","Nj","Vyj","Vzj","Tj","Myj","Mzj")
    if not isinstance(member_id,str) or not member_id.strip():
        raise Gate06InputError("member_id required")
    if component not in keys:
        raise Gate06InputError("member force component must be one of 12 local DOF")
    if not isinstance(combination_actions,(tuple,list)) or not combination_actions:
        raise Gate06InputError("source combinations required")
    cases=[]
    ids=set()
    for row in combination_actions:
        case=row.get("combination_id") if isinstance(row,Mapping) else None
        vector=row.get("signed_local_end_forces") if isinstance(row,Mapping) else None
        if (not isinstance(case,str) or not case.strip() or case in ids
             or not isinstance(vector,Mapping) or set(vector)!=set(keys)):
            raise Gate06InputError("each source combination requires unique ID and all 12 signed actions")
        ids.add(case)
        values={k:float(vector[k]) if not isinstance(vector[k],bool) else float("nan") for k in keys}
        if not all(math.isfinite(v) for v in values.values()):
            raise Gate06InputError("nonfinite member force")
        cases.append((case,values))
    case,vector=max(cases,key=lambda x:abs(x[1][component]))
    return {"member_id":member_id,"governing_component":component,
       "combination_id":case,"signed_governing_value":vector[component],
       "same_case_signed_12_component_vector":vector,
       "do_not_combine_independent_case_peaks":True,
       "engineering_approval":False}
