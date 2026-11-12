/* R6.18 original input frame/shell and research FE numerical evidence only. */
(()=>{"use strict";
const $=id=>document.getElementById(id),NS="http://www.w3.org/2000/svg";
const el=(tag,value,cls)=>{const q=document.createElement(tag);if(value!==undefined&&value!==null)q.textContent=String(value);if(cls)q.className=cls;return q};
const S=(tag,attrs,content)=>{const q=document.createElementNS(NS,tag);for(const [k,v] of Object.entries(attrs??{}))q.setAttribute(k,String(v));if(content!==undefined)q.textContent=String(content);return q};
const fmt=(value,places=3)=>Number.isFinite(Number(value))?Number(value).toLocaleString("en-US",{minimumFractionDigits:places,maximumFractionDigits:places}):"Unknown";
const pretty=x=>String(x).replaceAll("_"," ").toLowerCase();
let data=null;
function kpis(){
 const c=data.counts,items=[
  ["Original frame objects",c.original_frame_members],["Original shell objects",c.original_shells],
  ["Shells in research FE",c.source_graph_connected_shells],
  ["Unanchored shells excluded",c.original_unanchored_shells_excluded],
  ["Declared original bases",c.original_base_restraints_declared],
  ["Connected research base nodes",c.source_connected_research_support_nodes],
  ["2×2 numerical shell elements",c.research_shell_elements_2x2],
  ["4×4 numerical shell elements",c.research_shell_elements_4x4]
 ];
 const host=$("r618-kpis");host.replaceChildren();
 for(const [label,value] of items){
  const box=el("div",null,"r618-kpi");box.append(el("small",label),el("strong",value));host.append(box);
 }
}
function card(host,label,value){
 const box=el("div",null,"r618-card");box.append(el("small",label),el("strong",value));host.append(box);
}
function cell(tr,value){tr.append(el("td",value));}
function drawChart(rows){
 const svg=$("r618-chart");svg.replaceChildren();
 svg.append(S("text",{x:22,y:26,fill:"#305666","font-size":16,"font-weight":"700"},
  "Signed vertical reactions — original connected base point ID"));
 if(!rows.length)return;
 const min=Math.min(0,...rows.flatMap(r=>[r.Rz_2x2_kN,r.Rz_4x4_kN])),
  max=Math.max(0,...rows.flatMap(r=>[r.Rz_2x2_kN,r.Rz_4x4_kN]));
 const bottom=254,top=52,left=55,right=935;
 const xx=i=>left+i*(right-left)/Math.max(rows.length-1,1);
 const yy=v=>bottom-(v-min)*(bottom-top)/Math.max(1e-12,max-min);
 const zero=yy(0);
 svg.append(S("line",{x1:left,y1:zero,x2:right,y2:zero,stroke:"#8199a5",
    "stroke-width":1,"stroke-dasharray":"5 4"}));
 for(let i=0;i<5;i++){
  const v=min+(max-min)*i/4,y=yy(v);
  svg.append(S("text",{x:4,y:y+4,"font-size":10,fill:"#526d7c"},fmt(v,1)));
 }
 for(const [name,key,color] of [["2×2 coarse","Rz_2x2_kN","#147a83"],["4×4 refined","Rz_4x4_kN","#a95e3b"]]){
  svg.append(S("polyline",{points:rows.map((r,i)=>xx(i)+","+yy(r[key])).join(" "),
   fill:"none",stroke:color,"stroke-width":2.8,"stroke-linejoin":"round"}));
  rows.forEach((r,i)=>svg.append(S("circle",{cx:xx(i),cy:yy(r[key]),r:3.4,fill:color})));
 }
 rows.forEach((r,i)=>{
  if(i%Math.max(1,Math.ceil(rows.length/11))===0||i===rows.length-1)
   svg.append(S("text",{x:xx(i),y:bottom+19,"font-size":10,fill:"#4b6774","text-anchor":"middle"},r.original_source_base_point_ids.join(",")));
 });
 svg.append(S("text",{x:66,y:292,"font-size":13,fill:"#147a83"},"━━ 2×2 original-source research"));
 svg.append(S("text",{x:400,y:292,"font-size":13,fill:"#a95e3b"},"━━ 4×4 refined research"));
}
function refinement(){
 const [role,pattern]=$("r618-case").value.split("|"),
  caseRow=data.research_mesh_sensitivity_comparisons.find(x=>x.role===role&&x.source_gravity_pattern===pattern),
  coarse=data.original_source_connected_2x2_gravity_cases_and_six_axis_equilibrium.find(x=>x.role===role&&x.source_gravity_pattern===pattern),
  fine=data.independently_solved_4x4_refinements.find(x=>x.role===role&&x.source_gravity_pattern===pattern);
 const host=$("r618-refinement"),tbody=$("r618-refinement-table");host.replaceChildren();tbody.replaceChildren();
 if(!caseRow||!coarse||!fine){host.append(el("p","No independent refinement evidence for this source case"));return;}
 card(host,"Research mesh size","412 → 1,648 ShellMITC4");
 card(host,"Largest individual Δ Rz",fmt(caseRow.largest_single_source_support_Rz_change_kN,4)+" kN");
 card(host,"Relative to total source gravity",fmt(caseRow.largest_source_support_change_relative_to_total_gravity*100,3)+"%");
 card(host,"Numerical 5% screen",caseRow.five_percent_reaction_stability_screen_passed?"Pass — research only":"Hold — mesh-sensitive");
 card(host,"2×2 vertical force residual",fmt(Math.max(...coarse.gravity_force_residual_N),4)+" N");
 card(host,"4×4 vertical force residual",fmt(Math.max(...fine.gravity_force_residual_N),4)+" N");
 card(host,"2×2 max global moment residual",fmt(Math.max(...coarse.gravity_moment_residual_Nmm),3)+" N·mm");
 card(host,"4×4 max global moment residual",fmt(Math.max(...fine.gravity_moment_residual_Nmm),3)+" N·mm");
 const rows=caseRow.support_level_differences;
 for(const r of rows){
  const tr=el("tr");
  [r.original_source_base_point_ids.join(", "),fmt(r.Rz_2x2_kN,4),
   fmt(r.Rz_4x4_kN,4),fmt(r.signed_change_kN,4),
   fmt(100*r.absolute_change_relative_to_total_source_gravity,3)+"%"].forEach(x=>cell(tr,x));
  tbody.append(tr);
 }
 drawChart(rows);
}
function interfaces(){
 const res=$("r618-resolution").value,
  group=data.shell_frame_boundary_alignment_by_mesh_size[res],
  wanted=$("r618-class").value,
  q=$("r618-search").value.trim().toUpperCase(),
  host=$("r618-contacts");
 const filtered=group.geometric_contacts.filter(x=>
  (wanted==="ALL"||wanted===x.geometry_class)&&
  (!q||(x.source_frame_key+" "+x.source_shell_key).toUpperCase().includes(q)));
 host.replaceChildren();
 for(const x of filtered){
  const tr=el("tr");
  [x.source_frame_key,x.source_shell_key,x.shell_source_story,
   x.source_frame_point_id,
   x.original_shell_corner_point_identity_matches?"Matched":"Separate IDs",
   x.research_grid_node_at_frame_endpoint?"Coincident":"Hanging / unmatched",
   pretty(x.geometry_class)].forEach(v=>cell(tr,v));
  host.append(tr);
 }
 if(!filtered.length){const tr=el("tr"),td=el("td","No matching original source boundary encounters");td.colSpan=7;tr.append(td);host.append(tr);}
 const tag=$("r618-interface-counts");tag.replaceChildren();
 for(const [name,count] of Object.entries(group.by_geometry_class))tag.append(el("span",pretty(name)+": "+count,"r618-tag"));
 $("r618-contact-count").textContent=filtered.length+" of "+group.source_frame_endpoint_to_shell_boundary_encounters+
  " geometric research contacts. A real shell/frame generated analysis constraint has not been authenticated.";
}
function initContactFilters(){
 const statuses=[...new Set(Object.values(data.shell_frame_boundary_alignment_by_mesh_size)
  .flatMap(d=>Object.keys(d.by_geometry_class)))].sort();
 const select=$("r618-class");
 for(const status of statuses){const option=el("option",pretty(status));option.value=status;select.append(option);}
}
function supportTable(){
 const role=$("r618-support-role").value,pattern=$("r618-support-pattern").value,
  book=data.unapproved_original_base_point_to_foundation_reaction_register,
  tbody=$("r618-supports");
 tbody.replaceChildren();
 for(const r of book){
  const rec=r.research_case_signed_reactions.find(x=>x.model_stiffness===role&&x.source_gravity_pattern===pattern);
  if(!rec)continue;
  const tr=el("tr"),v=rec.signed_Rxyz_kN,m=rec.signed_Mxyz_kNm;
  [r.original_source_support_point_id,fmt(v[2],4),fmt(v[0],4),fmt(v[1],4),
   fmt(m[0],4),fmt(m[1],4),fmt(m[2],4),"NOT MAPPED"].forEach(x=>cell(tr,x));
  tbody.append(tr);
 }
 const bound=data.original_source_connected_2x2_gravity_cases_and_six_axis_equilibrium.find(
  x=>x.role===role&&x.source_gravity_pattern===pattern);
 const display=$("r618-six-axis");display.replaceChildren();
 if(bound){
  card(display,"Original source gravity",fmt(bound.applied_downward_kN,3)+" kN");
  card(display,"Signed vertical research support sum",fmt(bound.signed_base_Rxyz_kN[2],3)+" kN");
  card(display,"Largest XYZ force residual",fmt(Math.max(...bound.gravity_force_residual_N),4)+" N");
  card(display,"Largest XYZ moment residual",fmt(Math.max(...bound.gravity_moment_residual_Nmm),3)+" N·mm");
  card(display,"Original base to F3/CF1 match","UNKNOWN — HOLD");
 }
}
function init(d){
 const c=d?.counts??{};
 if(d.schema!=="jp.structural.r6p18.source_bounded_fe_mesh_and_foundation_reaction_gate.v0.1"||
 c.original_frame_members!==165||c.original_shells!==115||
 c.source_graph_connected_shells!==103||c.original_unanchored_shells_excluded!==12||
 c.original_base_restraints_declared!==27||c.source_connected_research_support_nodes!==21||
 c.baseline_gravity_cases_at_2x2!==8||c.additional_independently_solved_4x4_refinement_cases!==2||
 c.research_signed_base_reaction_records_2x2!==168||c.research_signed_base_reaction_records_4x4!==42||
 d.research_mesh_sensitivity_comparisons?.length!==2||
 d.unapproved_original_base_point_to_foundation_reaction_register?.length!==21||
 d.original_F3_CF1_source_support_correspondence_verified!==false||
 d.complete_independent_physical_FE_model_accepted!==false||
 d.historical_F3_one_way_shear_unsafe!==true||d.engineering_approval!==false||
 d.source_frame_shell_ties_physically_verified!==false||
 d.r6p18_research_force_and_moment_equilibrium_checked!==true)
  throw Error("R6.18 original source, six-axis FE proof or engineering hold changed");
 data=d;kpis();initContactFilters();
 $("r618-case").addEventListener("change",refinement);
 $("r618-resolution").addEventListener("change",interfaces);
 $("r618-class").addEventListener("change",interfaces);
 $("r618-search").addEventListener("input",interfaces);
 $("r618-support-role").addEventListener("change",supportTable);
 $("r618-support-pattern").addEventListener("change",supportTable);
 refinement();interfaces();supportTable();
}
fetch("../../data/r6p18-fe-connection-mesh-foundation-audit.json",{cache:"no-store"})
 .then(r=>r.ok?r.json():Promise.reject(Error("R6.18 data not yet published")))
 .then(init).catch(err=>{
  $("r618-kpis").textContent="Original R6.18 evidence unavailable: "+err.message;
  $("r618-refinement").textContent="No completed structural or foundation approval can be inferred.";
  $("r618-contacts").replaceChildren();$("r618-supports").replaceChildren();
 });
})();