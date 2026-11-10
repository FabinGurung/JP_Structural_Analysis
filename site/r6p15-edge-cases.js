/* R6.15: 77 original source slab-perimeter case studies; no approved support. */
(()=>{"use strict";
const by=id=>document.getElementById(id),NS="http://www.w3.org/2000/svg";
const elt=(tag,value,cls)=>{const e=document.createElement(tag);if(value!==null&&value!==undefined)e.textContent=String(value);if(cls)e.className=cls;return e};
const sf=(tag,attrs={},text)=>{const e=document.createElementNS(NS,tag);for(const [k,v] of Object.entries(attrs))e.setAttribute(k,String(v));if(text!==undefined)e.textContent=String(text);return e};
const num=(x,p=2)=>Number.isFinite(Number(x))?Number(x).toLocaleString("en-US",{maximumFractionDigits:p,minimumFractionDigits:p}):"unknown";
const words=k=>String(k).replaceAll("_"," ").toLowerCase();
let dataset=null,selected=null;
function addCounts(hostId,obj){const parent=by(hostId);parent.replaceChildren();
 for(const [name,count] of Object.entries(obj))parent.append(elt("span",words(name)+" · "+count,"r615-chip"));
 if(!Object.keys(obj).length)parent.append(elt("span","None meets the strictly hypothetical geometry gate","r615-muted"));
}
function renderSummary(){
 const c=dataset.coverage,items=[
 ["Original incomplete slabs",c.slabs_examined],["Source edges individually checked",c.source_edges_examined],
 ["Ground-floor cases",c.by_story.GF??0],["First-floor cases",c.by_story.FF??0],
 ["Top-floor cases",c.by_story.TF??0],
 ["Slabs with neighbouring FLOOR geometry",c.slabs_with_adjacent_floor_geometry],
 ["Slabs with non-sectioned LINE geometry",c.slabs_with_nonsectioned_lines_along_edges],
 ["Purely hypothetical slab cases",c.slabs_with_geometry_only_hypotheses]];
 const host=by("r615-kpis");host.replaceChildren();
 for(const [label,v] of items){const b=elt("div",null,"r615-kpi");b.append(elt("small",label),elt("strong",v));host.append(b)}
 addCounts("r615-groups",c.review_group_counts);
 addCounts("r615-edgecounts",c.frame_edge_class_counts);
 addCounts("r615-hypotheses",c.hypothesis_counts);
 const select=by("r615-group");for(const value of Object.keys(c.review_group_counts)){
  const option=elt("option",words(value));option.value=value;select.append(option);
 }
}
function cases(){
 const story=by("r615-story").value,group=by("r615-group").value,
  scenario=by("r615-scenario").value,q=by("r615-query").value.trim().toUpperCase();
 const exact=q&&dataset.cases.some(d=>d.shell_key.toUpperCase()===q);
 return dataset.cases.filter(d=>(story==="ALL"||d.story===story)&&
   (group==="ALL"||d.review_group===group)&&
   (!q||(exact?d.shell_key.toUpperCase()===q:d.shell_key.toUpperCase().includes(q)))&&
   (scenario==="ALL"||scenario==="NONE"&&!d.provisional_scenarios.length||
    scenario==="ONE_WAY"&&d.provisional_scenarios.some(s=>s.scenario.includes("ONE_WAY"))||
    scenario==="CANTILEVER"&&d.provisional_scenarios.some(s=>s.scenario.includes("CANTILEVER"))));
}
function cell(row,text){row.append(elt("td",text));}
function renderRows(){
 const records=cases(),table=by("r615-rows");table.replaceChildren();
 for(const item of records){
  const row=elt("tr");
  for(const val of [item.shell_key,item.story,num(item.projected_area_m2,3),
   item.complete_frame_edge_count,item.incomplete_frame_gap_edge_count,
   item.ambiguous_overlap_edge_count,words(item.review_group)])cell(row,val);
  const action=elt("td"),button=elt("button","Inspect");
  button.type="button";button.setAttribute("aria-label","Inspect source "+item.shell_key);
  button.onclick=()=>{selected=item.shell_key;detail()};
  action.append(button);row.append(action);table.append(row);
 }
 if(!records.length){const tr=elt("tr"),td=elt("td","No unresolved original source shells match the filters");td.colSpan=8;tr.append(td);table.append(tr)}
 by("r615-count").textContent=records.length+" of 77 original incomplete-perimeter cases shown. No accepted loads or solver reactions.";
 if(!records.some(x=>x.shell_key===selected))selected=records[0]?.shell_key??null;
 detail();
}
function diagram(d){
 const vertices=d.vertices_xyz_mm;
 const s=sf("svg",{viewBox:"0 0 760 480",role:"img",
    "aria-label":"Original shell plan with beam-segment gaps, full edges and overlaps",class:"r615-diagram"});
 s.append(sf("text",{x:16,y:22,"font-size":13,fill:"#365a6c"},
   "Source XYZ slab edges only · no real support continuity verified"));
 if(vertices.length!==4){s.append(sf("text",{x:20,y:60},"Non-four-sided original source polygon"));return s}
 const X=vertices.map(v=>Number(v[0])),Y=vertices.map(v=>Number(v[1]));
 const x0=Math.min(...X),x1=Math.max(...X),y0=Math.min(...Y),y1=Math.max(...Y);
 const scale=290/Math.max(x1-x0,y1-y0,1);
 const pt=p=>[370+(Number(p[0])-(x1+x0)/2)*scale,
    234-(Number(p[1])-(y1+y0)/2)*scale];
 const pts=vertices.map(pt);
 for(const e of d.edge_cases){
  const a=pts[e.edge_index],b=pts[(e.edge_index+1)%4];
  const colors={
   SINGLE_COMPLETE_FRAME_BEAM:"#188577",
   COMPLETE_SEGMENTED_FRAME_CHAIN_GEOMETRIC_ONLY:"#568c4e",
   NO_COLLINEAR_FRAME_BEAM:"#b35d43",
   PARTIAL_FRAME_EDGE_WITH_GAP:"#d09a33",
   COMPETING_FULL_AND_PARTIAL_BEAMS:"#93649c",
   AMBIGUOUS_MULTIPLE_FULL_BEAMS:"#93649c",
   COMPLETE_BUT_OVERLAPPING_FRAME_SEGMENTS:"#93649c"
  };
  const color=colors[e.frame_match_class]||"#b05a3f";
  s.append(sf("line",{x1:a[0],y1:a[1],x2:b[0],y2:b[1],
       stroke:"#d9e5e8","stroke-width":10,"stroke-linecap":"round"}));
  for(const t of e.frame_intervals){
   const lerp=(p,q,k)=>p+(q-p)*k;
   s.append(sf("line",{x1:lerp(a[0],b[0],t.start_fraction),
    y1:lerp(a[1],b[1],t.start_fraction),x2:lerp(a[0],b[0],t.end_fraction),
    y2:lerp(a[1],b[1],t.end_fraction),stroke:color,"stroke-width":5}));
  }
  const midX=(a[0]+b[0])/2,midY=(a[1]+b[1])/2;
  s.append(sf("text",{x:midX,y:midY-12,fill:color,"font-size":12,
   "font-weight":700,"text-anchor":"middle"},"E"+(e.edge_index+1)+
    " · "+(e.frame_intervals.length?e.frame_intervals.length+" beam segments":"no frame beam")));
 }
 pts.forEach((p,i)=>{
  s.append(sf("circle",{cx:p[0],cy:p[1],r:5,fill:"#234a61",stroke:"#fff","stroke-width":1}));
  s.append(sf("text",{x:p[0]+9,y:p[1]+15,fill:"#365b6f","font-size":11},
    "P"+d.source_corner_ids[i]));
 });
 s.append(sf("text",{x:16,y:456,fill:"#3d6875","font-size":12},
  "Green: geometric length covered | Orange: gap | Purple: competing beams | Not design"));
 return s;
}
function tableOfScenario(caseBox,scenario){
 const entries=scenario.scenario.includes("ONE_WAY")?
  Object.entries(scenario.each_edge_example.source_uniform_resultants_half_kN).map(([k,v])=>[k,num(v,4)+" kN at each opposite edge"]):
  Object.entries(scenario.hypothetical_uniform_load_root_M_kNm).map(([k,v])=>[k,num(v,4)+" kN·m at hypothetical root"]);
 const t=elt("table",null,"r615-data"),head=elt("tr");
 for(const h of ["Original input pattern / proxy","Hypothetical arithmetic"])head.append(elt("th",h));
 t.append(head);
 for(const row of entries){const tr=elt("tr");row.forEach(v=>tr.append(elt("td",v)));t.append(tr)}
 caseBox.append(t);
}
function detail(){
 const d=dataset.cases.find(x=>x.shell_key===selected),host=by("r615-detail");host.replaceChildren();
 if(!d){host.append(elt("p","Choose a source slab to inspect the detailed geometry."));return}
 host.append(elt("h3",d.shell_key+" · "+d.story+" · "+d.source_section));
 host.append(elt("p","Original slab area "+num(d.projected_area_m2,4)+" m² · "+
  d.complete_frame_edge_count+" fully geometrically covered source edges · "+
  d.incomplete_frame_gap_edge_count+" partial/gap edges · "+
  d.ambiguous_overlap_edge_count+" ambiguous/overlap edges."));
 host.append(elt("p","Review group: "+words(d.review_group)+
  ". Original R6.14 decision: "+words(d.historical_R614_status)+".","r615-case"));
 host.append(diagram(d));
 const grid=elt("div",null,"r615-evidence-grid");
 for(const e of d.edge_cases){
  const card=elt("div",null,"r615-edge");
  card.append(elt("strong","Edge "+(e.edge_index+1)+" · "+num(e.edge_length_mm/1000,3)+" m · "+words(e.frame_match_class)));
  card.append(elt("p","Original corner IDs: "+e.source_corner_ids.join(" → ")));
  card.append(elt("p","Source beam candidates: "+(e.frame_intervals.map(v=>v.beam_key).join(", ")||"none")));
  card.append(elt("p","Beam coverage: "+num(e.partition.covered_fraction*100,2)+"% · gaps "+
   num(e.partition.total_gap_mm,3)+" mm · overlap "+num(e.partition.overlap_length_mm,3)+" mm."));
  if(e.partition.gaps.length)card.append(elt("p","Uncovered intervals: "+
    e.partition.gaps.map(g=>num(g.start_fraction*100,2)+"–"+num(g.end_fraction*100,2)+"% ("+num(g.length_mm,2)+" mm)").join("; ")));
  if(e.adjacent_floor_shells_geometric_only.length)card.append(elt("p",
   "Touching FLOOR geometry (not a structural support): "+
    [...new Set(e.adjacent_floor_shells_geometric_only.map(x=>x.source_key))].join(", ")));
  if(e.coincident_unsectioned_SOURCE_LINE_not_a_beam.length)card.append(elt("p",
    "Non-sectioned original LINE geometry (NOT structural beams): "+
    [...new Set(e.coincident_unsectioned_SOURCE_LINE_not_a_beam.map(x=>x.source_key))].join(", ")));
  card.append(elt("small","Generated analysis joint, edge restraint and actual vertical reaction: NOT VERIFIED"));
  grid.append(card);
 }
 host.append(elt("h4","Original beam-alignment evidence (not support acceptance)"),grid);
 host.append(elt("h4","One-way / cantilever hypotheses"));
 if(!d.provisional_scenarios.length)
   host.append(elt("p","No clean opposite-edge or single-root geometric scenario meets this strict source-only filter. Partial, overlapping, neighbouring or missing edge geometry remains unresolved.","r615-case"));
 for(const scenario of d.provisional_scenarios){
  const box=elt("div",null,"r615-case");
  box.append(elt("strong",words(scenario.scenario)));
  if(scenario.scenario.includes("ONE_WAY"))
   box.append(elt("p","Two opposite beam-aligned source edges only. Hypothetical A/2="+
     num(scenario.hypothetical_area_to_each_opposite_edge_m2,4)+" m² to each edge, normal span "+
     num(scenario.normal_span_m,3)+" m. Not verified as a one-way spanning structural plate."));
  else box.append(elt("p","One geometric root edge with three unaligned source frame edges and no recorded adjoining source FLOOR edge. Hypothetical root projection "+
    num(scenario.normal_projection_m,3)+" m; root-fixity and slab anchorage remain UNKNOWN."));
  tableOfScenario(box,scenario);
  box.append(elt("p","Working assumption only: uniformly distributed original shell resultant, idealized boundary conditions, no analysed edge restraints. These forces and moments are NOT design loads."));
  host.append(box);
 }
 const link=elt("a","View this original shell within the full R6.14 register");
 link.href="tributary-audit.html?shell="+encodeURIComponent(d.shell_key);
 host.append(link);
 host.append(elt("p","Engineering check: no signed ETABS21 reactions or compatible native shell/frame joint map; approved beam allocation and verified support fields remain unknown. F3 one-way shear remains unsafe.","r615-muted"));
}
function init(d){
 if(d?.schema!=="jp.structural.r6p15.incomplete_slab_beam_edge_classification.v0.1"||
   d.coverage?.slabs_examined!==77||d.coverage?.source_edges_examined!==308||
   d.baseline?.shells!==115||d.baseline?.r614_complete_four_edge_shells!==25||
   d.baseline?.source_graph_unanchored!==12||d.cases?.length!==77||
   d.F3_one_way_shear_unsafe!==true||d.twelve_unsupported_shells_still_excluded!==true||
   d.engineering_approval!==false||d.member_design_loads_modified!==false||
   d.original_source_gravity_actions_modified!==false||d.shell_contact_gate_promoted!==false)
   throw Error("Source coverage or engineering HOLD failed");
 dataset=d;renderSummary();
 for(const id of ["r615-story","r615-group","r615-scenario","r615-query"])
  by(id).addEventListener(id==="r615-query"?"input":"change",renderRows);
 const requested=new URL(window.location.href).searchParams.get("shell");
 if(d.cases.some(x=>x.shell_key===requested))selected=requested;
 renderRows();
}
fetch("../../data/r6p15-incomplete-slab-edge-audit.json",{cache:"no-store"})
 .then(r=>r.ok?r.json():Promise.reject(Error("R6.15 audit JSON not published")))
 .then(init).catch(err=>{
  by("r615-kpis").textContent="Original R6.15 evidence unavailable: "+err.message;
  by("r615-rows").replaceChildren();
  by("r615-detail").textContent="No design load or verified support can be inferred.";
 });
})();