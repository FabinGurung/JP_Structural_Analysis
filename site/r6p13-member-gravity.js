/* R6.13 source-derived member ledger, NOT ETABS21 member design. */
(()=>{"use strict";
const by=id=>document.getElementById(id);
const fmt=(v,n=3)=>Number.isFinite(Number(v))?Number(v).toLocaleString("en-US",{minimumFractionDigits:n,maximumFractionDigits:n}):"—";
const node=(tag,value,klass)=>{
 const e=document.createElement(tag);if(klass)e.className=klass;
 if(value!==undefined&&value!==null)e.textContent=String(value);return e;
};
let audit=null,chosen="GF:B46";
const controls=["r613-storey","r613-type","r613-role","r613-case","r613-search"];
const role=()=>by("r613-role").value,pattern=()=>by("r613-case").value;
function summary(){
 const info=audit.count,display=[
  ["Structural frame members",info.actual_structural_frame_members],
  ["Source shells",info.source_shell_objects],
  ["Included research shells",info.research_shells_included],
  ["Excluded unsupported shells",info.research_shells_excluded],
  ["Unsectioned source lines",info.unsectioned_line_source_records],
  ["Gravity patterns / role",info.source_gravity_patterns_by_stiffness],
  ["Gravity combinations / role",info.source_gravity_only_expressions_by_stiffness]];
 const host=by("r613-stats");host.replaceChildren();
 for(const [label,value] of display){const item=node("div",null,"r613-stat");
  item.append(node("small",label),node("strong",value));host.append(item);}
}
function filtered(){
 const floor=by("r613-storey").value,kind=by("r613-type").value;
 const search=by("r613-search").value.trim().toUpperCase();
 return audit.members.filter(m=>(floor==="ALL"||floor===m.story)&&
  (kind==="ALL"||kind===m.kind)&&
  (!search||(m.key+" "+m.section).toUpperCase().includes(search)));
}
function cell(tr,value){tr.append(node("td",value));}
function renderMembers(){
 const host=by("r613-members");host.replaceChildren();
 const rows=filtered();const sourceRole=role(),caseName=pattern();
 for(const m of rows){
  const tr=node("tr");
  const acts=m.trial_actions_by_source_stiffness[sourceRole].raw_gravity_case_trial[caseName];
  const max=acts.max_abs_component_of_end_actions.bending_kNm;
  for(const value of [m.key,m.section,fmt(m.geometry.length_m,3),
    fmt(m.geometry.gross_concrete_volume_m3,5),
    fmt(m.geometry.gross_member_selfweight_proxy_kN,3),
    fmt(m.source_loading.source_member_wall_resultant_kN,3),fmt(max,3)]){
   cell(tr,value);
  }
  const action=node("td"),btn=node("button","Inspect");
  btn.type="button";btn.setAttribute("aria-label","Inspect "+m.key+" research actions");
  btn.onclick=()=>{chosen=m.key;showMember();};
  action.append(btn);tr.append(action);host.append(tr);
 }
 if(!rows.length){const tr=node("tr"),td=node("td","No original members match these filters");
  td.colSpan=8;tr.append(td);host.append(tr);}
 by("r613-count").textContent=rows.length+" original structural members displayed of "+audit.members.length+
  ". All force results are bounded research, not approved strength checks.";
 if(rows.length&& !rows.some(m=>m.key===chosen))chosen=rows[0].key;
 if(rows.length)showMember();
 else by("r613-detail").replaceChildren(node("p","Change filters to inspect a source member."));
}
function propertyList(parent,pairs){
 const dl=node("dl");
 for(const [name,value] of pairs){dl.append(node("dt",name),node("dd",value));}parent.append(dl);
}
function forceView(parent,d){
 const box=node("div",null,"r613-action");
 box.append(node("strong","Signed local trial end actions — selected pattern"));
 const table=node("table"),tbody=node("tbody");
 const keys=["N_kN","Vy_kN","Vz_kN","T_kNm","My_kNm","Mz_kNm"];
 for(const k of keys){const suffix=k.split("_")[0],units=k.endsWith("kNm")?"kN·m":"kN";
  const v=d.signed_local_end_actions;
  const row=node("tr");row.append(node("td",suffix),
    node("td","I: "+fmt(v[suffix+"i_"+k.split("_")[1]],3)+" "+units),
    node("td","J: "+fmt(v[suffix+"j_"+k.split("_")[1]],3)+" "+units));
  tbody.append(row);
 }
 table.append(tbody);box.append(table);parent.append(box);
}
function showMember(){
 const m=audit.members.find(x=>x.key===chosen);if(!m)return;
 const host=by("r613-detail");host.replaceChildren();
 const name=node("h3",m.key+" · "+m.kind+" · "+m.section);host.append(name);
 const g=m.geometry,load=m.source_loading,run=m.trial_actions_by_source_stiffness[role()],
  r=run.raw_gravity_case_trial[pattern()];
 propertyList(host,[
  ["Source section",m.section+" · "+m.material],
  ["Source local points",m.source_point_ids.join(" → ")],
  ["Member length",fmt(g.length_m,5)+" m"],
  ["Gross section area",fmt(g.section_area_mm2,2)+" mm²"],
  ["Gross concrete",fmt(g.gross_concrete_volume_m3,6)+" m³"],
  ["Source selfweight estimate",fmt(g.gross_member_selfweight_proxy_kN,4)+" kN"],
  ["Direct wall assignment",fmt(load.source_member_wall_resultant_kN,4)+" kN"],
  ["Selected research role",role()+" stiffness, "+pattern()+" loading"]]);
 host.append(node("h4","Given / Working / Check"));
 host.append(node("p","Working: V=A×L; W≈V×source material unit weight. Original uniformly applied line-load resultants are integrated from the recorded beam spans; partial-span cases retain their original fractions."));
 for(const a of load.original_source_loads){
  host.append(node("p",a.pattern+" · "+a.method+" source load = "+fmt(a.raw_resultant_kN,5)+
   " kN. Calculation: "+a.working.formula));
 }
 const simple=load.simple_span_wall_only_counterfactual;
 if(simple){
  host.append(node("p","Simple-span teaching counterfactual (uniform wall load ONLY): "+simple.formula+
   " → wall q="+fmt(simple.assumed_only_wall_kN_per_m,3)+" kN/m, reaction per end="+
   fmt(simple.assumed_pin_support_each_reaction_kN,3)+" kN, midspan M="+
   fmt(simple.assumed_pin_support_midspan_M_kNm,3)+" kN·m. This is NOT the actual continuous-frame member design.","r613-alert"));
 }
 if(load.wall_segment_requires_partial_span_analysis)
  host.append(node("p","At least one original wall load uses a partial/trapezoidal span; do not substitute a full-span uniform simply supported estimate.","r613-alert"));
 forceView(host,r);
 const ext=r.max_abs_component_of_end_actions;
 host.append(node("p","Research end-component absolute maxima for this one load pattern: axial "+
   fmt(ext.axial_kN,3)+" kN; shear "+fmt(ext.shear_kN,3)+" kN; bending "+
   fmt(ext.bending_kNm,3)+" kN·m; torsion "+fmt(ext.torsion_kNm,3)+" kN·m."));
 const study=node("div",null,"r613-action");
 study.append(node("strong","Three gravity-only source expressions, recombined on the coarse research model"));
 for(const entry of run.three_original_gravity_combo_research_trials){
  study.append(node("p",entry.source_expression+": maximum absolute member-end bending component "+
    fmt(entry.metrics.bending_kNm,3)+" kN·m · NOT original ETABS21 design envelope"));
 }host.append(study);
 const link=node("a","Inspect "+m.key+" in linked original-source 2D/3D");
 link.href="../../etabs21-member-book.html?member="+encodeURIComponent(m.key);
 host.append(link);
 host.append(node("p","Check: source identity and numerical pattern amplitudes are traceable. Real strength/capacity is NOT DETERMINED, because native mesh transfer, design combination demands, rebar and support reaction identity remain unresolved.","r613-alert"));
}
function shells(){
 const host=by("r613-shells");host.replaceChildren();
 for(const shell of audit.shells){
  const row=node("tr");if(!shell.included_in_103_shell_research_trial)row.className="r613-unsupported";
  for(const value of [shell.key,shell.kind+" · "+shell.section,
    fmt(shell.projected_area_m2,4),fmt(shell.gross_plan_selfweight_proxy_kN,3),
    fmt(shell.source_applied_resultants_kN["FLOOR FINISH"],3),
    fmt(shell.source_applied_resultants_kN.Live,3),
    shell.included_in_103_shell_research_trial?"Research included":"Excluded — support unverified"])cell(row,value);
  host.append(row);
 }
}
function init(data){
 if(data?.schema!=="jp.structural.r6p13.source_gravity_research_member_ledger.v0.1" ||
  data.count?.actual_structural_frame_members!==165 ||data.count?.source_shell_objects!==115 ||
  data.count?.research_shells_included!==103||data.count?.research_shells_excluded!==12 ||
  data.F3_one_way_shear_unsafe!==true||data.engineering_approval!==false ||
  data.original_ETABS21_native_mesh_or_reactions_reproduced!==false ||
  data.research_member_strength_or_capacity_accepted!==false)throw Error("Source identity or engineering HOLD failed verification");
 audit=data;
 const requested=new URL(window.location.href).searchParams.get("member");
 if(data.members.some(x=>x.key===requested))chosen=requested;
 if(requested){const m=data.members.find(x=>x.key===chosen);if(m)by("r613-storey").value=m.story;}
 summary();for(const id of controls)by(id).addEventListener(id==="r613-search"?"input":"change",renderMembers);
 renderMembers();shells();
}
fetch("../../data/r6p13-member-gravity-research.json",{cache:"no-store"})
 .then(r=>r.ok?r.json():Promise.reject(Error("R6.13 source data not published")))
 .then(init).catch(e=>{
   by("r613-stats").textContent="No verified R6.13 research dataset available: "+e.message;
   by("r613-members").replaceChildren();
   by("r613-detail").textContent="No structural strength conclusions are available.";
 });
})();
