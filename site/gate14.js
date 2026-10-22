/* Gate14: actual ShellMITC4 sample panel, calibrated only as a source-bounded FE trial. */
(()=>{
"use strict";
const $=id=>document.getElementById(id);if(!$("g14-kpis"))return;
const make=(tag,txt,cls)=>{const n=document.createElement(tag);if(txt!==undefined)n.textContent=String(txt);if(cls)n.className=cls;return n;};
const nf=(x,d=4)=>Number.isFinite(x)?x.toLocaleString("en-US",{maximumFractionDigits:d}):"—";
let record=null;
function render(){
 if(!record)return;
 const selected=$("g14-case").value;
 const m=["FRAME_POINT_PATCH_2F","SHELLMITC4_PATCH_2F","FULL_RIGID_MPC_REFERENCE_2F"];
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
 $("g14-matrix").replaceChildren(...entries.map(vals=>{const tr=make("tr");vals.forEach(v=>tr.append(make("td",v)));return tr;}));
 const grav=selected==="GRAVITY";
 $("g14-explain").textContent=grav?
  "Gravity: "+nf(record.patch_total_dead_kN,3)+" kN slab panel and "+nf(record.uniform_beam_wall_line_load_sum_kN,3)+" kN distributed masonry line loads in each model. Both assumed levels carry identical patch loading in every alternative; only two shell bays out of three whole floors are modelled.":
  "Seismic: the three models use the same signed imposed lateral nodal resultant; their shell/MPC stiffness alters redistribution. No independently reconciled seismic mass, diaphragm shell coverage, member detailing, or code drift decision.";
}
function admissible(d){
 if(d.schema!=="jp.structural.g15.gate14.multilevel_bay_shell_wall.v0.1"||
    d.engineering_approval!==false||d.seismic_mass_reconciled!==false||
    d.source_bay_geometry_repeated_on_real_floor_verified!==false||
    d.chosen_assumed_panel_levels?.join(",")!=="1,2"||
    d.shells_represent_complete_building!==false||
    d.real_wall_locations_verified!==false||
    d.source_F3_one_way_shear!=="NOT SAFE IN ONE WAY SHEAR"||
    d.source_grid_3d_beam_column_segments!==165||
    d.subdivided_3d_frame_segments!==177||
    d.shell_elements_across_assumed_levels!==8||
    d.cases?.length!==27||d.comparisons?.length!==9)return false;
 return d.cases.every(x=>x.frame_local_signed_action_count===177&&
    x.force_and_moment_equilibrium_pass===true&&
    x.force_equilibrium_error_kN<.001&&x.moment_equilibrium_error_kNm<.001&&
    Number.isFinite(x.governing_signed_end_moment_kNm));
}
fetch("data/g15-gate13-shell-wall.v0.1.json",{cache:"no-store"})
.then(r=>r.ok?r.json():Promise.reject(Error("No OpenSees source-coupled slab result")))
.then(d=>{
 if(!admissible(d))throw Error("Source physicality, 27-case signature or engineering HOLD violated");
 record=d;
 const cards=[["Modelled assumed bay area",nf(d.patch_total_area_m2,3)+" m²"],
 ["Actual FE shell elements",String(d.shell_elements_across_assumed_levels)],
 ["Hypothesized shell levels",d.chosen_assumed_panel_levels.join(", ")],
 ["Finite-element cases",String(d.cases.length)]];
 $("g14-kpis").replaceChildren(...cards.map(([label,value])=>{
  const cell=make("div",undefined,"lab-kpi");cell.append(make("small",label),make("strong",value));return cell;
 }));
 const c=d.comparisons.map(x=>x.case);
 $("g14-case").replaceChildren(...c.map(name=>{
  const o=make("option",name.replaceAll("_"," "));o.value=name;return o;
 }));
 $("g14-case").value="EQ_X_POS_EPOS";
 $("g14-case").disabled=false;
 $("g14-case").addEventListener("change",render);
 render();
}).catch(err=>$("g14-kpis").replaceChildren(make("p","Gate14 numerical comparison withheld: "+err.message)));
})();