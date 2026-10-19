
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