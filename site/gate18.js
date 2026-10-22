/* Gate18 source-mass reconciliation and explicit unsafe F3 visual evidence. */
(()=>{
"use strict";
const $=id=>document.getElementById(id);
if(!$("g18-kpis"))return;
const fmt=(x,k=5)=>Number.isFinite(x)?x.toLocaleString("en-US",{maximumFractionDigits:k}):"—";
const e=(tag,t)=>{const a=document.createElement(tag);if(t!==undefined)a.textContent=String(t);return a;};
fetch("data/g15-gate18-source-mass-f3.v0.1.json",{cache:"no-store"}).then(r=>r.ok?r.json():Promise.reject(Error("Missing Gate18 source evidence"))).then(d=>{
 if(d.schema!=="jp.structural.g15.gate18.story_mass_and_f3_safety.v0.1"||
   d.reported_mass_table_units_printed!==false||d.kilograms_inferred_not_native_ETABS_verified!==true||
   d.source_aggregate_mass_arithmetic_consistent_given_kg_and_standard_g!==true||
   d.ETABS_source_mass_settings_observed!==false||d.mass_source_reconciled!==false||
   d.f3_source_explicit_verdict!=="NOT SAFE IN ONE WAY SHEAR"||
   d.f3_current_design_accepted!==false||d.engineering_approval!==false||
   d.source_floor_conditional_weights?.length!==3||d.f3_hypothetical_depth_trials?.length!==4||
   Math.abs(d.reported_minus_story_table_W_kN)>d.max_rounding_bound_kN)
    throw Error("Gate18 source and safety gates failed");
 const stats=[
 ["Reported ETABS seismic weight",fmt(d.source_report_ETABS_seismic_W_kN,4)+" kN"],
 ["Story-mass-derived conditional weight",fmt(d.reconstructed_from_story_table_W_kN,6)+" kN"],
 ["Difference (rounding bound)",fmt(d.reported_minus_story_table_W_kN,6)+" kN"],
 ["F3 source verdict","NOT SAFE"]
 ];
 $("g18-kpis").replaceChildren(...stats.map(([k,v])=>{const p=e("div");p.className="lab-kpi";p.append(e("small",k),e("strong",v));return p;}));
 $("g18-floor").replaceChildren(...d.source_floor_conditional_weights.map(q=>{
    const tr=e("tr");tr.append(e("td",q.storey),e("td",fmt(q.reported_mass_number,2)),e("td",fmt(q.conditional_seismic_W_kN,6)));return tr;
 }));
 $("g18-f3").replaceChildren(...d.f3_hypothetical_depth_trials.map(q=>{
   const tr=e("tr");tr.append(e("td",fmt(q.trial_overall_thickness_mm,0)),
   e("td",fmt(q.service_bearing_kPa,3)),
   e("td",q.kernel_only_status),
   e("td","NOT APPROVED"));return tr;
 }));
 $("g18-note").textContent="If the mass table uses kg, its three storeys sum to "+
 fmt(d.reconstructed_from_story_table_W_kN,7)+" kN at "+d.conversion_gravity_m_s2+
 " m/s²; displayed rounding permits ±"+fmt(d.max_rounding_bound_kN,7)+
 " kN. Including the base entry instead gives "+fmt(d.weight_including_base_mass_kN,5)+
 " kN. Source mass units and ETABS inclusion rules remain unverified.";
}).catch(err=>$("g18-kpis").replaceChildren(e("p","Gate18 withheld: "+err.message)));
})();