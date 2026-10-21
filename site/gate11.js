/* Gate11 engineering assumptions — no NBC approval, no physical diaphragm. */
(()=>{
"use strict";
const $=id=>document.getElementById(id);if(!$("g11-head"))return;
const el=(n,v,c)=>{const x=document.createElement(n);if(v!==undefined)x.textContent=String(v);if(c)x.className=c;return x;};
const fmt=(x,d=3)=>Number.isFinite(x)?x.toLocaleString("en-US",{maximumFractionDigits:d}):"—";
let doc=null;
function select(){
 const idx=Number($("g11-case").value);
 const c=doc?.cases[idx];if(!c)return;
 $("g11-table").replaceChildren(...c.floors.map(f=>{
  const tr=el("tr");
  [f.floor,fmt(f.signed_applied_floor_force_kN),fmt(f.accidental_eccentricity_m),
   fmt(f.signed_torsional_demand_about_stiffness_center_kNm),
   fmt(f.max_assumed_lateral_displacement_mm)].forEach(v=>tr.append(el("td",v)));
  return tr;
 }));
 $("g11-note").textContent="All 23-column force and torsion sums balance the applied case. " +
  "Floors follow scaled area polygons; source diaphragm stiffness, wall placements, interstorey drifts and P-delta are NOT verified. " +
  "F3 remains NOT SAFE IN ONE WAY SHEAR.";
}
fetch("data/g15-gate11-diaphragm-proxy.v0.1.json",{cache:"no-store"})
.then(r=>r.ok?r.json():Promise.reject(Error("Diaphragm screen data missing")))
.then(d=>{
 if(d.schema!=="jp.structural.g15.gate11.rigid_diaphragm_proxy.v0.1"||
    d.cases?.length!==8||d.engineering_approval!==false||
    d.mass_source_reconciled!==false||
    d.actual_story_drift_accepted!==false||
    d.foundation_F3_source!=="NOT SAFE IN ONE WAY SHEAR"||
    d.cases.some(x=>x.floors?.length!==3||x.floors.some(f=>f.force_and_moment_equilibrium_verified!==true)))
   throw Error("Evidence integrity or engineering HOLD inconsistent");
 doc=d;
 const card=[["Source mass scenario",d.source_mass_case_id],
    ["Accidental eccentricity","±"+fmt(d.accidental_eccentricity_fraction*100,0)+"%"],
    ["Signed cases",String(d.cases.length)],["Structural approval","HOLD"]];
 $("g11-head").replaceChildren(...card.map(([k,v])=>{
  const box=el("div",undefined,"lab-kpi");box.append(el("small",k),el("strong",v));return box;
 }));
 $("g11-case").replaceChildren(...d.cases.map((a,i)=>{
  const o=el("option",(a.lateral_sign>0?"+":"−")+a.axis+" and "+(a.accidental_offset_sign>0?"+":"−")+"ecc");
  o.value=String(i);return o;
 }));
 $("g11-case").addEventListener("change",select);select();
}).catch(e=>$("g11-note").textContent="Gate11 torsion evidence HOLD: "+e.message);
})();