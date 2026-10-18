"""Report-first bounded numerical RC engines, not approval of a building.

NBC 105:2025 Annex A 4.1.3 and 4.4.1.1-3, IS456:2000 §§25.4,39.6,
34.2.3,34.2.4,31.6,40.2. Explicit source/assumption IDs mandatory.
mm, MPa, kN, kNm, kPa. No full FE/member design or construction certification.
"""
import math
from jp_structural.solvers.native.rc_beam_strength import (
    rectangular_singly_reinforced_flexure, conservative_table19_shear_strength,
    RCBeamInputError,
)
NBC="https://ebps.kathmandu.gov.np/UploadFiles/NBC_105_2025_Sesmic_Design.pdf"
IS456="https://wriddodoti.gov.np/uploads/blog/20230331071217_IS-456-with-all-ammendments.pdf"

class RCDesignError(ValueError):pass

def n(v,label,zero=False):
    if isinstance(v,bool):raise RCDesignError(f"{label}: invalid boolean")
    try:x=float(v)
    except (ValueError,TypeError,OverflowError) as e:raise RCDesignError(f"{label}: numeric required") from e
    if not math.isfinite(x) or (x<0 if zero else x<=0):
        raise RCDesignError(f"{label}: finite {'nonnegative' if zero else 'positive'} required")
    return x

def evidence(s,label):
    if not isinstance(s,str) or not s.strip():raise RCDesignError(f"{label}: evidence ID required")
    return s.strip()

def nbc_capacity_design_beam_shear(*,span_mm,gravity_shear_a_kN,
    gravity_shear_b_kN,analysis_shear_a_kN,analysis_shear_b_kN,
    sway_right_moment_a_kNm,sway_right_moment_b_kNm,
    sway_left_moment_a_kNm,sway_left_moment_b_kNm,
    moment_capacity_source_id):
    """NBC105 Annex A 4.1.3(e): V=max(V_FE,V_gravity +/- 1.4(sum M_end)/L).

    End moments must be actual provided/validated hinge-strength magnitudes
    for BOTH sway directions. Gravity shears are nonnegative magnitudes and
    both algebraic signs are enveloped conservatively.
    """
    L=n(span_mm,"span_mm")/1000
    g=[n(gravity_shear_a_kN,"gravity_A",True),n(gravity_shear_b_kN,"gravity_B",True)]
    fe=[n(analysis_shear_a_kN,"analysis_A",True),n(analysis_shear_b_kN,"analysis_B",True)]
    right=1.4*(n(sway_right_moment_a_kNm,"right_Ma")+n(sway_right_moment_b_kNm,"right_Mb"))/L
    left=1.4*(n(sway_left_moment_a_kNm,"left_Ma")+n(sway_left_moment_b_kNm,"left_Mb"))/L
    if not all(math.isfinite(x) for x in (right,left)):raise RCDesignError("shear overflow")
    end=[{"end":label,"analysis_shear_kN":fe[i],"capacity_shear_sway_right_kN":right,
          "capacity_shear_sway_left_kN":left,
          "required_shear_kN":max(fe[i],abs(g[i]+right),abs(g[i]-right),abs(g[i]+left),abs(g[i]-left))}
         for i,label in enumerate(("A","B"))]
    return {"engine":"M08_NBC_CAPACITY_DESIGN_SHEAR","code":"NBC105:2025",
            "clause":"Annex A 4.1.3(e), Eqs 4.1.3.1-4.1.3.4","source":NBC,
            "moment_capacity_source_id":evidence(moment_capacity_source_id,"moment capacity"),
            "end_demands":end,"status":"DEMAND_CALCULATED_STIRRUP_CHECK_PENDING",
            "engineering_approval":False}

def is456_biaxial_column(*,width_mm,depth_mm,fck_MPa,fy_MPa,Ast_mm2,
                         Pu_kN,Mux_kNm,Muy_kNm,Mux1_kNm,Muy1_kNm,
                         clear_height_mm,effective_length_x_mm,effective_length_y_mm,
                         uniaxial_capacity_source_id):
    """Cl 39.6 Puz and alpha, plus 25.4 minimum eccentricity and short-column gate.

    Mux1/Muy1 are SOURCE-SUPPLIED independently verified uniaxial capacities
    at EXACT SAME Pu; SP16 chart calculation is a separate unsolved requirement.
    """
    b=n(width_mm,"b");D=n(depth_mm,"D");fck=n(fck_MPa,"fck");fy=n(fy_MPa,"fy")
    As=n(Ast_mm2,"Ast");Pu=n(Pu_kN,"Pu")
    Mx=n(Mux_kNm,"Mux",True);My=n(Muy_kNm,"Muy",True)
    capx=n(Mux1_kNm,"Mux1");capy=n(Muy1_kNm,"Muy1")
    h=n(clear_height_mm,"clear_height")
    lex=n(effective_length_x_mm,"lex");ley=n(effective_length_y_mm,"ley")
    if As>=b*D:raise RCDesignError("steel exceeds gross section area")
    Puz=(.45*fck*(b*D-As)+.75*fy*As)/1000
    r=Pu/Puz
    alpha=1 if r<=.2 else 2 if r>=.8 else 1+(r-.2)/.6
    e_x=max(20,h/500+D/30);e_y=max(20,h/500+b/30)
    Mdx=max(Mx,Pu*e_x/1000);Mdy=max(My,Pu*e_y/1000)
    util=(Mdx/capx)**alpha+(Mdy/capy)**alpha
    short=lex/D<12 and ley/b<12
    passed=util<=1 and Pu<=Puz and short and .008<=As/(b*D)<=.06
    return {"engine":"M09_IS456_BIAXIAL_PMM_INTERACTION","source":IS456,
            "clauses":["25.4","39.6","39.7 slender excluded"],
            "uniaxial_capacity_source_id":evidence(uniaxial_capacity_source_id,"uniaxial capacities"),
            "Puz_kN":Puz,"Pu_over_Puz":r,"alpha_n":alpha,
            "minimum_eccentricity_x_mm":e_x,"minimum_eccentricity_y_mm":e_y,
            "design_Mux_kNm":Mdx,"design_Muy_kNm":Mdy,
            "interaction_utilization":util,"short_column":short,
            "status":"BOUNDED_INTERACTION_PASS_UNIAXIAL_SOURCE_HOLD" if passed else "FAIL",
            "uniaxial_capacity_solver_implemented":False,"engineering_approval":False}

def nbc_joint_shear(*,confinement_faces,framing,fck_MPa,fy_MPa,
                    joint_breadth_mm,joint_width_mm,Ast_top_mm2,Ast_bottom_mm2,
                    column_shear_kN,joint_geometry_source_id):
    """NBC105 Annex A 4.4.1: Vjc=factor*Aej*sqrt(fck), Vjh=1.25fyAst-Vcol."""
    coeff={"FOUR":1.5,"THREE":1.2,"OTHER":1.0}.get(confinement_faces)
    if coeff is None or framing not in ("INTERIOR","EXTERIOR"):
        raise RCDesignError("explicit confinement faces and interior/exterior framing required")
    fck=n(fck_MPa,"fck");fy=n(fy_MPa,"fy")
    A=n(joint_breadth_mm,"bj")*n(joint_width_mm,"wj")
    ast=n(Ast_top_mm2,"top_steel")+(n(Ast_bottom_mm2,"bottom_steel",True) if framing=="INTERIOR" else 0)
    Vcol=n(column_shear_kN,"column_shear",True)
    capacity=coeff*A*math.sqrt(fck)/1000
    demand=max(0,1.25*fy*ast/1000-Vcol)
    deficit=max(0,demand-capacity)
    return {"engine":"M10_NBC_JOINT_SHEAR","source":NBC,
            "clause":"Annex A 4.4.1.1-4.4.1.3",
            "joint_geometry_source_id":evidence(joint_geometry_source_id,"joint geometry"),
            "effective_joint_area_mm2":A,"nominal_Vjc_kN":capacity,
            "factored_Vjh_kN":demand,"additional_Ajh_mm2":deficit*1000/fy,
            "joint_nominal_shear_pass":capacity>=demand,
            "status":"BOUNDED_SHEAR_PASS_CONFINEMENT_HOLD" if capacity>=demand else "REQUIRES_ADDITIONAL_JOINT_REINFORCEMENT",
            "confinement_clause_4_3_checked":False,"engineering_approval":False}

def is456_centered_isolated_footing(*,B_mm,L_mm,D_mm,d_x_mm,d_y_mm,
                                   column_b_mm,column_l_mm,fck_MPa,fy_MPa,
                                   Ast_x_mm2_per_m,Ast_y_mm2_per_m,
                                   P_service_kN,P_ultimate_kN,allowable_soil_kPa,
                                   soil_assumption_source_id):
    """IS456 §§34.2.3-4,31.6,40.2, concentric interior rectangle on soil.

    The caller supplies total service/factored pressures inclusive of footing
    and backfill self-weight. Does not check settlement/eccentricity, ties,
    transfer, sliding, uplift, reinforcement anchorage or seismic bearing.
    """
    B=n(B_mm,"B")/1000;L=n(L_mm,"L")/1000;D=n(D_mm,"D")
    dx=n(d_x_mm,"dx");dy=n(d_y_mm,"dy")
    cb=n(column_b_mm,"column_b")/1000;cl=n(column_l_mm,"column_l")/1000
    Asx=n(Ast_x_mm2_per_m,"Asx");Asy=n(Ast_y_mm2_per_m,"Asy")
    ps=n(P_service_kN,"service");pu=n(P_ultimate_kN,"ultimate");sbc=n(allowable_soil_kPa,"SBC")
    provenance=evidence(soil_assumption_source_id,"soil/SBC")
    if not (dx<D and dy<D and cb<B and cl<L and pu>=ps):
        raise RCDesignError("invalid footing geometry or load factors")
    q_s=ps/(B*L);q_u=pu/(B*L)
    axes=[]
    for axis,a,d,Ast in (("X",(B-cb)/2,dx,Asx),("Y",(L-cl)/2,dy,Asy)):
        M=q_u*a*a/2
        try:
            flex=rectangular_singly_reinforced_flexure(
                width_mm=1000,effective_depth_mm=d,overall_depth_mm=D,
                fck_MPa=fck_MPa,fy_MPa=fy_MPa,
                tension_steel_area_mm2=Ast,factored_moment_kNm=M)
            tc=conservative_table19_shear_strength(
                fck_MPa=fck_MPa,tension_steel_percentage=100*Ast/(1000*d))["tau_c_MPa"]
        except RCBeamInputError as exc:
            raise RCDesignError(str(exc)) from exc
        # q[kN/m2]*remaining[m] is kN per 1m strip; divide by d[mm] -> MPa.
        Vu=q_u*max(0,a-d/1000)
        tau=Vu/d
        axes.append({"axis":axis,"cantilever_m":a,"M_ultimate_kNm_per_m":M,
                     "V_oneway_kN_per_m":Vu,"tau_v_MPa":tau,"tau_c_MPa":tc,
                     "flexure_pass":flex["status"]=="BOUNDED_FLEXURE_PRECHECK_PASS",
                     "oneway_shear_pass":tau<=tc,
                     "flexure_kernel_status":flex["status"]})
    d=min(dx,dy)/1000
    if cb+d>=B or cl+d>=L:
        raise RCDesignError("punch perimeter intersects free edge: case unsupported")
    area_punch=(cb+d)*(cl+d)
    b0=2*(cb+d+cl+d)*1000
    Vp=q_u*(B*L-area_punch)
    tau_punch=Vp*1000/(b0*(d*1000))
    ks=min(1,.5+min(cb,cl)/max(cb,cl))
    tau_allow=ks*.25*math.sqrt(n(fck_MPa,"fck"))
    checks={"service_bearing":q_s<=sbc,
            "x_flexure":axes[0]["flexure_pass"],"y_flexure":axes[1]["flexure_pass"],
            "x_oneway_shear":axes[0]["oneway_shear_pass"],
            "y_oneway_shear":axes[1]["oneway_shear_pass"],
            "punching_shear":tau_punch<=tau_allow}
    return {"engine":"M12_IS456_CENTERED_ISOLATED_FOOTING","source":IS456,
            "clauses":["34.2.3.2","34.2.4","31.6.1-31.6.3","40.2/Table19"],
            "soil_assumption_source_id":provenance,
            "service_pressure_kPa":q_s,"factored_pressure_kPa":q_u,
            "SBC_kPa":sbc,"axis_checks":axes,
            "punch_Vu_kN":Vp,"punch_b0_mm":b0,"punch_tau_v_MPa":tau_punch,
            "punch_tau_allow_MPa":tau_allow,"checks":checks,
            "status":"BOUNDED_NUMERIC_PASS_UNVERIFIED_SITE_HOLD" if all(checks.values()) else "FAIL",
            "scope":"CENTERED_INTERIOR_ISOLATED_SOIL_FOOTING_ONLY",
            "full_foundation_design":False,"engineering_approval":False}



def is456_combined_footing_rigid_contact(
    *, length_mm, breadth_mm, column_loads, uniform_footing_weight_kN,
    allowable_soil_pressure_kPa, load_factor, footing_depth_mm,
    effective_depth_mm, top_Ast_mm2_per_m,bottom_Ast_mm2_per_m,
    fck_MPa,fy_MPa,layout_source_id
):
    """Rigid rectangular combined footing, EXACT nonuniform linear soil reaction.

    Column loads: [{x_from_left_mm,service_load_kN},...], sorted or unordered.
    Uniform footing/backfill service weight acts at geometric centre.
    Contact q(x) is linear only while EVERYWHERE COMPRESSION. Resultant:
      e = (sum(P_i*x_i)+Wf*L/2)/(sum(P_i)+Wf) - L/2
      q(x) = P/(B*L)*(1+12e(x-L/2)/L^2).
    Exact polynomial V(x) and M(x) from vertical statics and column point loads.
    1-mm grid is used to locate max bending, plus all exact discontinuities;
    this does NOT replace shear/punching/settlement/contact FE verification.
    """
    L=n(length_mm,"length_mm")/1000;B=n(breadth_mm,"breadth_mm")/1000
    D=n(footing_depth_mm,"footing_depth_mm");d=n(effective_depth_mm,"effective_depth_mm")
    if d>=D:raise RCDesignError("effective footing depth must be below thickness")
    sf=n(load_factor,"load_factor")
    if sf<1:raise RCDesignError("load_factor must be at least 1 for this bounded case")
    Wf=n(uniform_footing_weight_kN,"uniform_footing_weight_kN",True)
    sbc=n(allowable_soil_pressure_kPa,"allowable_soil_pressure_kPa")
    src=evidence(layout_source_id,"column location and soil data")
    if not isinstance(column_loads,(list,tuple)) or len(column_loads)<2:
        raise RCDesignError("at least two column source-load records required")
    prepared=[];seen=set()
    for row in column_loads:
        if not isinstance(row,dict):raise RCDesignError("column load must be mapping")
        x=n(row.get("x_from_left_mm"),"column.x_from_left_mm")/1000
        p=n(row.get("service_load_kN"),"column.service_load_kN")
        if x>=L or x in seen:raise RCDesignError("columns must be unique inside footing")
        seen.add(x);prepared.append((x,p))
    prepared.sort()
    P=math.fsum(p for _,p in prepared)+Wf
    cg=(math.fsum(x*p for x,p in prepared)+Wf*L/2)/P
    e=cg-L/2
    q0=P/(L*B)
    q_left=q0*(1-6*e/L)
    q_right=q0*(1+6*e/L)
    if min(q_left,q_right)<=0:
        raise RCDesignError("soil separation/uplift: nonlinear contact analysis required")
    # service statics: integrate soil pressure, subtract distributed footing
    # selfweight and each concentrated column load.
    def shear(x,scale):
        upward=(B*q0)*(x+6*e*(x*x/(L*L)-x/L))
        down=Wf*x/L+math.fsum(p for xi,p in prepared if x>=xi)
        return scale*(upward-down)
    def moment(x,scale):
        upward=B*q0*(x*x/2+2*e*x**3/(L*L)-3*e*x*x/L)
        down=Wf*x*x/(2*L)+math.fsum(p*max(0,x-xi) for xi,p in prepared)
        return scale*(upward-down)
    left_force=shear(L,1.)
    end_moment=moment(L,1.)
    if (abs(left_force)>1e-8*max(1,P)
        or abs(end_moment)>1e-8*max(1,P*L)):
        raise RCDesignError("exact combined-footing force/moment equilibrium failed")
    # 1mm sample resolution; compare the convergence separately in tests.
    steps=max(1,math.ceil(L*1000))
    candidates=[0.,L,*[x for x,_ in prepared]]
    candidates += [L*i/steps for i in range(steps+1)]
    min_pair=min(((moment(x,sf),x) for x in candidates),key=lambda z:z[0])
    max_pair=max(((moment(x,sf),x) for x in candidates),key=lambda z:z[0])
    max_u=max(abs(min_pair[0]),abs(max_pair[0]))/B
    # One metre transverse strip moment demand; bar layer orientation
    # expected to be verified by engineering detail, not assumed here.
    flex=[]
    for label,Ast in (("top",top_Ast_mm2_per_m),("bottom",bottom_Ast_mm2_per_m)):
        try:
            row=rectangular_singly_reinforced_flexure(
                width_mm=1000,effective_depth_mm=d,overall_depth_mm=D,
                fck_MPa=fck_MPa,fy_MPa=fy_MPa,
                tension_steel_area_mm2=n(Ast,label+"_Ast"),
                factored_moment_kNm=max_u)
        except RCBeamInputError as err:raise RCDesignError(str(err)) from err
        flex.append({"face":label,"capacity_kNm_per_m":row.get("nominal_design_moment_capacity_kNm"),
                     "flexure_status":row["status"]})
    flex_pass=all(x["flexure_status"]=="BOUNDED_FLEXURE_PRECHECK_PASS" for x in flex)
    return {"engine":"M12_IS456_RIGID_COMBINED_FOOTING","code":"IS456:2000",
      "source":IS456,"clauses":["34.2.3","34.2.4 (shear not evaluated)"],
      "layout_source_id":src,"columns_service":prepared,
      "footing_selfweight_service_kN":Wf,"total_service_kN":P,
      "resultant_x_from_left_m":cg,"resultant_eccentricity_from_centroid_m":e,
      "service_q_left_kPa":q_left,"service_q_right_kPa":q_right,
      "service_q_max_kPa":max(q_left,q_right),"service_q_min_kPa":min(q_left,q_right),
      "service_soil_bearing_pass":max(q_left,q_right)<=sbc,
      "factored_load_multiplier":sf,"factored_q_left_kPa":sf*q_left,
      "factored_q_right_kPa":sf*q_right,
      "max_positive_moment_kNm_total":max_pair[0],
      "max_positive_moment_x_m":max_pair[1],
      "most_negative_moment_kNm_total":min_pair[0],
      "most_negative_moment_x_m":min_pair[1],
      "absolute_design_moment_kNm_per_m":max_u,
      "service_force_equilibrium_residual_kN":left_force,
      "service_moment_equilibrium_residual_kNm":end_moment,
      "moment_sampling_step_mm":1000*L/steps,
      "provisional_face_flexure":flex,
      "status":"BOUNDED_FLEXURE_CONTACT_PASS_FULL_SHEAR_HOLD"
          if flex_pass and max(q_left,q_right)<=sbc else "FAIL",
      "combined_footing_shear_punching_verified":False,
      "settlement_verified":False,"engineering_approval":False}
