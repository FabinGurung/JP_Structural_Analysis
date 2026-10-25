/* Chapter 2.6.4–2.8 source-conditional numeric audit. Source and validity flags are not interchangeable. */
(()=>{"use strict";
const $=id=>document.getElementById(id);if(!$("c02-seismic-summary"))return;
const td=x=>{const el=document.createElement("td");el.textContent=String(x);return el};
const num=(x,d=4)=>typeof x==="number"&&Number.isFinite(x)?x.toLocaleString("en-US",{minimumFractionDigits:d,maximumFractionDigits:d}):"—";
function makeTable(headers,rows){
 const t=document.createElement("table"),h=document.createElement("thead"),tr=document.createElement("tr"),body=document.createElement("tbody");
 headers.forEach(x=>{const th=document.createElement("th");th.textContent=x;tr.append(th)});h.append(tr);
 rows.forEach(vals=>{const r=document.createElement("tr");vals.forEach(x=>r.append(td(x)));body.append(r)});
 t.append(h,body);return t;
}
function failed(message){
 for(const id of ["c02-seismic-summary","c02-seismic-floors","c02-combo-table"]){
  const e=$(id);if(e){const p=document.createElement("p");p.className="c02-alert";p.textContent="SOURCE-VALIDATED NUMBERS WITHHELD: "+message;e.replaceChildren(p)}
 }
}
fetch("data/g15-chapter02-seismic-audit.v0.1.json",{cache:"no-store"})
.then(r=>{if(!r.ok)throw Error("audit data unavailable");return r.json()})
.then(d=>{
 const s=d.source_summary,b=d.balanced_distribution_by_inferred_floor_weights_kN;
 if(d.schema!=="jp.structural.g15.chapter02.seismic_wind_combinations_audit.v0.1"||
 d.engineering_approval!==false||d.source_mass_reconciled!==false||
 d.physical_evidence_accepted!==false||d.source_f3_verdict!=="NOT SAFE IN ONE WAY SHEAR"||
 d.project_signed_demand_envelope_generated!==false||
 d.source_conditional_floor_weights_and_forces?.length!==3||
 d.open_tasks?.length!==6||
 s.ETABS_source_mass_composition_verified!==false||s.accidental_eccentricity_applied_in_numeric_distribution!==false||
 Math.abs(s.formula_ULS_coefficient_unrounded-.13125)>1e-9||
 Math.abs(s.source_ULS_coefficient_printed-.131)>1e-9||
 !b.not_accepted_as_real_model_loading||
 Math.abs(b.ULS-b.ULS_floor_force_sum_kN)>1e-5||
 Math.abs(b.SLS-b.SLS_floor_force_sum_kN)>1e-5||
 d.wind_screen.wind_load_computed!==false||d.soft_storey_screen.actual_story_stiffnesses_verified!==false)
 throw Error("source provenance, numeric conservation or safety invariants failed");
 $("c02-seismic-summary").replaceChildren(makeTable(["Original input or calculation","Value","Status"],[
 ["Source empirical T",num(s.reported_period_s,4)+" s","SOURCE-REPORTED"],
 ["Computed source empirical T",num(s.empirical_formula_period_s,6)+" s","FORMULA CHECK"],
 ["Elastic C = Ch×Z×I",num(s.elastic_C_computed,6),"FROM REPORTED COEFFICIENTS"],
 ["ULS formula C/(R×Ωu)",num(s.formula_ULS_coefficient_unrounded,6),"UNROUNDED FORMULA"],
 ["ULS printed coefficient",num(s.source_ULS_coefficient_printed,6),"SOURCE ROUNDED"],
 ["ULS base shear from printed coefficient",num(s.base_shear_rounded_source_coefficient_kN,4)+" kN","SOURCE COEFFICIENT PATH"],
 ["ULS base shear from unrounded formula",num(s.base_shear_unrounded_formula_kN,4)+" kN","NOT ORIGINAL ETABS CASE"],
 ["ULS force difference due to coefficient rounding",num(s.base_shear_difference_solely_coefficient_rounding_kN,4)+" kN","DISPLAY / PRECISION DEPENDENCY"],
 ["SLS formula coefficient",num(s.formula_SLS_coefficient,6),"SOURCE-DERIVED"],
 ["SLS base shear from rounded source coefficient",num(s.base_shear_SLS_formula_kN,4)+" kN","SOURCE COEFFICIENT PATH"]
 ]));
 $("c02-seismic-floors").replaceChildren(makeTable(
 ["Inferred storey (from PDF table)","Height (m)","Inferred weight if mass is kg (kN)","ULS lateral force (kN)","SLS lateral force (kN)","Source-accepted element?"],
 d.source_conditional_floor_weights_and_forces.map(x=>[
 x.story,num(x.height_m,3),num(x.conditional_weight_kN,4),num(x.ULS_lateral_force_kN,4),num(x.SLS_lateral_force_kN,4),"NO · original mass-source absent"
 ])));
 $("c02-combo-table").replaceChildren(makeTable(["Original source expression","Use","Numerical project case"],
 d.parallel_combination_expressions.map(x=>[x,"Static parallel source family","HOLD · source member actions incomplete"])));
 $("c02-wind-result").textContent=d.wind_screen.engineering_status+" — no verified wind pressure or project demand comparison; seismic dominance claim not independently established.";
 $("c02-soft-result").textContent=d.soft_storey_screen.engineering_status+" — no verified original storey stiffness; original 'no soft storey' narrative remains unaccepted.";
}).catch(e=>failed(e.message));
})();
