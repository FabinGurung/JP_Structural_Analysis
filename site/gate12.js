/* Gate12: actual OpenSees 165-member FE comparison, only source-labelled assumptions. */
(()=>{
"use strict";
const $=id=>document.getElementById(id);
if(!$("g12-kpis"))return;
const el=(tag,text,cls)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=String(text);if(cls)e.className=cls;return e;};
const num=(x,d=3)=>Number.isFinite(x)?x.toLocaleString("en-US",{maximumFractionDigits:d,minimumFractionDigits:Math.min(d,2)}):"—";
let data=null;
function pairs(){
 if(!data)return;
 const option=data.comparisons[Number($("g12-choice").value)];
 if(!option)return;
 const left=data.cases.find(x=>x.boundary==="FLEXIBLE"&&x.case===option.case);
 const right=data.cases.find(x=>x.boundary==="RIGID_MPC_TRIAL"&&x.case===option.case);
 if(!left||!right)return;
 const rows=[
  ["Maximum roof horizontal vector (mm)",num(left.max_elastic_roof_horizontal_vector_mm),num(right.max_elastic_roof_horizontal_vector_mm)],
  ["Largest elastic story chord ratio (%)",num(100*left.max_elastic_story_chord_ratio,5),num(100*right.max_elastic_story_chord_ratio,5)],
  ["Governing absolute member end moment (kN·m)",num(left.governing_absolute_member_end_moment_kNm),num(right.governing_absolute_member_end_moment_kNm)],
  ["Governing member",left.governing_member,right.governing_member],
  ["Signed governing component",left.governing_local_component+" "+num(left.governing_signed_local_component_kNm),right.governing_local_component+" "+num(right.governing_signed_local_component_kNm)],
  ["Global force balance (kN)",num(left.max_force_equilibrium_residual_kN,7),num(right.max_force_equilibrium_residual_kN,7)],
  ["Global moment balance (kN·m)",num(left.max_moment_equilibrium_residual_kNm,7),num(right.max_moment_equilibrium_residual_kNm,7)],
 ];
 $("g12-compare").replaceChildren(...rows.map(cols=>{
   const tr=el("tr");cols.forEach(v=>tr.append(el("td",v)));return tr;
 }));
 const combos=data.trial_signed_combinations.filter(c=>c.seismic_case===option.case);
 $("g12-combinations").replaceChildren(...combos.map(c=>{
   const tr=el("tr");
   [c.boundary,c.trial_combination,c.governing_member,
    c.governing_local_component+" "+num(c.governing_signed_end_moment_kNm,3)]
      .forEach(v=>tr.append(el("td",v)));
   return tr;
 }));
 const r=left.max_elastic_roof_horizontal_vector_mm>0?
  right.max_elastic_roof_horizontal_vector_mm/left.max_elastic_roof_horizontal_vector_mm:null;
 $("g12-highlight").textContent="Source-derived trial "+option.case+
  ". Rigid/flexible roof-motion ratio: "+(r===null?"undefined for zero displacement":num(r,4))+
  ". Smaller motion does not demonstrate seismic or diaphragm adequacy: assumed physical loads and geometry are still open.";
}
function validate(d){
 if(d.schema!=="jp.structural.g15.gate12.diaphragm_openSees_comparison.v0.1"||
    d.engineering_approval!==false||d.seismic_mass_reconciled!==false||
    d.actual_slab_shell_elements!==false||d.displacement_limit_compliance_verified!==false||
    d.source_F3_one_way_shear!=="NOT SAFE IN ONE WAY SHEAR"||
    d.cases?.length!==18||d.comparisons?.length!==9||
    d.trial_signed_combinations?.length!==32||
    d.trial_factors_need_NBC_SOURCE_COMBINATION_VERIFICATION!==true||
    d.trial_signed_combinations.some(c=>c.not_a_confirmed_code_combination!==true||c.signed_member_action_count!==165)||
    d.source_grid_members!==165||d.source_columns!==23)return false;
 const keys=new Set(d.cases.map(c=>c.boundary+":"+c.case));
 if(keys.size!==18)return false;
 return d.cases.every(c=>c.members===165&&c.reaction_equilibrium_verified===true&&
    c.local_signed_member_action_count===165&&
    Number.isFinite(c.max_force_equilibrium_residual_kN)&&
    Number.isFinite(c.max_moment_equilibrium_residual_kNm)&&
    c.max_force_equilibrium_residual_kN<.001&&c.max_moment_equilibrium_residual_kNm<.001&&
    Number.isFinite(c.max_elastic_story_chord_ratio)&&c.floor_drifts?.length===3&&
    c.governing_signed_local_12_actions?.length===12);
}
fetch("data/g15-gate12-diaphragm-fe.v0.1.json",{cache:"no-store"})
.then(r=>r.ok?r.json():Promise.reject(Error("3D FE result unavailable")))
.then(d=>{
 if(!validate(d))throw Error("signed FE results fail source/structural HOLD checks");
 data=d;
 const summary=[["Real frame",d.source_grid_members+" members"],
 ["Finite-element cases",d.cases.length],["Diaphragm alternatives","2 · Flexible / Rigid MPC"],["Engineering acceptance","HOLD"]];
 $("g12-kpis").replaceChildren(...summary.map(([label,value])=>{
  const box=el("div",undefined,"lab-kpi");box.append(el("small",label),el("strong",value));return box;
 }));
 $("g12-choice").replaceChildren(...d.comparisons.map((c,i)=>{
  const o=el("option",c.case.replaceAll("_"," "));o.value=String(i);return o;
 }));
 $("g12-choice").disabled=false;
 $("g12-choice").value="1";
 $("g12-choice").addEventListener("change",pairs);
 $("g12-overview").replaceChildren(...d.comparisons.map(c=>{
   const tr=el("tr");[c.case,
     num(c.flexible_roof_mm)+" / "+num(c.rigid_roof_mm),
     num(100*c.flexible_max_story_chord_ratio,5)+"% / "+num(100*c.rigid_max_story_chord_ratio,5)+"%",
     num(c.flexible_governing_end_moment_kNm)+" / "+num(c.rigid_governing_end_moment_kNm)]
     .forEach(v=>tr.append(el("td",v)));
   return tr;
 }));
 pairs();
}).catch(e=>$("g12-kpis").replaceChildren(el("p","Gate12 engineering data unavailable or invalid: "+e.message)));
const queueButton=$("g12-run");
fetch("data/g15-gate10-assumptions.v0.1.json",{cache:"no-store"})
.then(r=>r.ok?r.json():Promise.reject(Error("Gate10 source case list unavailable")))
.then(d=>{
 if(d.schema!=="jp.structural.g15.gate10.assumption_sensitivity.v0.1"||
    d.model_cases?.length!==9||d.engineering_approval!==false||
    d.seismic_mass_source_reconciled!==false)
    throw Error("Gate10 source model integrity failed");
 $("g12-run-case").replaceChildren(...d.model_cases.map(c=>{
  const o=el("option",c.label);o.value=c.id;return o;
 }));
 $("g12-run-case").value="G10_EDGE_COMM";
 $("g12-run-case").disabled=false;queueButton.disabled=false;
}).catch(err=>$("g12-queue-state").textContent="Gate12 Actions handoff HOLD: "+err.message);
queueButton.addEventListener("click",()=>{
 if(queueButton.disabled)return;
 const params={gate10_case:$("g12-run-case").value,
               stiffness:$("g12-run-stiffness").value};
 if(!/^G(?:08|10)_[A-Z0-9_]{2,35}$/.test(params.gate10_case)||
    !["ULS","SLS","GROSS"].includes(params.stiffness))return;
 const title="[JP G15 G12] 3D diaphragm "+params.gate10_case+" "+params.stiffness;
 const body="JP_G15_GATE12_RUN_V1"+String.fromCharCode(10)+JSON.stringify(params)+
  String.fromCharCode(10)+"Source-derived 165-member OpenSees trial. Flexible/rigid MPC; engineering approval HOLD. Do not accept signed trial factors as proven code combinations. F3 one-way shear source FAIL.";
 const url="https://github.com/FabinGurung/JP_Structural_Analysis/issues/new?title="+
   encodeURIComponent(title)+"&body="+encodeURIComponent(body);
 const tab=window.open(url,"_blank","noopener,noreferrer");
 if(!tab)window.location.href=url;
 $("g12-queue-state").textContent="GitHub issue opened. Submit it while signed in as an authorized repository contributor; the Actions artifact will contain 18 FE cases and 32 provisional signed combinations.";
});
})();