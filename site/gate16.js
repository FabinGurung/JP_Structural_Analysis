/* Gate16: source-verified drawing labels + bounded 2/4/8 mesh FE screen. */
(()=>{
"use strict";
const $=id=>document.getElementById(id);
if(!$("g16-kpis"))return;
const cell=(tag,txt)=>{const n=document.createElement(tag);if(txt!==undefined)n.textContent=String(txt);return n};
const fmt=(v,n=4)=>Number.isFinite(v)?v.toLocaleString("en-US",{maximumFractionDigits:n}):"—";
const modes=["MESH_2X2_FULL","MESH_4X4_FULL","MESH_8X8_FULL","MESH_4X4_CENTER_VOID"];
let record;
function render(){
 const selected=$("g16-case").value;
 const items=modes.map(mode=>record.cases.find(c=>c.case===selected&&c.mode===mode));
 if(items.some(x=>!x))return;
 const data=[
 ["ShellMITC4 elements",...items.map(c=>c.shell_mitc4_elements)],
 ["Roof horizontal movement (mm)",...items.map(c=>fmt(c.roof_horizontal_displacement_mm,6))],
 ["Elastic max story chord (%)",...items.map(c=>fmt(c.max_elastic_column_story_chord_ratio*100,6))],
 ["Same COL-F1-L0-1 signed Mzi (kN·m)",...items.map(c=>fmt(c.tracked_same_member_signed_Mzi_kNm,6))],
 ["Global force residual (kN)",...items.map(c=>fmt(c.force_equilibrium_error_kN,7))],
 ["Global moment residual (kN·m)",...items.map(c=>fmt(c.moment_equilibrium_error_kNm,7))]
 ];
 $("g16-table").replaceChildren(...data.map(row=>{
    const tr=cell("tr");for(const value of row)tr.append(cell("td",value));return tr;
 }));
 const c=record.comparisons.find(x=>x.case===selected);
 $("g16-note").textContent="Roof response difference: 2×2→4×4 "+fmt(c.roof_change_2_to_4_pct,5)+
 "%; 4×4→8×8 "+fmt(c.roof_change_4_to_8_pct,5)+"%. Matched tracked-member Mzi differences: "+
 fmt(c.Mzi_change_2_to_4_pct,5)+"% and "+fmt(c.Mzi_change_4_to_8_pct,5)+
 "%. These are numerical sensitivities, NOT automatic mesh-convergence approval.";
}
function valid(x){
 return x.schema==="jp.structural.g15.gate16.third_resolution_source_mass_review.v0.1"&&
 x.engineering_approval===false&&x.mesh_convergence_accepted===false&&
 x.source_concrete_unit_weight_conflict_unresolved===true&&
 x.mass_source_reconciled===false&&x.source_full_slab_and_terrace_boundaries_verified===false&&
 x.F3_one_way_shear==="NOT SAFE IN ONE WAY SHEAR"&&
 x.cases?.length===36&&x.comparisons?.length===9&&
 x.models?.map(m=>m.element_count_two_levels).join(",")==="8,32,128,24"&&
 x.cases.every(c=>c.force_and_moment_equilibrium_pass===true&&
  c.force_equilibrium_error_kN<.001&&c.moment_equilibrium_error_kNm<.001);
}
fetch("data/g15-gate16-source-mesh.v0.1.json",{cache:"no-store"})
.then(r=>r.ok?r.json():Promise.reject(Error("Missing Gate16 numerical artifact")))
.then(x=>{
 if(!valid(x))throw Error("Gate16 source/mass/engineering QA withheld");
 record=x;
 const rows=[
 ["3 full-bay mesh sizes","2×2, 4×4, 8×8"],
 ["OpenSees FE cases",x.cases.length],
 ["Original source terrace","Visible; boundaries unverified"],
 ["Concrete unit weight conflict","20 vs 25 kN/m³"]
 ];
 $("g16-kpis").replaceChildren(...rows.map(([k,v])=>{
  const div=cell("div");div.className="lab-kpi";div.append(cell("small",k),cell("strong",v));return div;
 }));
 $("g16-case").replaceChildren(...x.comparisons.map(c=>{
  const o=cell("option",c.case.replaceAll("_"," "));o.value=c.case;return o;
 }));
 $("g16-case").value="EQ_X_POS_EPOS";$("g16-case").disabled=false;
 $("g16-case").addEventListener("change",render);render();
}).catch(e=>$("g16-kpis").replaceChildren(cell("p","Gate16 withheld: "+e.message)));
})();