/* R6.17 inspect original ETABS21 source graph; NEVER auto-connect points or certify supports. */
(()=>{"use strict";
const $=id=>document.getElementById(id),NS="http://www.w3.org/2000/svg";
const n=(tag,value,cls)=>{const e=document.createElement(tag);if(value!==null&&value!==undefined)e.textContent=String(value);if(cls)e.className=cls;return e;};
const svg=(tag,attrs={},value)=>{const e=document.createElementNS(NS,tag);for(const [k,v] of Object.entries(attrs))e.setAttribute(k,String(v));if(value!==undefined)e.textContent=String(value);return e;};
const fmt=(value,p=3)=>Number.isFinite(Number(value))?Number(value).toLocaleString("en-US",{minimumFractionDigits:p,maximumFractionDigits:p}):"Unknown";
let data=null,selected=null,focusSupport=null;
function showNumbers(){
 const c=data.counts,kv=[
  ["Structural frames",c.source_frame_objects],["Source shells",c.source_shell_objects],
  ["Source graph nodes",c.canonical_source_graph_nodes],
  ["Declared source base restraints",c.original_source_fixed_base_point_ids],
  ["Connected research base nodes",c.used_in_current_coarse_FE_fixed_base_nodes],
  ["Original shells still excluded",c.original_unanchored_shells_excluded],
  ["Research gravity runs",c.independently_solved_bounded_gravity_cases],
  ["Individual signed reaction records",c.signed_individual_base_reactions]];
 const host=$("r617-kpis");host.replaceChildren();
 for(const [label,value] of kv){const item=n("div",null,"r617-kpi");item.append(n("small",label),n("strong",value));host.append(item);}
}
function projection(){
 const nodes=data.canonical_nodes;
 const raw=p=>[(p[0]-p[1])*.84,(p[0]+p[1])*.32-p[2]*.87];
 const loc=nodes.map(x=>raw(x.xyz_mm)),min=[Math.min(...loc.map(x=>x[0])),Math.min(...loc.map(x=>x[1]))],
 max=[Math.max(...loc.map(x=>x[0])),Math.max(...loc.map(x=>x[1]))];
 const scale=Math.min(895/Math.max(1,max[0]-min[0]),535/Math.max(1,max[1]-min[1]));
 return pos=>{const p=raw(pos);return [500+(p[0]-(min[0]+max[0])/2)*scale,310+(p[1]-(min[1]+max[1])/2)*scale];};
}
function renderIso(){
 const drawing=$("r617-diagram");drawing.replaceChildren();
 const floor=$("r617-floor").value,showFrames=$("r617-frames").checked,
 showShells=$("r617-shells").checked,highlight=$("r617-unsupported").checked,
 showBase=$("r617-supports").checked;
 const pos=projection(),nodes=new Map(data.canonical_nodes.map(p=>[p.key,p]));
 drawing.append(svg("text",{x:17,y:29,fill:"#3e6370","font-size":15},
  "Source 3D / original ID adjacency — not authenticated solver connections"));
 drawing.append(svg("text",{x:17,y:50,fill:"#506c78","font-size":12},
  "Red = 12 excluded shell objects; blue = frames; base diamonds = used research restraints"));
 if(showShells){
  const polygons=data.canonical_original_shells.filter(p=>floor==="ALL"||p.story===floor);
  polygons.sort((a,b)=>{
    const av=a.corner_xyz_mm.reduce((s,p)=>s+p[1]+p[0],0)/4;
    const bv=b.corner_xyz_mm.reduce((s,p)=>s+p[1]+p[0],0)/4;return av-bv;
  });
  for(const shell of polygons){
   const points=shell.corner_xyz_mm.map(v=>pos(v).map(x=>x.toFixed(2)).join(",")).join(" ");
   const supported=shell.source_graph_base_reachable;
   const color=supported?"#3e999b":"#bf493b";
   if(!supported&&!highlight)continue;
   const el=svg("polygon",{points,fill:color,"fill-opacity":supported?".10":".33",
     stroke:color,"stroke-opacity":supported?".42":".90",
     "stroke-width":selected===shell.key?"3.8":"1.2",
     class:"r617-select"});
   el.addEventListener("click",()=>{
    if(!supported){selected=shell.key;renderExcluded();renderIso();}else{
     $("r617-model-caption").textContent=shell.key+" has a source-graph base path, but its native ETABS21 shell-to-frame transfer is NOT verified.";
    }});
   drawing.append(el);
  }
 }
 if(showFrames){
  for(const member of data.canonical_original_frames){
   if(floor!=="ALL"&&member.source_story!==floor)continue;
   const a=nodes.get(member.node_i),b=nodes.get(member.node_j);
   if(!a||!b)continue;
   const p=pos(a.xyz_mm),q=pos(b.xyz_mm);
   drawing.append(svg("line",{x1:p[0],y1:p[1],x2:q[0],y2:q[1],
    stroke:member.kind==="COLUMN"?"#283d75":"#245970",
    "stroke-opacity":".73","stroke-width":member.kind==="COLUMN"?"2.7":"2.15"}));
  }
 }
 if(showBase){
  for(const key of data.coarse_FE_original_base_id_nodes){
   const p=nodes.get(key);
   if(!p)continue;
   const [x,y]=pos(p.xyz_mm);
   const selectedSupport=focusSupport&&focusSupport.includes(p.source_point_id);
   drawing.append(svg("polygon",{points:[[x,y-5],[x+5,y],[x,y+5],[x-5,y]].map(a=>a.join(",")).join(" "),
    fill:selectedSupport?"#e7a32b":"#343e95",stroke:"#fff","stroke-width":selectedSupport?2:1}));
  }
 }
 if(selected){
  const shell=data.canonical_original_shells.find(x=>x.key===selected);
  if(shell){
   const cent=shell.corner_xyz_mm.reduce((s,p)=>s.map((v,i)=>v+Number(p[i])/4),[0,0,0]);
   const xy=pos(cent);
   drawing.append(svg("text",{x:xy[0],y:xy[1]-10,fill:"#8d1e18","font-weight":"700",
     "font-size":15,"paint-order":"stroke",stroke:"#fff","stroke-width":4},selected));
  }
 }
 const visibleShells=data.canonical_original_shells.filter(s=>floor==="ALL"||s.story===floor);
 $("r617-model-caption").textContent="Visible original shells: "+
 visibleShells.length+"; excluded at source: "+
 visibleShells.filter(s=>!s.source_graph_base_reachable).length+
 ". No new connection is formed when an original shell or support appears close to another.";
}
function filteredExcluded(){
 const q=$("r617-shell-query").value.trim().toUpperCase(),floor=$("r617-shell-floor").value;
 const exact=q&&data.individual_twelve_unanchored_shell_investigations.some(s=>s.shell_key.toUpperCase()===q);
 return data.individual_twelve_unanchored_shell_investigations.filter(s=>
  (floor==="ALL"||s.story===floor)&&
  (!q||(exact?s.shell_key.toUpperCase()===q:s.shell_key.toUpperCase().includes(q))));
}
function addTd(tr,val){tr.append(n("td",val));}
function renderExcluded(){
 const rows=filteredExcluded(),host=$("r617-excluded");host.replaceChildren();
 for(const shell of rows){
  const tr=n("tr"),m=shell.nearest_original_structural_frames[0],
   p=shell.nearest_source_graph_connected_shell_edges_same_storey[0];
  [shell.shell_key,shell.story,shell.original_point_ids.join(" · "),
   m?fmt(m.minimum_corner_to_segment_mm,2):"Unknown",
   p?fmt(p.minimum_corner_to_edge_mm,2):"Unknown","EXCLUDED; support not verified"]
   .forEach(v=>addTd(tr,v));
  const action=n("td"),button=n("button","Inspect");button.type="button";
  button.setAttribute("aria-label","Inspect excluded source shell "+shell.shell_key);
  button.onclick=()=>{selected=shell.shell_key;renderShell();renderIso();};
  action.append(button);tr.append(action);host.append(tr);
 }
 if(!rows.length){const tr=n("tr"),td=n("td","No excluded original shells match this filter");td.colSpan=7;tr.append(td);host.append(tr);}
 if(!rows.some(x=>x.shell_key===selected))selected=rows[0]?.shell_key??null;
 renderShell();renderIso();
}
function renderShell(){
 const shell=data.individual_twelve_unanchored_shell_investigations.find(s=>s.shell_key===selected),
 host=$("r617-selected-shell");host.replaceChildren();
 if(!shell){host.append(n("p","Select an excluded source shell."));return;}
 host.append(n("h3",shell.shell_key+" · "+shell.kind+" · "+shell.story));
 host.append(n("p","Original corner point IDs: "+shell.original_point_ids.join(", ")+
   ". Source component(s): "+shell.source_component_ids.join(", ")+
   ". No source graph path to a declared base restraint; no FE analysis support verified."));
 const grid=n("div",null,"r617-evidence");
 const frame=n("div"),panels=n("div");
 frame.append(n("h4","Closest original frame members — geometry only"));
 for(const m of shell.nearest_original_structural_frames)
  frame.append(n("p",m.member_key+" ("+m.kind+", "+m.story+") · "+fmt(m.minimum_corner_to_segment_mm,3)+" mm gap"));
 panels.append(n("h4","Nearby connected shell boundaries — geometry only"));
 if(!shell.nearest_source_graph_connected_shell_edges_same_storey.length)
   panels.append(n("p","No supported original source shell of this storey."));
 for(const s of shell.nearest_source_graph_connected_shell_edges_same_storey)
   panels.append(n("p",s.shell_key+" · "+fmt(s.minimum_corner_to_edge_mm,3)+" mm gap"));
 grid.append(frame,panels);host.append(grid);
 host.append(n("p","Verdict: source connectivity remains unresolved. This shell is still excluded from the bounded OpenSees study; geometric coincidence alone cannot establish genuine load transfer."));
}
function renderEquilibrium(){
 const role=$("r617-role").value,pattern=$("r617-pattern").value;
 const item=data.coarse_trial_signed_gravity_support_reactions.find(x=>x.role===role&&x.original_source_gravity_pattern===pattern);
 if(!item){$("r617-equil").textContent="No genuine numerical record for this role and gravity pattern.";return;}
 const host=$("r617-equil");host.replaceChildren();
 const values=[
  ["Applied downward source-pattern gravity",fmt(item.applied_gravity_downward_kN,3)+" kN"],
  ["Signed upward base reaction sum",fmt(item.sum_signed_connected_base_reaction_kN[2],3)+" kN"],
  ["Force equilibrium residual",fmt(item.vertical_equilibrium_error_N,5)+" N"],
  ["Maximum permitted numerical residual",fmt(item.vertical_equilibrium_tolerance_N,4)+" N"]];
 for(const [label,val] of values){
  const b=n("div");b.append(n("small",label),n("strong",val));host.append(b);}
 const table=$("r617-reactions");table.replaceChildren();
 for(const r of item.signed_support_reactions){
  const tr=n("tr");
  const values=[r.original_source_base_point_ids.join(", "),
    fmt(r.xyz_mm[0],1),fmt(r.xyz_mm[1],1),
    fmt(r.signed_Rxyz_kN[2],4),fmt(r.signed_Rxyz_kN[0],4),
    fmt(r.signed_Rxyz_kN[1],4),fmt(r.signed_Mxyz_kNm[2],5)];
  for(const v of values)addTd(tr,v);
  tr.addEventListener("click",()=>{focusSupport=r.original_source_base_point_ids;renderIso();});
  tr.style.cursor="pointer";
  tr.title="Highlight original connected source base point in the 3D projection";
  table.append(tr);
 }
}
function init(d){
 const c=d?.counts??{};
 if(d.schema!=="jp.structural.r6p17.canonical_source_topology_and_bounded_gravity.v0.1"||
 c.source_frame_objects!==165||c.source_shell_objects!==115||
 c.original_source_fixed_base_point_ids!==27||c.used_in_current_coarse_FE_fixed_base_nodes!==21||
 c.original_unanchored_shells_excluded!==12||c.independently_solved_bounded_gravity_cases!==8||
 c.signed_individual_base_reactions!==168||d.individual_twelve_unanchored_shell_investigations?.length!==12||
 d.coarse_trial_signed_gravity_support_reactions?.length!==8||
 d.F3_one_way_shear_unsafe!==true||d.engineering_approval!==false||
 d.full_ETABS21_3D_model_reconstructed_and_validated!==false||
 d.no_new_fixed_restraints_or_beam_shell_ties_created!==true||
 d.equilibrium_of_research_gravity_cases_verified!==true)
   throw Error("Governing source counts, research equilibrium or engineering HOLD changed");
 data=d;showNumbers();
 for(const id of ["r617-floor","r617-frames","r617-shells","r617-unsupported","r617-supports"])
  $(id).addEventListener("change",renderIso);
 for(const id of ["r617-shell-query","r617-shell-floor"])
  $(id).addEventListener(id==="r617-shell-query"?"input":"change",renderExcluded);
 for(const id of ["r617-role","r617-pattern"])$(id).addEventListener("change",renderEquilibrium);
 const query=new URL(window.location.href).searchParams.get("shell");
 if(data.individual_twelve_unanchored_shell_investigations.some(x=>x.shell_key===query))selected=query;
 renderExcluded();renderEquilibrium();
}
fetch("../../data/r6p17-canonical-3d-source-graph.json",{cache:"no-store"})
 .then(r=>r.ok?r.json():Promise.reject(Error("R6.17 governed graph not published")))
 .then(init).catch(err=>{
   $("r617-kpis").textContent="R6.17 source evidence unavailable: "+err.message;
   $("r617-diagram").replaceChildren();
   $("r617-excluded").replaceChildren();
   $("r617-equil").textContent="No accepted support or design load can be inferred.";
 });
})();