/* R6.10 authenticated source-input shell/diaphragm workbench.
 * This visualization cannot assert solved ETABS21 modal/design results.
 */
(()=>{"use strict";
const by=id=>document.getElementById(id);
if(new URLSearchParams(location.search).get("view")==="report") document.body.classList.add("r610-report-view");
const svgNS="http://www.w3.org/2000/svg";
const fmt=(x,n=3)=>Number.isFinite(Number(x))?Number(x).toLocaleString("en-US",{minimumFractionDigits:n,maximumFractionDigits:n}):"—";
const elt=(tag,attrs={},body)=>{const n=document.createElementNS(svgNS,tag);
  for(const [k,v] of Object.entries(attrs))n.setAttribute(k,String(v));
  if(body!==undefined)n.textContent=String(body);return n;};
const div=(klass)=>{const x=document.createElement("div");if(klass)x.className=klass;return x;};
function insertLine(parent,tag,text){const el=document.createElement(tag);el.textContent=String(text);parent.append(el);return el;}
let d=null,floor="GF",filter="ALL",selected="GF:F4",yaw=-.78,role="ULS",lineKey="",comboKey="",contactGroup="GF_F56";
const p2=xyz=>[34+xyz[0]/21000*615,400-xyz[1]/12550*355];
const p3=xyz=>{const x=(xyz[0]-10500)/1000,y=(xyz[1]-6275)/1000,z=xyz[2]/1000;
return [346+(x*Math.cos(yaw)-y*Math.sin(yaw))*16,292+(x*Math.sin(yaw)+y*Math.cos(yaw))*7.5-z*19];};
function lerp(vertices,u,v){const w=[(1-u)*(1-v),u*(1-v),u*v,(1-u)*v];
return [0,1,2].map(j=>w.reduce((a,x,i)=>a+x*vertices[i][j],0));}
function visible(x){return (floor==="ALL"||x.story===floor)&&
(filter==="ALL"||filter==="SUPPORTED"&&x.source_supported_by_frame_shell_topology||
 filter==="FLOATING"&&!x.source_supported_by_frame_shell_topology||
 filter==="PANEL"&&x.kind==="PANEL");}
function sourceCells(){return d?.all_shell_parameters?.filter(visible)??[];}
function choose(key){selected=key;const panel=d.all_shell_parameters.find(x=>x.key===key);
 if(!panel)return;floor=panel.story;by("r610-floor").value=floor;
 by("r610-filter").value="ALL";filter="ALL";buildSelect();by("r610-shell").value=key;redraw();}
function clickSource(el,key){el.dataset.shell=key;el.setAttribute("tabindex","0");el.setAttribute("role","button");
el.setAttribute("aria-label","Inspect original ETABS21 shell "+key);
el.addEventListener("click",()=>choose(key));el.addEventListener("keydown",ev=>{
 if(ev.key==="Enter"||ev.key===" "){ev.preventDefault();choose(key);}});}
function sourceLayer(svg,projection){
 svg.replaceChildren(elt("rect",{x:1,y:1,width:678,height:428,rx:10,fill:"#f9fcfd"}));
 const objects=sourceCells();
 objects.sort((a,b)=>(a.key===selected?1:-1)-(b.key===selected?1:-1));
 for(const a of objects){
  const polygon=a.corners_xyz_mm.map(p=>projection(p).join(",")).join(" ");
  const focus=a.key===selected,good=a.source_supported_by_frame_shell_topology;
  const shape=elt("polygon",{points:polygon,stroke:focus?"#193f6f":good?"#53a29b":"#dd785c",
   "stroke-width":focus?3:1,"stroke-opacity":focus?1:.7,
   fill:focus?"#d4bc70":good?"#80c7be":"#ee9276",
   "fill-opacity":focus?.87:good?.35:.60});
  clickSource(shape,a.key);svg.append(shape);
 }
 const active=d.all_shell_parameters.find(a=>a.key===selected);
 if(active&&objects.some(x=>x.key===selected)){
  // Native E2K 8x8 mesh is a source REQUEST, not a verified native mesh.
  // This visualizes requested bilinear divisions only on the selected quad.
  const n1=Math.min(8,active.n1),n2=Math.min(8,active.n2);
  for(let i=1;i<n1;i++){
    const t=i/n1,a=projection(lerp(active.corners_xyz_mm,t,0)),
      b=projection(lerp(active.corners_xyz_mm,t,1));
    svg.append(elt("line",{x1:a[0],y1:a[1],x2:b[0],y2:b[1],stroke:"#154f65","stroke-width":1,opacity:.75}));
  }
  for(let i=1;i<n2;i++){
    const t=i/n2,a=projection(lerp(active.corners_xyz_mm,0,t)),
      b=projection(lerp(active.corners_xyz_mm,1,t));
    svg.append(elt("line",{x1:a[0],y1:a[1],x2:b[0],y2:b[1],stroke:"#154f65","stroke-width":1,opacity:.75}));
  }
  const c=projection(lerp(active.corners_xyz_mm,.5,.5));
  svg.append(elt("circle",{cx:c[0],cy:c[1],r:3.8,fill:"#193f6f",stroke:"#fff","stroke-width":1.1}));
 }
 svg.append(elt("text",{x:13,y:21,"font-size":12,fill:"#54717f"},
   "ETABS21 original shell surfaces · "+objects.length+" visible · 8×8 lines are mesh previews"));
}

function contactMarkers(svg,project){
 const audit=d?.r6p11_contact_audit;
 const group=audit?.groups?.find(g=>g.id===contactGroup);
 if(!group || (floor!=="ALL" && floor!==group.story)) return;
 const [start,end]=group.edge_xyz_mm.map(project);
 const edge=elt("line",{x1:start[0],y1:start[1],x2:end[0],y2:end[1],stroke:"#7841b0","stroke-width":3,"stroke-dasharray":"8 5"});
 svg.append(edge);
 for(const c of group.candidates){
  const p=project(c.xyz_mm);
  const marker=elt("circle",{cx:p[0],cy:p[1],r:6,fill:"#ffd369",stroke:"#71429a","stroke-width":2});
  marker.append(elt("title",{},c.source_shell+" corner "+c.corner_source_id+
   " · geometric candidate only · reaction/constraint NOT verified"));
  svg.append(marker);
 }
}
function contactDetail(){
 const host=by("r611-contact-detail");if(!host)return;
 host.replaceChildren();
 const audit=d?.r6p11_contact_audit;
 if(!audit||audit.candidate_source_corners!==10||audit.original_unsupported_shells!==12||
    audit.support_gate_passed!==false||audit.engineering_approval!==false){
  insertLine(host,"p","R6.11 input unavailable; no original shell can be admitted.");return;
 }
 const group=audit.groups.find(x=>x.id===contactGroup);if(!group)return;
 insertLine(host,"h3",group.label+" · "+group.target_key);
 insertLine(host,"p",group.geometric_matches+" of "+group.candidates.length+
  " source corners coincide with the candidate receiving edge at a tolerance of 0.001 mm.");
 for(const c of group.candidates){
  insertLine(host,"p",c.source_shell+" · point "+c.corner_source_id+
   " · gap "+fmt(c.three_dimensional_gap_mm,6)+" mm · "+fmt(c.edge_fraction_from_first_endpoint*100,2)+
   "% along edge · native analysis joint, constraint and vertical reaction: NOT VERIFIED");
 }
 insertLine(host,"strong","ENGINEERING HOLD — 12 unsupported shells remain excluded. F3 remains unsafe in one-way shear.");
}
function drawCandidateViews(){
 for(const [id,project] of [["r611-plan",p2],["r611-3d",p3]]){
  const svg=by(id);
  if(!svg)continue;
  sourceLayer(svg,project);
  contactMarkers(svg,project);
 }
 contactDetail();
}
function redraw(){
 sourceLayer(by("r610-plan"),p2);
 sourceLayer(by("r610-3d"),p3);
 contactMarkers(by("r610-plan"),p2);
 contactMarkers(by("r610-3d"),p3);
 detail();drawCandidateViews();
}
function buildSelect(){
 const items=sourceCells().sort((a,b)=>a.key.localeCompare(b.key,undefined,{numeric:true}));
 const sel=by("r610-shell");sel.replaceChildren();
 for(const a of items){const opt=document.createElement("option");opt.value=a.key;
  opt.textContent=a.key+(a.source_supported_by_frame_shell_topology?"":" · unsupported");
  sel.append(opt);}
 if(!items.some(a=>a.key===selected))selected=items[0]?.key||"";
 sel.value=selected;
}
function detail(){
 const m=d.all_shell_parameters.find(x=>x.key===selected);
 const parent=by("r610-shell-detail");parent.replaceChildren();
 if(!m){insertLine(parent,"p","No shell matches the current filter.");return;}
 insertLine(parent,"h3",m.key+" · "+m.kind+" · "+m.source_section_canonical);
 insertLine(parent,"p","Source request: "+m.source_mesh_mode+" · "+m.n1+" × "+m.n2+" divisions. "+
  (m.source_mesh_mode==="MESHN1XN2"?"The model specifies this division count.":"The displayed divisions approximate the automatic mesh."));
 insertLine(parent,"p","Panel corner coordinates (mm) · "+m.corners_xyz_mm.map(p=>"("+p.map(x=>fmt(x,1)).join(", ")+")").join("  ·  "));
 insertLine(parent,"p","Projected plan area "+fmt(m.projected_area_m2,4)+" m²; actual triangle surface area "+
  fmt(m.true_triangular_surface_area_m2,4)+" m²; original thickness "+fmt(m.source_thickness_mm,1)+" mm.");
 insertLine(parent,"code","Source dead selfweight ≈ true surface area × thickness × original material unit weight = "+
   fmt(m.true_area_concrete_selfweight_kN,4)+" kN (gross geometric proxy).");
 insertLine(parent,"p",m.source_supported_by_frame_shell_topology?
   "Source connectivity: traceable through original frame/shell object vertices to at least one fixed foundation node. Actual auto-mesh coupling remains to be validated.":
   "ENGINEERING HOLD: this shell has no source-traced vertical support path through the original frames/shell corner graph. It remains in the original input set, not silently deleted.");
 if(m.source_applied_loads.length){
  insertLine(parent,"p","Direct original surface loads: "+m.source_applied_loads.map(x=>
    x.pattern+" = "+fmt(x.raw_integrated_kN,4)+" kN").join(" + "));
 }else insertLine(parent,"p","No directly assigned floor finish/live pressure to this source object.");
}
function metric(title,value,note){const el=div("r610-fact");insertLine(el,"small",title);
 insertLine(el,"strong",value);insertLine(el,"p",note);return el;}
function facts(){
 const root=by("r610-facts");root.replaceChildren(
  metric("Original shell objects",d.source_shell_count,"106 explicit 8×8 mesh instructions"),
  metric("Shells with source support",d.shells_connected_through_source_to_fixed_base,"Frame + shell corner graph"),
  metric("Unsupported shell objects",d.shells_without_verified_vertical_support_path,"Three unanchored original groups"),
  metric("Rigid diaphragm points",d.source_diaphragm_points_total,"D1 · D2 · D3, horizontal movement"),
  metric("LINE wall loads located",d.mapped_source_line_wall_load_count,"Original unsectioned source geometry"),
  metric("Source design combinations","11 + 11","Exact ULS and SLS combo records")
 );
}
function lines(){
 const root=by("r610-line"),list=d.source_line_wall_load_to_shell_transfer_proxy;
 root.replaceChildren();
 for(const x of list){const el=document.createElement("option");el.value=x.source_line;el.textContent=x.source_line;root.append(el);}
 if(!list.some(x=>x.source_line===lineKey))lineKey=list[0]?.source_line||"";
 root.value=lineKey;lineDetail();
}
function lineDetail(){
 const data=d.source_line_wall_load_to_shell_transfer_proxy.find(x=>x.source_line===lineKey);
 const el=by("r610-line-detail");el.replaceChildren();
 if(!data){insertLine(el,"p","Select original wall line.");return;}
 insertLine(el,"h3",data.source_line+" · "+fmt(data.source_wall_kN,5)+" kN");
 insertLine(el,"p","Original WALL LOAD intensity integrated over native line geometry; "+
 data.quadrature_intervals+" source geometric samples, "+data.unique_matching_shells+
 " adjacent original shell targets, zero unmatched samples.");
 for(const [k,v] of Object.entries(data.candidate_shell_force_share_kN)){
   insertLine(el,"p",k+" → "+fmt(v,5)+" kN source-conserving proxy share");
 }
 insertLine(el,"p","Sum of target shares equals source wall resultant. This partitions geometric input, not ETABS' verified shell/beam mesh end-force transfer.");
}
function pattern(){
 const out=by("r610-gravity");out.replaceChildren();
 const mass=d.all_source_gravity_loading;
 for(const [name,value] of Object.entries(mass.pattern_source_integrated_kN)){
  const p=div("r610-pattern");insertLine(p,"small",name);
  insertLine(p,"b",fmt(value,3)+" kN");
  insertLine(p,"p",name==="Dead"?
    "Gross original frame and 3D shell geometric selfweight proxy.":
    name==="Live"?"Original full live surface load, not the 30% mass participation value.":
    "Original E2K object-load integration; all 115 shells retained in source totals.");
  out.append(p);
 }
 out.append(metric("Conditional mass-source weight",
  fmt(mass.conditional_msSrc1_gravity_weight_kN,3)+" kN",
  "NOT independently verified ETABS21 mass; 12 unsupported source shells remain."));
}
function combos(){
 const source=d.original_loadcase_and_combination_register[role];
 const all=source.source_11_load_combinations;
 const select=by("r610-combo");select.replaceChildren();
 for(const v of all){const opt=document.createElement("option");opt.value=v.name;opt.textContent=v.name;select.append(opt);}
 if(!all.some(x=>x.name===comboKey))comboKey=all[0].name;
 select.value=comboKey;combo();
}
function combo(){
 const a=d.original_loadcase_and_combination_register[role].source_11_load_combinations.find(x=>x.name===comboKey);
 const parent=by("r610-combo-detail");parent.replaceChildren();if(!a)return;
 insertLine(parent,"h3",role+" · "+a.name);
 const t=document.createElement("table"),head=document.createElement("thead"),row=document.createElement("tr");
 for(const title of ["Source case","Source factor","Numerical standing"]){const th=document.createElement("th");th.textContent=title;row.append(th);}
 head.append(row);t.append(head);
 const body=document.createElement("tbody");
 for(const x of a.terms){const tr=document.createElement("tr");
  for(const s of [x.case,fmt(x.scale,2),x.case.startsWith("EQ")?"Lateral source mass/response NOT VERIFIED": "Original gravity case inputs, not a complete frame solution"]){
    const td=document.createElement("td");td.textContent=s;tr.append(td);}
  body.append(tr);
 }
 t.append(body);parent.append(t);
 insertLine(parent,"p","Known gravity load-input arithmetic: "+fmt(a.gravity_known_exact_source_total_kN,4)+" kN. "+
 (a.contains_lateral_seismic?
 "This combination includes an original seismic case whose authentic modal/mass and diaphragm response is not yet reproduced.":
 "This is not a source-supported force/moment envelope until a connected numerical model executes every participating load pattern."));
}
function viewSolver(d,s){
 const el=by("r610-solver-status");el.replaceChildren();
 if(!d || d.status!=="INDEPENDENT_RESEARCH_CONNECTED_SHELL_FRAME_GRAVITY_NOT_FULL_SOURCE"||
   d.original_unsupported_shells_numerically_excluded!==12||
   d.original_frame_elements_included!==165||d.F3_one_way_shear_unsafe!==true||
   d.professional_engineer_approved!==false){
  insertLine(el,"strong","Not a verified complete building solution");
  insertLine(el,"p","Full source ETABS21 analysis remains blocked by unresolved shell support/connectivity, exact mesh compatibility and unapproved source mass. The original shell and gravity records above remain available for QA.");
  return;
 }
 insertLine(el,"h3","Independent connected-shell research trial · "+d.role+" "+d.source_case);
 insertLine(el,"p","OpenSees solved "+d.original_frame_elements_included+" original structural frame segments, "+
 d.vertically_supported_shells_numerically_included+" source-connected shell objects represented by "+
 d.coarse_numerical_shell_elements+" coarse trial quadrilaterals, and 3 source diaphragm groups.");
 insertLine(el,"p","Input source gravity = "+fmt(d.applied_gravity.total_applied_downward_N/1000,4)+
 " kN; summed vertical base reaction = "+fmt(d.sum_native_fixed_base_reactions_N[2]/1000,4)+
 " kN; residual = "+fmt(d.vertical_equilibrium_residual_N,5)+" N.");
 insertLine(el,"p","Research-only, nonconforming reduced mesh; source 8×8 meshing, all 115 shell objects and complete seismic/member design cases are not reproduced. F3 unsafe.");
}
let researchBook=null,trialRole="ULS",trialCase="P|Dead",trialMember="GF:B46";
function casebookOptions(){
 const data=researchBook?.role_results?.[trialRole];
 if(!data)return;
 const select=by("r610-trial-case");select.replaceChildren();
 for(const name of ["Dead","Live","WALL LOAD","FLOOR FINISH","EQX_CONDITIONAL","EQY_CONDITIONAL"]){
  const opt=document.createElement("option");opt.value="P|"+name;opt.textContent=
    name.startsWith("EQ")?name.replace("_CONDITIONAL","")+" · conditional centred ESM":name+" · source gravity";
  select.append(opt);
 }
 for(const combo of data.recombined_original_11_linear_add_expressions){
  const opt=document.createElement("option");opt.value="C|"+combo.original_source_name;
  opt.textContent="Combination · "+combo.original_source_name+
    (combo.source_seismic_combination?" · ESM PROXY":" · supported-shell trial");
  select.append(opt);
 }
 if(!Array.from(select.options).some(o=>o.value===trialCase))trialCase="P|Dead";
 select.value=trialCase;
 const member=by("r610-trial-member");member.replaceChildren();
 const ids=Object.keys(data.independently_run_research_patterns.Dead.signed_member_end_actions_bounded)
  .sort((a,b)=>a.localeCompare(b,undefined,{numeric:true}));
 for(const name of ids){const opt=document.createElement("option");opt.value=name;opt.textContent=name;member.append(opt);}
 if(!ids.includes(trialMember))trialMember=ids[0]||"";
 member.value=trialMember;
 showCasebook();
}
function signedRow(parent,label,value,unit){
 const r=div("r610-action-row");insertLine(r,"span",label);
 insertLine(r,"strong",fmt(value,4)+" "+unit);parent.append(r);
}
function showCasebook(){
 const record=researchBook?.role_results?.[trialRole];
 if(!record)return;
 const [type,key]=trialCase.split(/\|(.+)/);
 const o=type==="P"?record.independently_run_research_patterns[key]:
   record.recombined_original_11_linear_add_expressions.find(c=>c.original_source_name===key);
 const status=by("r610-case-status");status.replaceChildren();
 if(!o){insertLine(status,"p","Selected source trial not available.");return;}
 const actions=type==="P"?o.signed_member_end_actions_bounded:o.signed_member_end_actions_non_design;
 const vals=actions?.[trialMember];
 if(!vals||vals.length!==12){insertLine(status,"p","Selected frame has no source-reproducible signed actions.");return;}
 insertLine(status,"h4",(type==="P"?"Independent source pattern: ":"Source expression: ")+key+
  " · "+trialRole);
 if(type==="P"){
  const E=key.startsWith("EQ")?o.applied_conditional_lateral:null;
  insertLine(status,"p",E?
     "Centred source seismic-coefficient sensitivity only; W is a connected-only mass proxy. Lateral equilibrium residual "+
        fmt(o.horizontal_equilibrium_residual_N,5)+" N. The native ±5% accidental eccentricity subcases and modal source mass have NOT been reproduced.":
     "Source original gravity pattern with 103 connected shells and 165 frames on a coarse 2×2 independent OpenSees mesh. Input "+
       fmt(o.applied_gravity.total_applied_downward_N/1000,4)+" kN; reaction "+
       fmt(o.sum_native_fixed_base_reactions_N[2]/1000,4)+" kN; vertical equilibrium residual "+
       fmt(o.vertical_equilibrium_residual_N,5)+" N.");
 }else{
  insertLine(status,"p",(o.source_seismic_combination?"Trial combination with centred lateral loading. ":"Trial combination with gravity loading. ")+"Force balance difference "+
      fmt(Math.max(...o.force_residual_N),5)+" N. "+
      (o.source_seismic_combination?"Seismic source requires unresolved mass, mesh and ±5% eccentricity qualification.":
       "Gravity solution is valid only for source-connected 103-shell coarse research structure."));
 }
 insertLine(status,"p","Full original ETABS21 solver reproduced: NO · Original all 115 shells supported: NO · F3 safe: NO.");
 for(const [id,start] of [["r610-actions-i",0],["r610-actions-j",6]]){
  const parent=by(id);parent.replaceChildren();
  for(let i=0;i<6;i++){
   const k=["N","Vy","Vz","T","My","Mz"][i],units=i<3?"kN":"kN·m";
   signedRow(parent,k,vals[start+i],units);
  }
 }
 const link=by("r610-case-source-link");link.replaceChildren();
 const a=document.createElement("a");a.href="etabs21-member-book.html?member="+encodeURIComponent(trialMember);
 a.textContent="Inspect original ETABS21 beam/column "+trialMember+" in linked 2D and 3D →";link.append(a);
}
function loadCasebook(){
 fetch("data/r6p10-connected-shell-gravity-casebook.json",{cache:"no-store"})
 .then(r=>r.ok?r.json():Promise.reject(Error("Bounded research casebook not published")))
 .then(raw=>{
  if(raw.schema!=="jp.structural.r6p10.connected_source_shell_gravity_and_conditional_seismic_casebook.v0.2"||
     raw.original_shells_source_vertically_unanchored!==12||
     raw.replayed_source_gravity_pattern_cases!==8||
     raw.replayed_source_conditional_seismic_pattern_cases!==4||
     raw.recombined_original_source_linear_add_expressions!==22||
     raw.F3_one_way_shear_unsafe!==true||raw.engineering_approval!==false||
     raw.all_source_gravity_and_seismic_combination_envelopes_reproduced!==false)
     throw Error("Casebook safety/source validation failed");
  researchBook=raw;casebookOptions();
  by("r610-trial-role").addEventListener("change",()=>{
    trialRole=by("r610-trial-role").value;casebookOptions();});
  by("r610-trial-case").addEventListener("change",()=>{
    trialCase=by("r610-trial-case").value;showCasebook();});
  by("r610-trial-member").addEventListener("change",()=>{
    trialMember=by("r610-trial-member").value;showCasebook();});
 }).catch(err=>{
  by("r610-case-status").textContent="No qualified casebook available: "+err.message+
    ". No missing seismic force values will be fabricated.";
 });
}

function init(data){
 if(data.schema!=="jp.structural.r6p10.original_e2k_source_shell_mesh_and_loadcase_audit.v0.1" ||
 data.source_shell_count!==115||data.source_diaphragm_points_total!==201||
 data.shells_without_verified_vertical_support_path!==12||data.engineering_approval!==false||
 data.source_F3_one_way_shear_unsafe!==true)throw Error("Source scope or engineering acceptance incorrectly changed");
 d=data;facts();buildSelect();redraw();lines();pattern();combos();loadCasebook();
 if(data.r6p11_contact_audit?.groups?.length===3){
  by("r611-group").addEventListener("change",()=>{
   contactGroup=by("r611-group").value;
   const g=data.r6p11_contact_audit.groups.find(x=>x.id===contactGroup);
   if(!g)return;
   floor=g.story;by("r610-floor").value=floor;
   selected=g.candidates[0].source_shell;
   filter="ALL";by("r610-filter").value=filter;by("r611-view-filter").value=filter;
   buildSelect();redraw();
  });
  by("r611-view-filter").addEventListener("change",()=>{
   filter=by("r611-view-filter").value;
   by("r610-filter").value=filter;buildSelect();redraw();
  });
 }

 by("r610-floor").addEventListener("change",()=>{floor=by("r610-floor").value;buildSelect();redraw();});
 by("r610-filter").addEventListener("change",()=>{filter=by("r610-filter").value;if(by("r611-view-filter")&&["ALL","SUPPORTED"].includes(filter))by("r611-view-filter").value=filter;buildSelect();redraw();});
 by("r610-shell").addEventListener("change",()=>{selected=by("r610-shell").value;redraw();});
 by("r610-rot-left").addEventListener("click",()=>{yaw-=Math.PI/12;redraw();});
 by("r610-rot-right").addEventListener("click",()=>{yaw+=Math.PI/12;redraw();});
 by("r610-line").addEventListener("change",()=>{lineKey=by("r610-line").value;lineDetail();});
 by("r610-role").addEventListener("change",()=>{role=by("r610-role").value;combos();});
 by("r610-combo").addEventListener("change",()=>{comboKey=by("r610-combo").value;combo();});
 fetch("data/r6p10-source-connected-shell-trial.json",{cache:"no-store"}).then(r=>r.ok?r.json():null)
  .then(x=>viewSolver(x)).catch(()=>viewSolver(null));
}
fetch("data/r6p10-source-shell-diaphragm-loads.json",{cache:"no-store"}).then(r=>{
 if(!r.ok)throw Error("Governed shell source audit not yet deployed");
 return r.json();
}).then(init).catch(e=>{
 by("r610-facts").textContent="Source-connected shell QA unavailable: "+e.message;
 by("r610-shell-detail").textContent="No numerical or engineering results will be fabricated while input checks fail.";
});
})();
