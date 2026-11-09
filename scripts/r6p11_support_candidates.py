"""R6.11 candidate source-corner contacts; does NOT establish vertical force transfer."""
from math import dist

TOLERANCE_MM = 0.001
CANDIDATE_GROUPS = (
    ("GF_F56", "GF", "GF group of five", "GF:F56", "SHELL", ("56", "75"),
     (("GF:W2", "115"), ("GF:W2", "123"), ("GF:W6", "132"), ("GF:W6", "133"))),
    ("FF_F56", "FF", "FF group of five", "FF:F56", "SHELL", ("56", "75"),
     (("FF:W2", "115"), ("FF:W2", "123"), ("FF:W6", "132"), ("FF:W6", "133"))),
    ("FF_B27", "FF", "FF group of two", "FF:B27", "FRAME", ("26", "27"),
     (("FF:W3", "71"), ("FF:W4", "72"))),
)

def point_to_edge(p, a, b):
    vector=[b[i]-a[i] for i in range(3)]
    square=sum(v*v for v in vector)
    if square <= 0:
        raise ValueError("Degenerate source segment")
    fraction=sum((p[i]-a[i])*vector[i] for i in range(3))/square
    t=max(0.0,min(1.0,fraction))
    projection=[a[i]+t*vector[i] for i in range(3)]
    return fraction,dist(p,projection)

def contact_audit(model, unsupported):
    shells={s["key"]:s for s in model["shells"]}
    members={m["key"]:m for m in model["members"]}
    if len(unsupported)!=12 or not set(unsupported).issubset(shells):
        raise ValueError("Original 12-shell HOLD changed")
    groups=[]
    for gid,story,label,target_key,target_kind,ids,points in CANDIDATE_GROUPS:
        target=(shells if target_kind=="SHELL" else members)[target_key]
        source_ids=[str(k) for k in target["point_ids"]]
        if not all(i in source_ids for i in ids):
            raise ValueError("Source target edge changed: "+target_key)
        if target_kind=="SHELL":
            edge=[target["vertices_xyz_mm"][source_ids.index(i)] for i in ids]
        else:
            positions=[target["start_xyz_mm"],target["end_xyz_mm"]]
            edge=[positions[source_ids.index(i)] for i in ids]
        rows=[]
        for key,pid in points:
            source=shells[key]
            source_ids=[str(x) for x in source["point_ids"]]
            if key not in unsupported or pid not in source_ids:
                raise ValueError("Source point changed: "+key+" / "+pid)
            xyz=source["vertices_xyz_mm"][source_ids.index(pid)]
            fraction,offset=point_to_edge(xyz,*edge)
            rows.append({
              "source_shell":key,"corner_source_id":pid,
              "xyz_mm":[round(float(x),6) for x in xyz],
              "edge_fraction_from_first_endpoint":round(fraction,8),
              "three_dimensional_gap_mm":round(offset,8),
              "geometry_within_tolerance":0<=fraction<=1 and offset<=TOLERANCE_MM,
              "native_generated_joint_verified":False,"constraint_verified":False,
              "gravity_vertical_transfer_verified":False,"admission":"ENGINEERING_HOLD"
            })
        groups.append({"id":gid,"story":story,"label":label,"target_key":target_key,
            "target_kind":target_kind,"edge_source_point_ids":list(ids),
            "edge_xyz_mm":edge,"candidates":rows,
            "geometric_matches":sum(r["geometry_within_tolerance"] for r in rows),
            "support_admitted":False})
    if sum(len(g["candidates"]) for g in groups)!=10:
        raise ValueError("R6.11 candidate count changed")
    return {
      "schema":"jp.structural.r6p11.geometric_contacts.v0.1",
      "source_tolerance_mm":TOLERANCE_MM,
      "candidate_source_corners":10,"groups":groups,
      "original_unsupported_shells":12,"unsupported_shells_still_excluded":True,
      "native_ETABS21_joint_mesh_constraint_output_verified":False,
      "ETABS21_supported_gravity_reactions_verified":False,
      "full_mass_verified":False,"accidental_eccentricity_verified":False,
      "native_mesh_equivalence_verified":False,"engineering_approval":False,
      "F3_one_way_shear_unsafe":True,"support_gate_passed":False,
      "next_step":"Export actual ETABS21 ULS/SLS generated analysis joints, shell/frame connectivity, edge constraints, signed gravity reactions and prove vertical force transfer."
    }
