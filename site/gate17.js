/* Gate17 - source-audited mass discrepancy and engineering roadmap. */
(()=>{
"use strict";
const $=id=>document.getElementById(id);
if(!$("g17-kpis"))return;
const n=(x,d=3)=>Number.isFinite(x)?x.toLocaleString("en-US",{maximumFractionDigits:d}):"—";
const e=(tag,txt)=>{const el=document.createElement(tag);if(txt!==undefined)el.textContent=String(txt);return el;};
fetch("data/g15-gate17-source-audit.v0.1.json",{cache:"no-store"})
.then(r=>r.ok?r.json():Promise.reject(Error("Missing Gate17 source evidence")))
.then(d=>{
 if(d.schema!=="jp.structural.g15.gate17.source_mass_conflict_ledger.v0.1"||
    d.engineering_approval!==false||d.source_mass_reconciled!==false||
    d.F3_status!=="NOT SAFE IN ONE WAY SHEAR"||d.audit_fact_count!==11||
    d.gap_scenarios?.length!==2||d.decision_gates?.length!==5||
    d.original_ETABS_e2k_for_this_building_found!==false||
    d.decision_gates.some(g=>g.ready))throw Error("Engineering source gate violated");
 const cards=[
  ["Reported ETABS seismic W",n(d.report_seismic_weight_kN,4)+" kN"],
  ["Unexplained Gate08 baseline",n(d.gap_scenarios[0].unexplained_kN,3)+" kN"],
  ["Unexplained Gate10 hypothesis",n(d.gap_scenarios[1].unexplained_kN,3)+" kN"],
  ["Evidence observations",String(d.audit_fact_count)]
 ];
 $("g17-kpis").replaceChildren(...cards.map(([k,v])=>{
  const p=e("div");p.className="lab-kpi";p.append(e("small",k),e("strong",v));return p;
 }));
 $("g17-gates").replaceChildren(...d.decision_gates.map(g=>{
   const tr=e("tr");tr.append(e("td",g.gate),e("td",g.status),e("td",g.requirement));return tr;
 }));
 $("g17-modal").textContent="First modal period in table: "+n(d.table_first_modal_period_seconds,3)+
 " s; report narrative instead cites "+n(d.narrative_claim_period_seconds,3)+
 " s. Both UX and UY cumulative participation reach 90% by mode 5, while RZ reaches 90% by mode 6. Interpretation remains HOLD.";
}).catch(err=>$("g17-kpis").replaceChildren(e("p","Gate17 source audit withheld: "+err.message)));
})();