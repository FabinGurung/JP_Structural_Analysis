"""Deterministic source-to-node gravity and seismic mass allocation.

This is NOT a tributary-area geometry solver and never invents wall positions,
NBC live-load participation, member self-weight or diaphragm connectivity.
Explicit source-key uniqueness prevents accidental duplicate components.
Canonical force/length/time units: kN, m, s; mass in kN*s^2/m = metric tonne.
"""
from __future__ import annotations
from collections import defaultdict
from collections.abc import Mapping, Sequence
import math

class LoadAssemblyError(ValueError):
    """Invalid or non-conservative load-to-mass mapping."""


def _number(value: object, field: str, *, zero_ok: bool = False) -> float:
    if isinstance(value, bool):
        raise LoadAssemblyError(f"{field}: boolean not allowed")
    try:
        n = float(value)
    except (TypeError, ValueError) as exc:
        raise LoadAssemblyError(f"{field}: numeric value required") from exc
    if not math.isfinite(n) or (n < 0 if zero_ok else n <= 0):
        raise LoadAssemblyError(f"{field}: finite {'nonnegative' if zero_ok else 'positive'} number required")
    return n


def _id(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LoadAssemblyError(f"{field}: nonempty string required")
    return value


def _check_close(actual: float, expected: float, field: str, *, relative: float = 1e-10, absolute: float = 1e-9):
    if not math.isclose(actual, expected, rel_tol=relative, abs_tol=absolute):
        raise LoadAssemblyError(f"{field} equilibrium failure: {actual:.12g} versus {expected:.12g}")


def allocate_loads_to_nodes(
    nodes: Sequence[Mapping],
    components: Sequence[Mapping],
    gravity_m_s2: float,
) -> dict:
    """Return independently auditable gravity nodal loads and seismic nodal masses.

    components contain id, source_key, load_category, downward_load_kN,
    participation_factor (caller supplied), node_shares=[{node_id,fraction}].
    A component is a known total load, not a pressure without tributary area.
    """
    g = _number(gravity_m_s2, "gravity_m_s2")
    if not isinstance(nodes, (list, tuple)) or not nodes:
        raise LoadAssemblyError("explicit nonempty node list required")
    if not isinstance(components, (list, tuple)) or not components:
        raise LoadAssemblyError("explicit nonempty source components required")
    node_map: dict[str, dict] = {}
    for n in nodes:
        if not isinstance(n, Mapping):
            raise LoadAssemblyError("node must be mapping")
        nid = _id(n.get("node_id"), "node_id")
        if nid in node_map:
            raise LoadAssemblyError(f"duplicate node: {nid}")
        sid = _id(n.get("storey_id"), f"{nid}.storey_id")
        # Local models may use signed coordinates; do not restrict to first quadrant.
        try:
            x, y, z = (float(n[v]) for v in ("x_m", "y_m", "z_m"))
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            raise LoadAssemblyError(f"{nid}: finite x_m/y_m/z_m required") from exc
        if not all(math.isfinite(c) for c in (x, y, z)):
            raise LoadAssemblyError(f"{nid}: nonfinite coordinates")
        node_map[nid] = {"storey_id": sid, "x_m": x, "y_m": y, "z_m": z}
    downward = defaultdict(float)
    seismic = defaultdict(float)
    by_source = []
    component_ids: set[str] = set()
    physical_keys: set[str] = set()
    for c in components:
        if not isinstance(c, Mapping):
            raise LoadAssemblyError("component must be mapping")
        cid = _id(c.get("id"), "component.id")
        source_key = _id(c.get("source_key"), f"{cid}.source_key")
        category = _id(c.get("load_category"), f"{cid}.load_category")
        if cid in component_ids or source_key in physical_keys:
            raise LoadAssemblyError(f"duplicate component or physical source key: {cid}/{source_key}")
        component_ids.add(cid); physical_keys.add(source_key)
        weight = _number(c.get("downward_load_kN"), f"{cid}.downward_load_kN", zero_ok=True)
        participation = _number(c.get("participation_factor"), f"{cid}.participation_factor", zero_ok=True)
        if participation > 1:
            raise LoadAssemblyError(f"{cid}: participation fraction >1")
        shares = c.get("node_shares")
        if not isinstance(shares, (list, tuple)) or not shares:
            raise LoadAssemblyError(f"{cid}: node tributaries missing")
        seen = set()
        weights = []
        for share in shares:
            if not isinstance(share, Mapping):
                raise LoadAssemblyError(f"{cid}: invalid tributary")
            nid = _id(share.get("node_id"), f"{cid}.node_id")
            if nid not in node_map or nid in seen:
                raise LoadAssemblyError(f"{cid}: tributary node unknown/duplicated: {nid}")
            seen.add(nid)
            fraction = _number(share.get("fraction"), f"{cid}.fraction", zero_ok=True)
            if fraction > 1:
                raise LoadAssemblyError(f"{cid}: fraction >1")
            weights.append((nid, fraction))
        _check_close(math.fsum(f for _, f in weights), 1.0, f"{cid}.tribuary_fractions")
        for nid, fraction in weights:
            downward[nid] += weight*fraction
            seismic[nid] += weight*participation*fraction
        by_source.append({"id": cid, "source_key": source_key, "load_category": category,
                          "gravity_weight_kN": weight, "seismic_weight_kN": weight*participation})
    total_downward = math.fsum(x["gravity_weight_kN"] for x in by_source)
    total_seismic = math.fsum(x["seismic_weight_kN"] for x in by_source)
    if total_downward <= 0 or total_seismic <= 0 or not all(math.isfinite(x) for x in (total_downward, total_seismic)):
        raise LoadAssemblyError("positive, finite gravity and seismic totals required")
    _check_close(math.fsum(downward.values()), total_downward, "gravity vertical force")
    _check_close(math.fsum(seismic.values()), total_seismic, "seismic mass source")
    storeys = defaultdict(lambda: {"gravity_kN": 0., "seismic_weight_kN": 0.,
                                   "weighted_x": 0., "weighted_y": 0.})
    nodal_gravity, nodal_masses = [], []
    for nid, n in node_map.items():
        down, w = downward[nid], seismic[nid]
        if down > 0:
            nodal_gravity.append({"node_id": nid, "downward_load_kN": down})
        if w > 0:
            m = w/g
            if not math.isfinite(m):
                raise LoadAssemblyError("mass overflow")
            nodal_masses.append({"node_id": nid, "mx": m, "my": m, "mz": m,
                                 "mrx": 0., "mry": 0., "mrz": 0.})
        s = storeys[n["storey_id"]]
        s["gravity_kN"] += down
        s["seismic_weight_kN"] += w
        s["weighted_x"] += n["x_m"]*w
        s["weighted_y"] += n["y_m"]*w
    _check_close(math.fsum(x["mx"] for x in nodal_masses)*g, total_seismic, "mass-weight conservation")
    result_storeys=[]
    for sid, s in sorted(storeys.items()):
        if s["seismic_weight_kN"] > 0:
            result_storeys.append({"storey_id": sid, "gravity_kN": s["gravity_kN"],
                                  "seismic_weight_kN": s["seismic_weight_kN"],
                                  "center_mass_x_m": s["weighted_x"]/s["seismic_weight_kN"],
                                  "center_mass_y_m": s["weighted_y"]/s["seismic_weight_kN"]})
    return {"schema":"jp.structural.load_mass_assembly.v0.1",
            "formula_id":"JP-LOAD-MASS-PLACEMENT-006",
            "status":"SOURCE_ASSIGNED_NUMERIC_CONSERVATION_PASS_NOT_ENGINEERING_APPROVAL",
            "units":{"force":"kN","length":"m","time":"s","mass":"kN*s^2/m"},
            "source_nodes":[{"node_id":nid, **n} for nid,n in node_map.items()],
            "gravity_m_s2":g,"total_gravity_load_kN":total_downward,
            "total_seismic_weight_kN":total_seismic,
            "gravity_nodal_loads":nodal_gravity,"nodal_masses":nodal_masses,
            "storeys":result_storeys,"sources":by_source}


def verify_vertical_support_equilibrium(nodes: Sequence[Mapping],
                                        nodal_gravity_loads: Sequence[Mapping],
                                        support_reactions: Sequence[Mapping],
                                        *, rel_tol: float = 1e-8, abs_tol: float = 1e-7) -> dict:
    """Check independent solver support Rz and moments against nodal gravity.

    Fz loads are DOWNWARD. Reactions Rz are UPWARD. Positive Mx/My use
    right-handed global axes. Support nodal couples Mx/My are included.
    Passing equilibrium alone DOES NOT establish local force accuracy.
    """
    if not nodes or not nodal_gravity_loads or not support_reactions:
        raise LoadAssemblyError("nonempty source, gravity and reaction lists required")
    pts={}
    for n in nodes:
        k=_id(n.get("node_id"), "node_id")
        if k in pts:
            raise LoadAssemblyError("duplicate geometric node")
        try:
            x,y=float(n["x_m"]),float(n["y_m"])
        except (KeyError, TypeError, ValueError) as exc:
            raise LoadAssemblyError("invalid reaction geometry") from exc
        if not (math.isfinite(x) and math.isfinite(y)):
            raise LoadAssemblyError("nonfinite reaction coordinates")
        pts[k]=(x,y)
    def evaluate(records, mag, sign):
        used=set(); forces=[]; mxs=[]; mys=[]
        for item in records:
            k=_id(item.get("node_id"), "response node_id")
            if k not in pts or k in used:
                raise LoadAssemblyError(f"invalid/duplicate response node {k}")
            used.add(k)
            x,y=pts[k]
            if sign==1:
                try:
                    z=float(item[mag])
                except (KeyError, TypeError, ValueError) as exc:
                    raise LoadAssemblyError("invalid signed support reaction") from exc
                if not math.isfinite(z):
                    raise LoadAssemblyError("nonfinite support reaction")
            else:
                z=_number(item.get(mag), mag, zero_ok=True)
            f=sign*z
            mx=y*f
            my=-x*f
            if sign==1:
                for field, arr in (("Mx_kNm",mxs),("My_kNm",mys)):
                    try: couple=float(item.get(field,0))
                    except (ValueError, TypeError) as exc: raise LoadAssemblyError("invalid reaction couple") from exc
                    if not math.isfinite(couple):raise LoadAssemblyError("nonfinite reaction couple")
                    arr.append(couple)
            forces.append(f);mxs.append(mx);mys.append(my)
        return math.fsum(forces),math.fsum(mxs),math.fsum(mys)
    react=evaluate(support_reactions,"Rz_kN",1)
    load=evaluate(nodal_gravity_loads,"downward_load_kN",-1)
    errors=[a+b for a,b in zip(react,load)]
    for name,actual,r,l in zip(("Fz_kN","Mx_kNm","My_kNm"),errors,react,load):
        if abs(actual)>max(abs_tol,rel_tol*max(abs(r),abs(l),1.)):
            raise LoadAssemblyError(f"{name} equilibrium residual: {actual:.12g}")
    return {"schema":"jp.structural.vertical_equilibrium.v0.1",
            "formula_id":"JP-LOAD-REACTION-FREEBODY-007",
            "status":"VERTICAL_GLOBAL_FORCE_AND_MOMENT_EQUILIBRIUM_PASS",
            "residual":{"Fz_kN":errors[0],"Mx_kNm":errors[1],"My_kNm":errors[2]}}
