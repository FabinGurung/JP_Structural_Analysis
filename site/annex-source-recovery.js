/* Annex stage: public authority links and original F3 sensitivity, never a physical approval. */
(()=>{"use strict";
const byId=id=>document.getElementById(id);if(!byId("annex-evidence-queue"))return;
const node=(tag,txt)=>{const e=document.createElement(tag);if(txt!==undefined)e.textContent=String(txt);return e};
const num=(v,d=3)=>typeof v==="number"&&Number.isFinite(v)?v.toLocaleString("en-US",{maximumFractionDigits:d,minimumFractionDigits:d}):"—";
const table=(h,rows)=>{
 const t=node("table"),head=node("thead"),tr=node("tr"),body=node("tbody");
 h.forEach(x=>tr.append(node("th",x)));head.append(tr);t.append(head);
 rows.forEach(r=>{const row=node("tr");r.forEach(v=>row.append(node("td",v)));body.append(row)});t.append(body);return t;
};
fetch("data/g15-annex-source-recovery.v0.1.json",{cache:"no-store"})
 .then(r=>r.ok?r.json():Promise.reject(Error("Published source-recovery evidence unavailable")))
 .then(d=>{
 if(d.schema!=="jp.structural.g15.annex.source_recovery_f3_demand_sensitivity.v0.1"||
 d.engineering_approval!==false||d.original_F3_verdict!=="NOT SAFE IN ONE WAY SHEAR"||
 d.gate_count!==15||d.accepted_gate_count!==0||d.owner_original_source_authenticated!==false||
 d.F3_replacement_approved!==false||d.F3_sensitivity_scenarios?.length!==12||
 d.gates?.length!==15||d.gates.some(g=>g.physical_source_acceptance!==false)||
 d.F3_sensitivity_scenarios.some(s=>s.design_pass!==false))
 throw Error("Source acceptance / structural failure safety check failed");
 byId("annex-evidence-queue").replaceChildren(table(
 ["Gate","Priority","Evidence that must be obtained","Responsible role","Physical acceptance"],
 d.gates.map(g=>[g.gate_id,g.priority,g.evidence_needed,g.required_by_role,"OPEN"])));
 const refs=byId("annex-standards");refs.replaceChildren();
 d.authoritative_references.forEach(r=>{
  const p=node("p"),link=node("a",r.title);link.href=r.url;link.rel="noopener noreferrer";
  link.target="_blank";p.append(link,node("small"," · "+r.clauses.join(" | ")));refs.append(p);
 });
 const sel=byId("annex-f3-load-model");
 const order=[
  {value:"axial_only_demand",q:"q_1p5_axial_571_kPa",text:"1.5 × 571 kN / B² (source worksheet interpretation)"},
  {value:"includes_600_demand",q:"q_1p5_reported_total_600_kPa",text:"1.5 × 600 kN / B² (different printed load basis)"}
 ];
 sel.replaceChildren(...order.map(x=>{const o=node("option",x.text);o.value=x.value;return o}));
 function render(){
  const option=order.find(x=>x.value===sel.value)||order[0];
  byId("annex-f3-sensitivity").replaceChildren(table(
   ["Illustrative square plan","Overall D","Effective d (assumed)","Pressure (kPa)","One-way demand τv (MPa)","Against rounded source 0.2 MPa","Physical result"],
   d.F3_sensitivity_scenarios.map(s=>[
    num(s.plan_B_and_L_m,2)+" × "+num(s.plan_B_and_L_m,2)+" m",
    s.overall_D_mm+" mm",num(s.cover_based_effective_d_mm,1)+" mm",
    num(s[option.q],3),num(s[option.value].one_way_uniform_pressure_stress_MPa,4),
    num(s[option.value].one_way_uniform_pressure_stress_MPa,4)<.2?"Below rounded number only":"At/above rounded number",
    "NOT APPROVED"
   ])));
 }
 sel.addEventListener("change",render);render();
 byId("annex-f3-base").textContent="Original printed effective d = "+num(d.scenario_inputs.source_d_mm,5)+
  " mm versus cover-based scenario d = "+num(d.scenario_inputs.source_D_mm-d.scenario_inputs.cover_scenario_mm-d.scenario_inputs.bar_diameter_mm/2,1)+
  " mm. The numerical difference is "+num(d.source_F3_effective_depth_conflict_mm,5)+
  " mm. No replacement footing has been selected or approved.";
 byId("annex-recovery-summary").textContent="Owner study authorization recorded; "+d.gate_count+
  " source acceptance obligations, "+d.accepted_gate_count+" accepted. Original F3 verdict: "+
  d.original_F3_verdict+". Next independent evidence inputs: "+
  d.independent_evidence_starting_tasks.join(", ")+".";
 }).catch(err=>byId("annex-evidence-queue").replaceChildren(node("p","Fail-closed: "+err.message)));
})();