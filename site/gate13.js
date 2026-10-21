/* Gate13: actual ShellMITC4 sample panel, calibrated only as a source-bounded FE trial. */
(()=>{
"use strict";
const $=id=>document.getElementById(id);if(!$("g13-kpis"))return;
const make=(tag,txt,cls)=>{const n=document.createElement(tag);if(txt!==undefined)n.textContent=String(txt);if(cls)n.className=cls;return n;};
const nf=(x,d=4)=>Number.isFinite(x)?x.toLocaleString("en-US",{maximumFractionDigits:d}):"—";
let record=null;
function render(){
 if(!record)return;
 const selected=$("g13-case").value;
 const m=["FRAME_POINT_PATCH","SHELLMITC4_PATCH","FULL_RIGID_MPC_REFERENCE"];
 const values=m.map(name=>record.cases.find(x=>x.mode===name&&x.case===selected));
 if(values.some(v=>!v))return;
 const entries=[
  ["Roof horizontal movement (mm)",...values.map(v=>nf(v.roof_horizontal_displacement_mm,5))],
  ["Largest elastic column story chord (%)",...values.map(v=>nf(v.max_elastic_column_story_chord_ratio*100,5))],
  ["Signed governing end moment (kN·m)",...values.map(v=>nf(v.governing_signed_end_moment_kNm,4))],
  ["Controlling frame segment",...values.map(v=>v.governing_frame_segment)],
  ["Global force residual (kN)",...values.map(v=>nf(v.force_equilibrium_error_kN,7))],
  ["Global moment residual (kN·m)",...values.map(v=>nf(v.moment_equilibrium_error_kNm,7))],
  ["ShellMITC4 elements",...values.map(v=>v.shell_mitc4_elements)]
 ];
 $("g13-matrix").replaceChildren(...entries.map(vals=>{const tr=make("tr");vals.forEach(v=>tr.append(make("td",v)));return tr;}));
 const grav=selected==="GRAVITY";
 $("g13-explain").textContent=grav?
  "Gravity: "+nf(record.patch_total_dead_kN,3)+" kN slab panel and "+nf(record.uniform_beam_wall_line_load_sum_kN,3)+" kN distributed masonry line loads in each model. The shell receives interior gravity while frame/rigid references use corner tributary loads; floor assignment is assumed.":
  "Seismic: the three models use the same signed imposed lateral nodal resultant; their shell/MPC stiffness alters redistribution. No independently reconciled seismic mass, diaphragm shell coverage, member detailing, or code drift decision.";
}
function admissible(d){
 if(d.schema!=="jp.structural.g15.gate13.bounded_shell_wall_loadpaths.v0.1"||
    d.engineering_approval!==false||d.seismic_mass_reconciled!==false||
    d.shells_represent_complete_building!==false||
    d.real_wall_locations_verified!==false||
    d.source_F3_one_way_shear!=="NOT SAFE IN ONE WAY SHEAR"||
    d.source_grid_3d_beam_column_segments!==165||
    d.subdivided_3d_frame_segments!==171||
    d.shell_elements_on_one_trial_floor!==4||
    d.cases?.length!==27||d.comparisons?.length!==9)return false;
 return d.cases.every(x=>x.frame_local_signed_action_count===171&&
    x.force_and_moment_equilibrium_pass===true&&
    x.force_equilibrium_error_kN<.001&&x.moment_equilibrium_error_kNm<.001&&
    Number.isFinite(x.governing_signed_end_moment_kNm));
}
fetch("data/g15-gate13-shell-wall.v0.1.json",{cache:"no-store"})
.then(r=>r.ok?r.json():Promise.reject(Error("No OpenSees source-coupled slab result")))
.then(d=>{
 if(!admissible(d))throw Error("Source physicality, 27-case signature or engineering HOLD violated");
 record=d;
 const cards=[["Source slab bay",nf(d.patch_area_m2,3)+" m²"],
 ["Actual FE shell elements",String(d.shell_elements_on_one_trial_floor)],
 ["Assumed wall edges",String(d.assumed_wall_edges_count)],
 ["Finite-element cases",String(d.cases.length)]];
 $("g13-kpis").replaceChildren(...cards.map(([label,value])=>{
  const cell=make("div",undefined,"lab-kpi");cell.append(make("small",label),make("strong",value));return cell;
 }));
 const c=d.comparisons.map(x=>x.case);
 $("g13-case").replaceChildren(...c.map(name=>{
  const o=make("option",name.replaceAll("_"," "));o.value=name;return o;
 }));
 $("g13-case").value="EQ_X_POS_EPOS";
 $("g13-case").disabled=false;
 $("g13-case").addEventListener("change",render);
 render();
}).catch(err=>$("g13-kpis").replaceChildren(make("p","Gate13 numerical comparison withheld: "+err.message)));
})();