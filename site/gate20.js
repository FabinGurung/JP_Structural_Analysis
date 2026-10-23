/* Gate20 provider-backed source crosswalk visualization, no raw source or identity reveal. */
(()=>{
"use strict";
const $=id=>document.getElementById(id);
if(!$("g20-summary"))return;
const e=(tag,v)=>{const x=document.createElement(tag);if(v!==undefined)x.textContent=String(v);return x;};
const fmt=(v,n=3)=>Number.isFinite(v)?v.toLocaleString("en-US",{maximumFractionDigits:n}):"—";
fetch("data/g15-gate20-crosswalk.v0.1.json",{cache:"no-store"})
.then(r=>r.ok?r.json():Promise.reject(Error("Missing Gate20 source contract")))
.then(d=>{
 if(d.schema!=="jp.structural.g15.gate20.crosswalk_F3_reconciliation.v0.1"||
 d.gate_count!==15||d.accepted_gate_count!==0||d.gates?.length!==15||
 d.upstream_native_ETABS_model_found!==false||
 d.native_ETABS_mass_unit_and_source_definition_verified!==false||
 d.f3?.source_verdict!=="NOT SAFE IN ONE WAY SHEAR"||
 d.f3?.F3_redesign_verified!==false||d.engineering_approval!==false||
 d.gates.some(g=>g.accepted||g.source_provider_readback))throw Error("Source safety checks reject output");
 const stat=[["Engineering proof obligations",d.gate_count],
 ["Accepted obligations",d.accepted_gate_count],
 ["Source ETABS W",fmt(d.reported_ETABS_W_kN,4)+" kN"],
 ["F3 original safety","FAIL · ONE-WAY SHEAR"]];
 $("g20-summary").replaceChildren(...stat.map(([k,v])=>{
  const box=e("div");box.className="lab-kpi";box.append(e("small",k),e("strong",v));return box;
 }));
 const body=$("g20-items");
 body.replaceChildren(...d.gates.map(g=>{
  const tr=e("tr");
  tr.append(e("td",g.id),e("td",g.domain),e("td",g.status),
            e("td",g.evidence_needed),e("td",g.acceptance_test));
  return tr;
 }));
 $("g20-f3").textContent="Source footing area "+fmt(d.f3.foundation_plan_area_m2,2)+" m². "+
 "Printed factored upward pressure "+fmt(d.f3.source_ultimate_pressure_printed_kPa,2)+" kPa "+
 "matches 1.5×571/4.41 = "+fmt(d.f3.reconstructed_printed_q_from_1p5_times_571_kPa,4)+" kPa. "+
 "Using the source's separate 600 kN including selfweight instead would give "+
 fmt(d.f3.alternative_1p5_times_600_kPa,4)+" kPa (+"+
 fmt(d.f3.factored_pressure_difference_kPa,4)+" kPa). "+
 "Reported effective depth "+fmt(d.f3.source_sheet_effective_depth_mm,5)+" mm vs "+
 fmt(d.f3.previous_trial_effective_depth_mm,0)+" mm historical assumption (Δ"+
 fmt(d.f3.discrepancy_mm,5)+" mm). Values are conflicting source/calculation bases; neither is a verified redesign.";
}).catch(err=>$("g20-summary").replaceChildren(e("p","Gate20 withheld: "+err.message)));
})();
