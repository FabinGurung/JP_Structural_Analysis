/* Chapter 6: source-authenticated arithmetic, NOT structural acceptance. */
(()=>{"use strict";
const byId=x=>document.getElementById(x);if(!byId("c06-columns"))return;
const node=(name,text)=>{const x=document.createElement(name);if(text!==undefined)x.textContent=String(text);return x};
const n=(v,d=3)=>Number.isFinite(v)?v.toLocaleString("en-US",{maximumFractionDigits:d,minimumFractionDigits:d}):"—";
function table(headers,rows){
 const t=node("table"),hd=node("thead"),tr=node("tr"),body=node("tbody");
 headers.forEach(s=>tr.append(node("th",s)));hd.append(tr);
 rows.forEach(row=>{const r=node("tr");row.forEach(v=>r.append(node("td",v)));body.append(r)});t.append(hd,body);return t;
}
function fill(id,heads,rows){byId(id).replaceChildren(table(heads,rows))}
function guard(d){
 if(d.schema!=="jp.structural.g15.chapter06.original_element_source_arithmetic.v0.1"||
 d.engineering_approval!==false||d.original_F3_one_way_shear!=="NOT SAFE IN ONE WAY SHEAR"||
 d.code_project_compliance_demonstrated!==false||d.source_acceptance_count!==0||
 d.open_source_acceptance_count!==15||d.source_acceptance_gates?.length!==15||
 d.section6_1_columns?.source_grid_count!==23||
 d.section6_1_columns?.source_schedule_rows?.length!==12||
 d.section6_4_footing?.F3_original_schedule_accepted!==false||
 d.source_acceptance_gates.some(g=>g.accepted!==false))
 throw Error("Original source acceptance/foundation safety invariant failed");
}
fetch("data/g15-chapter06-source-design.v0.1.json",{cache:"no-store"})
 .then(r=>r.ok?r.json():Promise.reject(Error("Chapter 6 source ledger missing")))
 .then(d=>{
  guard(d);
  const cols=d.section6_1_columns;
  fill("c06-columns",["Group","Storey","Section","Reported bars","Computed As","Computed %","Printed %","Grid links"],cols.source_schedule_rows.map(x=>[
    x.mark,x.level,x.section,x.nominal_bars,n(x.computed_As_mm2,2)+" mm²",
    n(x.computed_rho_percent,3)+"%",n(x.source_reported_rho_percent,2)+"%",
    x.grid_count+" source grid names (native IDs missing)"]));
  fill("c06-column-output",["Original ETABS item","Original As (mm²)","As / section area","Status"],
    cols.reported_ETABS_examples.map(x=>[
       x.id,n(x.reported_As_mm2,1),n(x.recalculated_As_percent,3)+"%",
       "Printed sample only; source ID not matched"]));
  fill("c06-beams",["ETABS example","Section mm","Mu3 kN·m","Vu2 kN","Tu kN·m","Printed top / bottom Ast"],d.section6_2_beams.source_ETABS_examples.map(x=>[
   x.id,x.printed_section_mm.join(" × "),n(x.Mu3_kNm,4),n(x.Vu2_kN,4),
   n(x.Tu_kNm,4),x.printed_top_required_As_mm2+" / "+x.printed_bottom_required_As_mm2+" mm²"]));
  const s=d.section6_3_slab;
  fill("c06-slab",["Source observation","Readback","Design status"],
   [["Grid 1–2–F–G (Lx × Ly)",n(s.sample_Lx_m,2)+" × "+n(s.sample_Ly_m,2)+" m","SAMPLE ONLY"],
    ["General schedule thickness",s.general_schedule_D_mm+" mm","UNRECONCILED"],
    ["Source worksheet thickness",s.sample_D_mm+" mm","UNRECONCILED"],
    ["8Ø150 reinforcement provided",n(s.computed_provided_As_mm2_per_m,2)+" mm²/m","AREA ARITHMETIC ONLY"],
    ["Original example factored pressure",n(s.printed_factored_load_kPa,2)+" kPa","SOURCE PRINTED"],
    ["Computed from 1.5 × (5.13+2)",n(s.computed_trial_factored_load_kPa,3)+" kPa","ROUNDING CHECK ONLY"]]);
  const f=d.section6_4_footing;
  fill("c06-footing",["F3 dimension or force","Printed/derived value","Evidence"],
   [["Plan",f.F3_printed.size_mm.join(" × ")+" mm","Original §6.4.2"],
    ["Overall depth",f.F3_printed.D_mm+" mm","Original worksheet"],
    ["Worksheet effective d",n(f.F3_printed.d_mm,5)+" mm","Source printed; unverified"],
    ["Cover-based scenario d",n(f.F3_derived.cover_based_scenario_effective_d_mm,1)+" mm","450−50−6 assumption"],
    ["Effective depth contradiction",n(f.F3_derived.worksheet_d_exceeds_cover_scenario_mm,4)+" mm","UNRESOLVED"],
    ["Printed ultimate uplift pressure",n(f.F3_printed.printed_factored_pressure_kPa,2)+" kPa","Original printed"],
    ["Independent source arithmetic 1.5×571÷4.41",n(f.F3_derived.original_factored_pressure_recomputed_kPa,4)+" kPa","MATHEMATICAL ONLY"],
    ["Service printed including weight / area",n(f.F3_derived.service_pressure_from_printed_total_kPa,3)+" kPa","SBC is not geotechnically verified"],
    ["One-way shear verdict",f.F3_warning,"UNSAFE — DESIGN RECHECK REQUIRED"]]);
  const st=d.section6_5_staircase;
  fill("c06-stair",["Source stair quantity","Printed or computed","Status"],[
    ["Riser / tread",st.rise_mm+" / "+st.tread_mm+" mm","SOURCE PRINTED"],
    ["General / worksheet waist depth",st.general_waist_mm+" / "+st.worksheet_adopted_D_mm+" mm","UNRECONCILED"],
    ["Flight AB / BC moment",n(st.flight_AB_reported_M_kNm,2)+" / "+n(st.flight_BC_reported_M_kNm,2)+" kN·m","SOURCE PRINTED"],
    ["Printed gravity/factored",n(st.printed_total_flight_kPa,2)+" / "+n(st.reported_factored_flight_kPa,2)+" kPa","SOURCE PRINTED"],
    ["Computed 1.5×gravity",n(st.calculated_1_5_factored_flight_kPa,3)+" kPa","ARITHMETIC ONLY"],
    ["12Ø127 area",n(st.computed_provided_main_As_mm2_per_m,2)+" mm²/m","ARITHMETIC ONLY"],
    ["Original printed BC adopted area",n(st.printed_BC_adopted_As_mm2,2)+" mm²","NEEDS RECONCILIATION"]]);
  fill("c06-gates",["Gate","Domain / evidence still needed","Physical acceptance"],
    d.source_acceptance_gates.map(x=>[x.id,x.evidence_needed,"OPEN · "+x.required_by_role]));
  byId("c06-provenance").textContent="Original private PDF SHA-256 "+d.original_pdf_SHA256+
    " · 15/15 physical source obligations OPEN · 23 printed column-grid names checked · source standards linked. No project design approval.";
 }).catch(err=>byId("c06-columns").replaceChildren(node("p","Source arithmetic withheld: "+err.message)));
})();