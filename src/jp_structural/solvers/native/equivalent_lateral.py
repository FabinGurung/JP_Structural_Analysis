"""Code-edition-neutral arithmetic for explicit equivalent lateral loads.
NOT an NBC 105:2025 compliance/design module. No E2K or ETABS dependency.
"""
from __future__ import annotations
import math
from typing import Mapping, Sequence

class ExplicitSeismicInputError(ValueError):
    """Missing or invalid authoritative seismic input."""

def positive(value: object, name: str) -> float:
    if isinstance(value, bool):
        raise ExplicitSeismicInputError(f'{name} must be numeric')
    try: number=float(value)
    except (TypeError, ValueError) as exc:
        raise ExplicitSeismicInputError(f'{name} must be numeric') from exc
    if not math.isfinite(number) or number<=0:
        raise ExplicitSeismicInputError(f'{name} must be finite and >0')
    return number

def empirical_period(height: float, coefficient: float, exponent: float, amplification: float) -> float:
    """T=a*kt*H**p; ALL parameters must be supplied and source-traced."""
    h=positive(height,'height'); c=positive(coefficient,'coefficient')
    p=positive(exponent,'exponent'); a=positive(amplification,'amplification')
    return positive(a*c*h**p,'computed_period')

def period_distribution_exponent(period: float, low_period: float, high_period: float,
                                 low_exponent: float, high_exponent: float) -> float:
    """Interpolation boundaries are supplied, NOT implicit NBC normative rules."""
    t=positive(period,'period'); lo=positive(low_period,'low_period')
    hi=positive(high_period,'high_period')
    klo=positive(low_exponent,'low_exponent')
    khi=positive(high_exponent,'high_exponent')
    if hi<=lo:raise ExplicitSeismicInputError('high_period must exceed low_period')
    if khi<klo:raise ExplicitSeismicInputError('high_exponent must >= low_exponent')
    if t<=lo:return klo
    if t>=hi:return khi
    return klo+(t-lo)*(khi-klo)/(hi-lo)

def report_coefficient_arithmetic(shape_factor: float, seismic_hazard_factor: float,
                                  importance_factor: float, ductility_factor: float,
                                  overstrength_uls: float, overstrength_sls: float,
                                  serviceability_spectrum_factor: float) -> dict[str,float]:
    """Given C=Ch*Z*I compute C_ULS=C/(R*OmegaU), C_SLS=s*C/OmegaS.
    These are supplied algebraic inputs, NOT a verified code clause.
    """
    ch=positive(shape_factor,'shape_factor')
    z=positive(seismic_hazard_factor,'seismic_hazard_factor')
    i=positive(importance_factor,'importance_factor')
    r=positive(ductility_factor,'ductility_factor')
    ou=positive(overstrength_uls,'overstrength_uls')
    os=positive(overstrength_sls,'overstrength_sls')
    s=positive(serviceability_spectrum_factor,'serviceability_spectrum_factor')
    elastic=ch*z*i
    return {'elastic_spectral_factor':elastic,'uls_coefficient':elastic/(r*ou),
            'sls_coefficient':s*elastic/os}

def vertical_force_distribution(levels: Sequence[Mapping[str,object]], total_base_shear: float,
                                height_exponent: float) -> list[dict[str,float|str]]:
    """Fi=V*Wi*hi**k / SUM(Wj*hj**k); forces conserve total base shear."""
    v=positive(total_base_shear,'total_base_shear')
    k=positive(height_exponent,'height_exponent')
    if not isinstance(levels,(list,tuple)) or not levels:
        raise ExplicitSeismicInputError('nonempty levels required')
    observed=set(); prepared=[]
    for level in levels:
        name=level.get('id') if isinstance(level,dict) else None
        if not isinstance(name,str) or not name or name in observed:
            raise ExplicitSeismicInputError('unique string level id required')
        observed.add(name)
        w=positive(level.get('seismic_weight'),'seismic_weight')
        h=positive(level.get('height_above_base'),'height_above_base')
        prepared.append((name,w,h,w*h**k))
    denom=math.fsum(row[3] for row in prepared)
    positive(denom,'total_vertical_weight')
    result=[{'level_id':name,'seismic_weight':w,'height_above_base':h,
             'distribution_fraction':f/denom,'lateral_force':v*f/denom}
            for name,w,h,f in prepared]
    if not math.isclose(math.fsum(r['lateral_force'] for r in result),v,rel_tol=1e-12,abs_tol=1e-10):
        raise ExplicitSeismicInputError('sum(Fi) must equal V')
    return result
