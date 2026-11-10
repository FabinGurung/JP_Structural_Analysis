/* R6.14 original shell-source edge matching only; zero approved structural connections. */
(()=>{"use strict";
const $=id=>document.getElementById(id);
const NS="http://www.w3.org/2000/svg";
const n=(tag,value,cls)=>{
 const el=document.createElement(tag);if(value!==null&&value!==undefined)el.textContent=String(value);
 if(cls)el.className=cls;return el;
};
const f=(x,places=3)=>Number.isFinite(Number(x))?Number(x).toLocaleString("en-US",
 {maximumFractionDigits:places,minimumFractionDigits:places}):"—";
const svg=(tag,attrs,text)=>{
 const el=document.createElementNS(NS,tag);for(const [k,v] of Object.entries(attrs))el.setAttribute(k,String(v));
 if(text!==undefined)el.textContent=String(text);return el;
};
let data=null,chosen=null;
const filters=["r614-storey","r614-status","r614-query"];
function stats(){
 const c=data.coverage,host=$("r614-kpis");host.replaceChildren();
 for(const [label,val] of [
  ["Original shell objects",c.original_shells],["Original beam objects",c.original_beams],
  ["Source graph connected shells",c.source_graph_shells_connected],
  ["Original unsupported shells",c.source_graph_shells_without_base_path],
  ["Geometrically complete floor shells",c.conditional_complete_perimeter_shells],
  ["Withheld source shells",c.withheld_shells],
  ["Conditional tributary area, m²",f(c.conditional_projected_area_m2,3)],
  ["Candidate beams",c.beams_with_conditional_tributary_areas]]){
  const box=n("div",null,"r614-kpi");box.append(n("small",label),n("strong",val));host.append(box);
 }
 const breakdown=$("r614-status-breakdown");breakdown.replaceChildren();
 for(const [key,count] of Object.entries(c.status_counts)){
  breakdown.append(n("span",key.replaceAll("_"," ").toLowerCase()+" · "+count,"r614-pill"));
 }
}
function selectedList(){
 const story=$("r614-storey").value,status=$("r614-status").value,q=$("r614-query").value.trim().toUpperCase();
 return data.shells.filter(s=>(story==="ALL"||s.story===story)&&
   (!q||s.shell_key.toUpperCase().includes(q)||s.source_section.toUpperCase().includes(q))&&
   (status==="ALL"||status==="CONDITIONAL"&&s.status.startsWith("CONDITIONAL_")||
    status==="WITHHELD"&&!s.status.startsWith("CONDITIONAL_")||
    status==="UNSUPPORTED"&&!s.source_graph_has_base_path));
}
function td(parent,value){parent.append(n("td",value));}
function shells(){
 const rows=selectedList(),host=$("r614-shells");host.replaceChildren();
 for(const row of rows){
  const tr=n("tr");
  for(const value of [row.shell_key,row.kind,f(row.projected_area_m2,3),
     row.source_graph_has_base_path?"Graph path exists":"No verified source graph path",
     row.status.replaceAll("_"," ").toLowerCase()])td(tr,value);
  const action=n("td"),button=n("button","Inspect");
  button.type="button";button.setAttribute("aria-label","Inspect source shell "+row.shell_key);
  button.onclick=()=>{chosen=row.shell_key;detail();};
  action.append(button);tr.append(action);host.append(tr);
 }
 if(!rows.length){const tr=n("tr"),cell=n("td","No original shell matches these filters");
   cell.colSpan=6;tr.append(cell);host.append(tr);}
 $("r614-result-count").textContent=rows.length+" original source objects displayed.";
 if(!rows.some(r=>r.shell_key===chosen))chosen=rows[0]?.shell_key??null;
 detail();
}
function diagram(row){
 const vertices=row.vertices_xyz_mm;
 const x=vertices.map(p=>Number(p[0])),y=vertices.map(p=>Number(p[1]));
 const loX=Math.min(...x),hiX=Math.max(...x),loY=Math.min(...y),hiY=Math.max(...y);
 const span=Math.max(hiX-loX,hiY-loY,1000),scale=250/span;
 const pos=p=>[320+(Number(p[0])-(loX+hiX)/2)*scale,205-(Number(p[1])-(loY+hiY)/2)*scale];
 const plot=svg("svg",{viewBox:"0 0 640 410",role:"img",
   "aria-label":"Schematic source XYZ shell plan, edge labels and geometric beam contacts",class:"r614-diagram"});
 plot.append(svg("text",{x:18,y:22,fill:"#375a6e","font-size":13},
   "Original source corners and edge candidate status (not support acceptance)"));
 if(vertices.length!==4){plot.append(svg("text",{x:30,y:60},"Original polygon has "+vertices.length+" corners"));return plot;}
 const status= row.edges??[];
 const points=vertices.map(pos);
 for(let i=0;i<4;i++){
  const a=points[i],b=points[(i+1)%4];
  const full=status[i]?.full_edge_candidate_beams??[];
  const partial=status[i]?.partial_edge_candidate_beams??[];
  const col=full.length===1?"#247d82":full.length>1?"#a57933":partial.length?"#b57632":"#b34b40";
  plot.append(svg("line",{x1:a[0],y1:a[1],x2:b[0],y2:b[1],stroke:col,
   "stroke-width":5,"stroke-dasharray":full.length===1?"none":"9 5"}));
  const mid=[(a[0]+b[0])/2,(a[1]+b[1])/2];
  const msg="Edge "+(i+1)+" · "+(full.length===1?full[0].beam_key:
     full.length>1?"Ambiguous":partial.length?"Partial":"No full beam");
  plot.append(svg("text",{x:mid[0],y:mid[1]-10,fill:col,"text-anchor":"middle",
      "font-size":12,"font-weight":"700"},msg));
 }
 for(let i=0;i<4;i++){
  const [a,b]=points[i];
  plot.append(svg("circle",{cx:a,cy:b,r:5,fill:"#23495c",stroke:"#fff","stroke-width":1}));
  plot.append(svg("text",{x:a+9,y:b+15,"font-size":11,fill:"#34546a"},
      "P"+row.source_corner_ids[i]+" / "+f(vertices[i][2],0)+" mm"));
 }
 return plot;
}
function detail(){
 const host=$("r614-details");host.replaceChildren();
 const row=data.shells.find(s=>s.shell_key===chosen);
 if(!row){host.append(n("p","Select a shell to inspect its source geometry."));return;}
 host.append(n("h3",row.shell_key+" · "+row.kind+" · "+row.source_section));
 host.append(n("p","Original projected area: "+f(row.projected_area_m2,4)+
    " m²; slab true-area selfweight proxy: "+f(row.true_area_ownweight_proxy_kN,3)+" kN. " +
    "Source graph base path: "+(row.source_graph_has_base_path?"present (not solver proven)":"not established")+"."));
 host.append(n("p","Decision: "+row.status.replaceAll("_"," ")+". Any visible slab-to-beam candidate is geometric only.","r614-notice"));
 host.append(diagram(row));
 if(row.edges?.length){
  const grid=n("div",null,"r614-edgegrid");
  for(const edge of row.edges){
   const card=n("div",null,"r614-edge");
   card.append(n("strong","Source edge "+(edge.edge_index+1)+" · "+f(edge.length_mm/1000,3)+" m"));
   card.append(n("p","Original corner IDs: "+edge.corner_source_point_ids.join(" → ")));
   const full=edge.full_edge_candidate_beams,partial=edge.partial_edge_candidate_beams;
   card.append(n("p",full.length?("Full-length beam candidates: "+
       full.map(x=>x.beam_key+" ["+x.match_type.replaceAll("_"," ").toLowerCase()+"]").join(", ")):
       "Full-length beam candidate: none"));
   if(partial.length)card.append(n("p","Partial collinear candidates (WITHHELD): "+
       partial.map(x=>x.beam_key+" ("+f(x.overlap_mm/1000,3)+" m)").join(", ")));
   card.append(n("small","Native analysis joint or constraint: NOT VERIFIED"));
   grid.append(card);
  }
  host.append(grid);
 }else host.append(n("p","Non-floor shell: no floor-edge tributary assignment attempted."));
 const applied=Object.entries(row.original_source_assigned_resultants_kN)
    .filter(([_,v])=>v!==0);
 if(applied.length){
  host.append(n("h4","Original assigned shell resultants (not already factored)"));
  host.append(n("p",applied.map(([k,v])=>k+": "+f(v,4)+" kN").join(" · ")));
 }
 if(row.conditional_45deg_geometry_allocations.length){
  host.append(n("h4","Conditional 45° two-way area split (NOT an accepted load path)"));
  const table=n("table");const th=n("tr");
  for(const val of ["Edge","Original beam","Area, m²","Area share","Own weight, kN","Live, kN","Finish, kN"])
    th.append(n("th",val));table.append(th);
  for(const a of row.conditional_45deg_geometry_allocations){
   const tr=n("tr");
   for(const val of [a.edge_index+1,a.beam_key,f(a.area_m2,4),
     f(100*a.fraction_of_shell,2)+"%",
     f(a.conditional_source_resultants_kN.GROSS_SELFWEIGHT_PROXY,3),
     f(a.conditional_source_resultants_kN.Live??0,3),
     f(a.conditional_source_resultants_kN["FLOOR FINISH"]??0,3)])td(tr,val);
   table.append(tr);
  }
  host.append(table);
  host.append(n("p","Working: for a ≥ b, each short edge receives b²/4; each long edge receives ab/2 − b²/4. Conditional load share = original shell load × area share. All four shares sum to the original shell area and respective source loads, but do not prove physical transfer."));
 }else{
  host.append(n("p","No speculative load has been redistributed to incomplete, ambiguous, nonrectangular or unsupported slab perimeters.","r614-notice"));
 }
 host.append(n("p","Check: source coordinates, same-storey edge identity and load/area conservation were inspected. Missing solver joints, mesh continuity, releases and supported gravity reactions prevent design acceptance.","r614-muted"));
}
function beams(){
 const host=$("r614-beams");host.replaceChildren();
 for(const beam of data.beam_conditional_totals){
  const tr=n("tr"),k=beam.conditional_source_resultants_kN;
  for(const val of [beam.beam_key,beam.story,beam.geometrically_matching_shell_edge_count,
    f(beam.matched_tributary_area_m2,4),f(k.GROSS_SELFWEIGHT_PROXY??0,3),
    f(k.Live??0,3),f(k["FLOOR FINISH"]??0,3),"NOT VERIFIED"])td(tr,val);
  host.append(tr);
 }
 if(!data.beam_conditional_totals.length){const tr=n("tr"),cell=n("td",
   "No original slabs satisfy the strict four-beam rectangular candidate gate; no slab loads attributed.");
   cell.colSpan=8;tr.append(cell);host.append(tr);}
}
function init(d){
 if(d?.schema!=="jp.structural.r6p14.slab_beam_geometric_tributary_reconciliation.v0.1"||
   d.coverage?.original_shells!==115||d.coverage.source_graph_shells_connected!==103||
   d.coverage.source_graph_shells_without_base_path!==12||
   d.twelve_unsupported_shells_excluded!==true||
   d.F3_one_way_shear_unsafe!==true||d.engineering_approval!==false||
   d.physical_vertical_force_transfer_verified!==false||
   d.native_generated_joint_or_edge_constraint_verified!==false||
   d.no_source_gravity_load_case_modified!==true||
   d.no_original_design_member_actions_modified!==true||
   d.shells?.length!==115)throw Error("Original-source proof or structural HOLD changed");
 data=d;stats();for(const id of filters)$(id).addEventListener(id==="r614-query"?"input":"change",shells);
 const requested=new URL(window.location.href).searchParams.get("shell");
 if(d.shells.some(s=>s.shell_key===requested))chosen=requested;
 shells();beams();
}
fetch("../../data/r6p14-slab-beam-tributary-audit.json",{cache:"no-store"})
 .then(r=>r.ok?r.json():Promise.reject(Error("R6.14 data was not published")))
 .then(init).catch(err=>{
  $("r614-kpis").textContent="Source evidence unavailable: "+err.message;
  $("r614-shells").replaceChildren();$("r614-beams").replaceChildren();
  $("r614-details").textContent="No conditional or accepted slab load data available.";
 });
})();