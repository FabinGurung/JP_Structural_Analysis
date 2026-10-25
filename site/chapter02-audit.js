/* Chapter 2 source/audit reader. Computations are done and independently tested in Python. */
(()=>{
"use strict";
const $=id=>document.getElementById(id);
if(!$("c02-calculated-modulus"))return;
const cell=t=>{const x=document.createElement("td");x.textContent=String(t);return x};
const n=(x,prec=3)=>typeof x==="number"&&Number.isFinite(x)?x.toLocaleString("en-US",{maximumFractionDigits:prec,minimumFractionDigits:prec}):"—";
const metric=(label,val)=>{const d=document.createElement("div");d.className="c02-metric";const a=document.createElement("strong"),b=document.createElement("small");a.textContent=val;b.textContent=label;d.append(a,b);return d};
const table=(heads,rows)=>{
 const t=document.createElement("table"),head=document.createElement("thead"),body=document.createElement("tbody"),hr=document.createElement("tr");
 heads.forEach(h=>{const th=document.createElement("th");th.textContent=h;hr.append(th)});
 head.append(hr);
 rows.forEach(row=>{const tr=document.createElement("tr");row.forEach(v=>tr.append(cell(v)));body.append(tr)});
 t.append(head,body);return t;
};
const fail=(reason)=>{for(const id of ["c02-calculated-modulus","c02-cover-audit","c02-scenario-matrix"]){$(id).replaceChildren();const p=document.createElement("p");p.className="c02-alert";p.textContent="SOURCE AUDIT UNAVAILABLE — numerical results withheld. "+reason;$(id).append(p)}};
fetch("data/g15-chapter02-source-audit.v0.1.json",{cache:"no-store"})
.then(r=>{if(!r.ok)throw Error("Missing source audit JSON");return r.json()})
.then(d=>{
 if(d.schema!=="jp.structural.g15.chapter02.source_audit.v0.1"||
 d.source_record_count!==21||d.gate_open_count!==8||d.gate_accepted_count!==0||
 d.engineering_approval!==false||d.actual_model_materials_verified!==false||
 d.actual_member_load_assignments_verified!==false||
 d.original_F3_verdict!=="NOT SAFE IN ONE WAY SHEAR"||
 d.illustrative_square_member_alternatives?.length!==6||
 d.cover_formula_examples?.length!==3)
 throw Error("Source audit or approval flags failed");
 const s=d.source_findings;
 if(!Number.isFinite(s.independent_formula_E_MPa)||
 Math.abs(s.independent_formula_E_MPa-5000*Math.sqrt(20))>1e-7||
 Math.abs(s.source_printed_E_MPa-s.independent_formula_E_MPa)<2000||
 s.steel_modulus_admitted_for_design!==false||
 s.source_printed_steel_E_MPa!==200)
 throw Error("Original modulus unit/arithmetic conflicts changed");
 $("c02-calculated-modulus").replaceChildren(
  metric("Source Table 1: printed E",n(s.source_printed_E_MPa,2)+" MPa"),
  metric("From source formula: 5000√20",n(s.independent_formula_E_MPa,2)+" MPa"),
  metric("Discrepancy — NOT resolved",n(s.source_modulus_difference_MPa,2)+" MPa"),
  metric("Chapter 2 engineering admission gates",d.gate_accepted_count+" accepted / "+d.gate_open_count+" open")
 );
 $("c02-cover-audit").replaceChildren(table(["Trial bar Ø (mm)","Reported beam cover (mm)","Reported slab cover (mm)","Status"],
 d.cover_formula_examples.map(x=>[x.bar_diameter_mm,x.source_beam_cover_mm,x.source_slab_cover_mm,"SOURCE ONLY / NOT CODE ACCEPTED"])));
 $("c02-scenario-matrix").replaceChildren(table(
  ["Alternative square size (mm)","Alternative density (kN/m³)","Illustrative weight (kN)","Member assignment"],
 d.illustrative_square_member_alternatives.map(x=>[n(x.square_side_m*1000,1)+" × "+n(x.square_side_m*1000,1),
 n(x.gamma_kN_m3,0),n(x.trial_member_weight_kN,4),"NONE · source comparison only"])));
}).catch(e=>fail(e.message));
})();
