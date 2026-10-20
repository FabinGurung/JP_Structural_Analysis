
/* D2: machine-generated synthetic OpenSees outputs, no hardcoded design numbers. */
(function(){
"use strict";
const views=[...document.querySelectorAll("[data-d2-view]")];if(!views.length)return;
const el=(tag,txt,cls)=>{const n=document.createElement(tag);if(txt!==undefined)n.textContent=txt;if(cls)n.className=cls;return n;};
const fmt=(x,n=2)=>Number.isFinite(x)?x.toFixed(n):"unverified";
fetch("data/d2_signed_frame.v0.1.json",{cache:"no-store"})
.then(r=>r.ok?r.json():Promise.reject(Error("D2 evidence unavailable")))
.then(d=>{
const c=d.design_checks,s=d.signed_fe_actions;
if(d.schema!=="jp.structural.d2_m08_m09_m10_synthetic_demo.v0.1"||d.engineering_approval!==false||d.report_accepted!==false||c.engineering_approval!==false||s.engineering_approval!==false||c.beam_design?.length!==1||c.column_design?.length!==1||c.joint_design?.length!==1||!s.raw_cases?.every(r=>r.global_equilibrium_pass===true))throw Error("D2 provenance or engineering HOLD check failed");
for(const v of views){
const grid=el("div",undefined,"m09-numbers");
for(const [a,b,sub] of [
["Signed FE cases",String(s.raw_cases.length),"Six global equilibrium checks"],
["Concurrent combinations",String(s.combinations.length),"Local I/J end sign preserved"],
["M09 utilization",fmt(c.column_design[0].governing_interaction_utilization,4),"Same-end P–M–M interaction"],
["M10 joint",c.joint_design[0].status.includes("FAIL")?"FAIL / HOLD":"HOLD","Adverse shear direction bounded"]]){
const cell=el("div",undefined,"m09-stat");cell.append(el("span",a),el("strong",b),el("small",sub));grid.append(cell);}
v.replaceChildren(el("p","TRUE OPENSees ELASTIC RESPONSE · SYNTHETIC INPUTS","m09-provenance"),grid,el("p","M08 beam-I shear demand: "+fmt(c.beam_design[0].check.end_demands[0].required_shear_kN)+" kN. Not an approved design.","m09-provenance"));
}
}).catch(e=>views.forEach(v=>v.replaceChildren(el("p","D2 evidence HOLD: "+e.message,"m09-error"))));
})();
/* SP16 original Chart31: two coarse primary-source ordinate comparisons only. */
(function(){
"use strict";
const views=[...document.querySelectorAll("[data-sp16-benchmark]")];
if(!views.length)return;
const el=(tag,text,cls)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;};
const num=x=>typeof x==="number"&&Number.isFinite(x)?x.toFixed(5):"unverified";
fetch("data/sp16_chart31_spotcheck.v0.1.json",{cache:"no-store"})
.then(r=>r.ok?r.json():Promise.reject(Error("Chart31 source benchmark unavailable")))
.then(d=>{
  if(d.schema!=="jp.structural.sp16.chart31.spot_comparison.v0.1"||
     d.engineering_approval!==false||d.report_accepted!==false||
     d.full_sp16_chart31_curve_digitization_complete!==false||
     d.code_edition_reconciliation?.full_edition_parity_verified!==false||
     d.all_sampled_points_agree!==true||d.points?.length!==2||
     !d.points.every(p=>p.spot_agreement===true&&p.absolute_normalized_error<=p.visual_uncertainty_absolute_normalized_moment))
    throw Error("original-source uncertainty and HOLD checks invalid");
  for(const v of views){
    const g=el("div",undefined,"m09-numbers");
    for(const p of d.points){
      const x=el("div",undefined,"m09-stat");
      x.append(el("span","Pu/(fck·b·D) = "+p.source_chart_coordinate.pu_over_fck_bD),
        el("strong",num(p.engine_mu_over_fck_bD2)),
        el("small","Source visual ≈"+num(p.source_chart_coordinate.mu_over_fck_bD2)+" ± "+num(p.visual_uncertainty_absolute_normalized_moment)+" normalized Mu; coarse agreement"));
      g.append(x);
    }
    v.replaceChildren(
      el("p","ORIGINAL SP16:1980 PRINTED P116 · TWO COARSE CHART POINTS · NOT FULL CODE APPROVAL","m09-provenance"),
      g,
      el("p","IS456:1978 historical chart versus current IS456:2000 model; entire curve and edition parity remain on HOLD.","m09-provenance"));
  }
}).catch(e=>views.forEach(v=>v.replaceChildren(el("p","Original Chart31 evidence HOLD: "+e.message,"m09-error"))));
})();

/* Gate05 code-readiness. Only an independently generated synthetic sample is public. */
(function(){
"use strict";
const views=[...document.querySelectorAll("[data-gate05-demo]")];
if(!views.length)return;
const el=(tag,txt,cls)=>{const n=document.createElement(tag);if(txt!==undefined)n.textContent=txt;if(cls)n.className=cls;return n;};
const fmt=n=>typeof n==="number"&&Number.isFinite(n)?n.toFixed(3):"unverified";
fetch("data/nbc105_esm_synthetic.v0.1.json",{cache:"no-store"})
.then(r=>r.ok?r.json():Promise.reject(Error("ESM evidence missing")))
.then(d=>{
if(d.schema!=="jp.structural.synthetic_nbc105_2025_esm.v0.1"||d.synthetic!==true||
  d.private_real_project_values_included!==false||d.engineering_approval!==false||
  d.report_accepted!==false||d.cases?.ULS?.engineering_approval!==false||
  d.guarded_drift_checks?.ULS?.engineering_approval!==false||
  Object.values(d.safety_gates||{}).some(v=>v!==false))
    throw Error("ESM data provenance or design HOLD invalid");
for(const v of views){
 const grid=el("div",undefined,"m09-numbers");
 for(const [label,val,units] of [
  ["ULS base shear",d.cases.ULS.base_shear_kN,"kN · synthetic"],
  ["SLS base shear",d.cases.SLS.base_shear_kN,"kN · synthetic"],
  ["ULS design drift",d.guarded_drift_checks.ULS.calculated_design_drift_ratio*100,"% · Rμ-scaled, synthetic"],
  ["Floor load sums",d.cases.ULS.floor_forces_kN.reduce((a,b)=>a+b,0),"kN · equilibrium"]]){
    const box=el("div",undefined,"m09-stat");box.append(el("span",label),el("strong",fmt(val)),el("small",units));grid.append(box);
 }
 v.replaceChildren(el("p","NBC105:2025 · NUMERIC DEMO ONLY · PRIVATE PROJECT DATA EXCLUDED","m09-provenance"),grid,
   el("p","Accidental eccentricity, effective stiffness, true site hazard/soil and approvals remain HOLD.","m09-provenance"));
}
}).catch(e=>views.forEach(v=>v.replaceChildren(el("p","ESM evidence HOLD: "+e.message,"m09-error"))));
})();

/* Gate06: public-facing anonymous synthetic data; private building not exported. */
(function(){
"use strict";
const views=document.querySelectorAll("[data-gate06-demo]");if(!views.length)return;
function node(tag,content,cls){const x=document.createElement(tag);if(content!==undefined)x.textContent=content;if(cls)x.className=cls;return x;}
fetch("data/nbc105_gate06_synthetic.v0.1.json",{cache:"no-store"})
.then(r=>r.ok?r.json():Promise.reject(Error("evidence not found")))
.then(data=>{
if(data.schema!=="jp.structural.public_synthetic_gate06.v0.1"||
data.synthetic!==true||data.private_project_input_values_included!==false||
data.engineering_approval!==false||data.report_accepted!==false||
data.signed_accidental_eccentricity_cases?.length!==16||
data.source_mass_reconciliation_demonstration?.source_to_trial_mass_closed!==false)
throw Error("source verification failed");
const values=[
["ULS beam EI",data.effective_stiffness.ULS.beam_flexural_EI_over_EcIg,"fraction of gross"],
["ULS column EI",data.effective_stiffness.ULS.column_flexural_EI_over_EcIg,"fraction of gross"],
["Accidental torsion cases",data.signed_accidental_eccentricity_cases.length,"synthetic signed combinations"],
["Seismic mass gap",data.source_mass_reconciliation_demonstration.residual_source_minus_trial_kN,"kN · synthetic reference"]];
for(const view of views){
const grid=node("div",undefined,"m09-numbers");
for(const [name,value,unit] of values){const cell=node("div",undefined,"m09-stat");cell.append(node("span",name),node("strong",Number(value).toFixed(3)),node("small",unit));grid.append(cell);}
view.replaceChildren(node("p","GATE06 · SYNTHETIC SOURCE-CALCULATED REGRESSION ONLY","m09-provenance"),grid,
node("p","True diaphragm, source mass, effective torsional modelling and professional approval remain HOLD.","m09-provenance"));
}
}).catch(err=>{for(const v of views)v.replaceChildren(node("p","GATE06 HOLD: "+err.message,"m09-error"));});
})();
