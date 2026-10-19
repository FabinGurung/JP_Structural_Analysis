"""Independent, bounded first-party 3D Euler–Bernoulli frame solver.

Unlike the OpenSees adapter, this uses only NumPy and a separately assembled
12-DOF stiffness matrix. Its purpose is independent equilibrium and response
comparison on source-labelled ELASTIC FRAME hypotheses, not final RC design.

Inputs are 3D SI kN/m, linear elastic, rigid member ends, fixed 6-DOF base.
No shell/surface loads, source-default member release, offsets, P-Delta,
soil springs, nonlinear response or phase-coherent seismic modal combination.
All actual project inputs belong outside the public GitHub repository.
"""
from __future__ import annotations
import hashlib
import json
import math

import numpy as np

SCHEMA = "jp.structural.native_3d_elastic_frame.v0.1"
DOFS = ("N", "Vy", "Vz", "T", "My", "Mz")


class IndependentFrameError(ValueError):
    """Invalid assumptions or failed stiffness/equilibrium closure."""


def _f(value, label, *, positive=False):
    if isinstance(value, bool):
        raise IndependentFrameError(f"{label}: no boolean numeric inputs")
    try:
        x = float(value)
    except (ValueError, TypeError, OverflowError) as exc:
        raise IndependentFrameError(f"{label}: finite numeric value required") from exc
    if not math.isfinite(x) or (positive and x <= 0):
        raise IndependentFrameError(f"{label}: invalid {'positive ' if positive else ''}numeric value")
    return x


def _id(row, field):
    value = row.get(field) if isinstance(row, dict) else None
    if not isinstance(value, str) or not value.strip():
        raise IndependentFrameError(f"{field}: source-linked text ID required")
    return value.strip()


def _local_k(E, G, A, Iy, Iz, J, L):
    """Standard 12x12 3D frame stiffness in [u,v,w,rx,ry,rz] I/J order."""
    k = np.zeros((12, 12))
    for i, j, v in ((0,0,1),(0,6,-1),(6,0,-1),(6,6,1)):
        k[i,j] += v*E*A/L
    for i,j,v in ((3,3,1),(3,9,-1),(9,3,-1),(9,9,1)):
        k[i,j] += v*G*J/L
    v = [1,5,7,11]
    zb = np.array([[12,6*L,-12,6*L],
                   [6*L,4*L*L,-6*L,2*L*L],
                   [-12,-6*L,12,-6*L],
                   [6*L,2*L*L,-6*L,4*L*L]])*E*Iz/L**3
    k[np.ix_(v,v)] += zb
    w = [2,4,8,10]
    yb = np.array([[12,-6*L,-12,-6*L],
                   [-6*L,4*L*L,6*L,2*L*L],
                   [-12,6*L,12,6*L],
                   [-6*L,2*L*L,6*L,4*L*L]])*E*Iy/L**3
    k[np.ix_(w,w)] += yb
    return k


def _transform(direction):
    e1 = direction/np.linalg.norm(direction)
    # Horizontal beams have local +y nominally upward; columns use a
    # horizontal local y. All axis assumptions explicitly returned.
    ref = np.array([0.,1.,0.]) if abs(e1[2]) > .9 else np.array([0.,0.,1.])
    e2 = ref - (ref @ e1)*e1
    e2 /= np.linalg.norm(e2)
    e3 = np.cross(e1,e2)
    R = np.stack((e1,e2,e3))
    T = np.zeros((12,12))
    for i in (0,3,6,9):
        T[i:i+3,i:i+3] = R
    return T,R


def _section(row):
    shape = row.get("shape")
    if shape == "RECTANGLE":
        b = _f(row.get("width_mm"), "width_mm", positive=True)/1000
        d = _f(row.get("depth_mm"), "depth_mm", positive=True)/1000
        a = b*d
        iy = d*b**3/12
        iz = b*d**3/12
        hi,lo = max(b,d),min(b,d)
        j = hi*lo**3*(1/3-.21*lo/hi*(1-lo**4/(12*hi**4)))
    elif shape == "CIRCLE":
        diameter = _f(row.get("diameter_mm"), "diameter_mm", positive=True)/1000
        a = math.pi*diameter**2/4
        iy = iz = math.pi*diameter**4/64
        j = math.pi*diameter**4/32
    else:
        raise IndependentFrameError("only explicit RECTANGLE or CIRCLE sections supported")
    return a,iy,iz,j


def _member(member, xyz, indices, n_nodes):
    mid = _id(member,"member_id")
    _id(member,"source_id")
    i,j = _id(member,"i_node"),_id(member,"j_node")
    if i == j or i not in xyz or j not in xyz:
        raise IndependentFrameError(f"{mid}: distinct existing end nodes required")
    if any(field in member for field in ("offsets","releases","shell_mapping","p_delta")):
        raise IndependentFrameError(f"{mid}: unreconciled release/offset/shell/P-Delta unsupported")
    v = xyz[j]-xyz[i]
    L = float(np.linalg.norm(v))
    if not .001 < L < 1000:
        raise IndependentFrameError(f"{mid}: invalid physical length")
    E = _f(member.get("E_MPa"),"E_MPa",positive=True)*1000
    nu = _f(member.get("poisson_ratio"),"poisson_ratio")
    if not -.9 < nu < .49:
        raise IndependentFrameError("Poisson ratio must represent a stable elastic solid")
    G = E/(2*(1+nu))
    rho = _f(member.get("weight_kN_m3"),"weight_kN_m3",positive=True)
    a,iy,iz,jprop = _section(member)
    K = _local_k(E,G,a,iy,iz,jprop,L)
    T,R = _transform(v)
    dofs=np.r_[np.arange(6*indices[i],6*indices[i]+6),
               np.arange(6*indices[j],6*indices[j]+6)]
    # Consistent uniform self-weight in local axes
    qx,qy,qz=R@np.array((0.,0.,-rho*a))
    f=np.zeros(12)
    f[[0,6]] = qx*L/2
    f[[1,7]] = qy*L/2
    f[5] = qy*L*L/12
    f[11] = -qy*L*L/12
    f[[2,8]] = qz*L/2
    f[4] = -qz*L*L/12
    f[10] = qz*L*L/12
    return {"id":mid,"source_id":member["source_id"],"i":i,"j":j,
            "dofs":dofs,"k":K,"T":T,"R":R,"L":L,
            "global_k":T.T@K@T,"selfweight_global":T.T@f,
            "selfweight_local":f}


def solve_linear_static_cases(*, model_id, nodes, members, fixed_node_ids,
                              load_cases, monitored_node_ids=None):
    """Solve explicit named static cases, verifying each six-component free body.

    Each case: {case_id, source_id, selfweight: bool,
      nodal_loads: [{node_id,Fx_kN,Fy_kN,Fz_kN,Mx_kNm,My_kNm,Mz_kNm}]}
    """
    if not isinstance(model_id, str) or not model_id.strip():
        raise IndependentFrameError("model_id required")
    if any(not isinstance(x,(list,tuple)) or not x for x in (nodes,members,fixed_node_ids,load_cases)):
        raise IndependentFrameError("nonempty list of nodes, members, supports and cases required")
    xyz={}
    for row in nodes:
        nid=_id(row,"node_id")
        if nid in xyz:
            raise IndependentFrameError("duplicate node ID")
        xyz[nid]=np.array([_f(row[k],k) for k in ("x_m","y_m","z_m")])
    ids=sorted(xyz)
    indices={k:i for i,k in enumerate(ids)}
    if len(set(fixed_node_ids))!=len(fixed_node_ids) or any(x not in xyz for x in fixed_node_ids):
        raise IndependentFrameError("unique source-linked existing fixed supports required")
    if monitored_node_ids is None:
        monitored_node_ids=ids
    if any(x not in xyz for x in monitored_node_ids) or not monitored_node_ids:
        raise IndependentFrameError("monitored_node_ids must be nonempty existing nodes")
    n=6*len(ids)
    global_k=np.zeros((n,n))
    element_records=[]
    seen=set()
    for row in members:
        el=_member(row,xyz,indices,len(ids))
        if el["id"] in seen:
            raise IndependentFrameError("duplicate member ID")
        seen.add(el["id"])
        global_k[np.ix_(el["dofs"],el["dofs"])]+=el["global_k"]
        element_records.append(el)
    fixed=sorted(6*indices[x]+j for x in fixed_node_ids for j in range(6))
    free=np.setdiff1d(np.arange(n), fixed)
    stiff=global_k[np.ix_(free,free)]
    if not np.allclose(stiff,stiff.T,rtol=1e-10,atol=1e-5):
        raise IndependentFrameError("assembled frame stiffness not symmetric")
    try:
        np.linalg.cholesky(stiff)
    except np.linalg.LinAlgError as exc:
        raise IndependentFrameError("unstable/singular supported frame hypothesis") from exc
    payload=json.dumps({"model_id":model_id,"nodes":nodes,"members":members,
                        "fixed_node_ids":fixed_node_ids,"load_cases":load_cases},
                        sort_keys=True,separators=(",",":"),allow_nan=False)
    solutions=[]
    for case in load_cases:
        caseid=_id(case,"case_id")
        sourceid=_id(case,"source_id")
        if "selfweight" not in case or not isinstance(case["selfweight"],bool):
            raise IndependentFrameError("every case must explicitly include selfweight bool")
        F=np.zeros(n)
        if case["selfweight"]:
            for el in element_records:
                F[el["dofs"]]+=el["selfweight_global"]
        nodal=case.get("nodal_loads")
        if not isinstance(nodal,list):
            raise IndependentFrameError("nodal_loads required even if empty")
        used=set()
        for load in nodal:
            nid=_id(load,"node_id")
            if nid not in indices or nid in used or set(load)!={"node_id","Fx_kN","Fy_kN","Fz_kN","Mx_kNm","My_kNm","Mz_kNm"}:
                raise IndependentFrameError("unknown/duplicated node or incomplete six signed loads")
            used.add(nid)
            F[6*indices[nid]:6*indices[nid]+6]+=[_f(load[key],key) for key in
                ("Fx_kN","Fy_kN","Fz_kN","Mx_kNm","My_kNm","Mz_kNm")]
        u=np.zeros(n)
        try:
            u[free]=np.linalg.solve(stiff,F[free])
        except np.linalg.LinAlgError as exc:
            raise IndependentFrameError("static solution failed") from exc
        if not np.all(np.isfinite(u)):
            raise IndependentFrameError("nonfinite displacement")
        R=global_k@u-F
        free_residual=max(abs(R[free])) if len(free) else 0
        eq=np.zeros(6)
        for nid in ids:
            p=xyz[nid]
            vec=F[6*indices[nid]:6*indices[nid]+6].copy()
            if nid in fixed_node_ids:
                vec+=R[6*indices[nid]:6*indices[nid]+6]
            fx,fy,fz,mx,my,mz=vec
            eq+=np.array((fx,fy,fz,
                mx+p[1]*fz-p[2]*fy,
                my+p[2]*fx-p[0]*fz,
                mz+p[0]*fy-p[1]*fx))
        eq_tol=max(1e-5,1e-8*max(1,sum(abs(F))))
        if max(abs(eq))>eq_tol or free_residual>eq_tol:
            raise IndependentFrameError(f"global frame equilibrium FAIL {caseid}")
        actions=[]
        for el in element_records:
            local=el["k"]@(el["T"]@u[el["dofs"]])
            if case["selfweight"]:
                local-=el["selfweight_local"]
            actions.append({
                "member_id":el["id"],"source_id":el["source_id"],
                "I":dict(zip(DOFS,[float(x) for x in local[:6]])),
                "J":dict(zip(DOFS,[float(x) for x in local[6:]])),
            })
        solutions.append({
            "case_id":caseid,"source_id":sourceid,
            "max_monitor_displacement_m":max(float(np.linalg.norm(u[6*indices[k]:6*indices[k]+3])) for k in monitored_node_ids),
            "free_dof_residual":float(free_residual),
            "global_equilibrium_residuals":[float(x) for x in eq],
            "reaction_totals_Fx_Fy_Fz_kN":[float(sum(R[6*indices[k]+j] for k in fixed_node_ids)) for j in range(3)],
            "member_end_actions":actions,
            "engineering_approval":False
        })
    return {
        "schema":SCHEMA,"model_id":model_id,
        "source_bundle_sha256":hashlib.sha256(payload.encode()).hexdigest(),
        "member_count":len(element_records),"node_count":len(ids),
        "solver":"INDEPENDENT_NUMPY_3D_EULER_BERNOULLI_FRAME",
        "local_axis_policy":"HORIZONTAL_BEAMS_LOCAL_Y_UP; VERTICAL_COLUMNS_LOCAL_Y_HORIZONTAL",
        "cases":solutions,
        "scope":"ELASTIC_FIXED_SUPPORTS_EXPLICIT_LOADS_NOT_CODE_SEISMIC_DESIGN",
        "engineering_approval":False
    }
