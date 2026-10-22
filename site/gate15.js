/* Gate15: hypothetical bay-only mesh convergence/opening FE study. */
(()=>{
"use strict";
const $=id=>document.getElementById(id);
if(!$("g15-mesh-kpis"))return;
const mk=(tag,txt,cls)=>{const e=document.createElement(tag);if(txt!==undefined)e.textContent=String(txt);if(cls)e.className=cls;return e;};
const num=(v,d=4)=>Number.isFinite(v)?v.toLocaleString("en-US",{maximumFractionDigits:d}):"—";
const modes=["MESH_2X2_FULL","MESH_4X4_FULL","MESH_4X4_CENTER_VOID"];
let record;
function render(){
  if(!record)return;
  const key=$("g15-mesh-case").value;
  const c=modes.map(m=>record.cases.find(v=>v.mode===m&&v.case===key));
  if(c.some(x=>!x))return;
  const rows=[
    ["OpenSees ShellMITC4 elements",...c.map(x=>num(x.shell_mitc4_elements))],
    ["Gravity patch weight, kN",...c.map(x=>num(x.measured_panel_transverse_load_kN,3))],
    ["Roof displacement, mm",...c.map(x=>num(x.roof_horizontal_displacement_mm,6))],
    ["Peak elastic story chord, %",...c.map(x=>num(x.max_elastic_column_story_chord_ratio*100,6))],
    ["Signed governing end moment, kN·m",...c.map(x=>num(x.governing_signed_end_moment_kNm,4))],
    ["Computational frame segments",...c.map(x=>num(x.frame_local_signed_action_count))],
    ["Force residual, kN",...c.map(x=>num(x.force_equilibrium_error_kN,7))],
    ["Moment residual, kN·m",...c.map(x=>num(x.moment_equilibrium_error_kNm,7))]
  ];
  $("g15-mesh-matrix").replaceChildren(...rows.map(vals=>{
    const tr=mk("tr");vals.forEach(v=>tr.append(mk("td",v)));return tr;
  }));
  const line=record.comparisons.find(v=>v.case===key);
  $("g15-mesh-comment").textContent=
    "2×2 vs 4×4 full-bay roof response relative difference: "+num(line.mesh_2x2_to_4x4_roof_relative_difference_pct,5)+
    "%. Two densities cannot prove convergence. Central-aperture case removes 25% of the assumed patch and conditionally adjusts seismic weight; its response difference mixes aperture stiffness and changed lateral demand.";
}
function ok(x){
 return x.schema==="jp.structural.g15.gate15.mesh_opening_source_bay.v0.1"&&
  x.engineering_approval===false&&x.mass_source_reconciled===false&&
  x.mesh_convergence_verified===false&&x.full_floor_slab_geometry_verified===false&&
  x.opening_geometry_and_structural_trim_verified===false&&
  x.source_F3_one_way_shear==="NOT SAFE IN ONE WAY SHEAR"&&
  x.cases?.length===27&&x.comparisons?.length===9&&
  x.models?.map(m=>m.active_shells).join(",")==="8,32,24"&&
  x.cases.every(c=>c.force_and_moment_equilibrium_pass===true&&
    c.force_equilibrium_error_kN<.001&&c.moment_equilibrium_error_kNm<.001&&
    Number.isFinite(c.governing_signed_end_moment_kNm));
}
fetch("data/g15-gate15-mesh-opening.v0.1.json",{cache:"no-store"})
.then(r=>r.ok?r.json():Promise.reject(Error("Missing computed Gate15 result")))
.then(d=>{
 if(!ok(d))throw Error("Numerical provenance or engineering safety HOLD failed");
 record=d;
 const items=[
 ["Full bay area",num(d.source_reported_panel_area_m2,3)+" m²"],
 ["Hypothetical central opening",num(d.assumed_opening_area_m2_per_level,4)+" m²/floor"],
 ["Conditional missing gravity",num(d.estimated_conditional_mass_deduction_both_floors_kN,3)+" kN"],
 ["FE cases",d.cases.length]
 ];
 $("g15-mesh-kpis").replaceChildren(...items.map(([k,v])=>{
   const b=mk("div",undefined,"lab-kpi");b.append(mk("small",k),mk("strong",v));return b;
 }));
 $("g15-mesh-case").replaceChildren(...d.comparisons.map(c=>{
   const o=mk("option",c.case.replaceAll("_"," "));o.value=c.case;return o;
 }));
 $("g15-mesh-case").value="EQ_X_POS_EPOS";
 $("g15-mesh-case").disabled=false;
 $("g15-mesh-case").addEventListener("change",render);
 render();
}).catch(err=>$("g15-mesh-kpis").replaceChildren(mk("p","Gate15 results withheld: "+err.message)));
})();