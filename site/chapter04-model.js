/* Chapter 4 public read-only provenance explorer. No client FE solving or design sign-off. */
(()=>{"use strict";
const $=id=>document.getElementById(id),svgNS="http://www.w3.org/2000/svg";
if(!$("c04-plan"))return;
const text=(tag,value)=>{const el=document.createElement(tag);el.textContent=String(value);return el};
const fmt=(v,p=3)=>Number.isFinite(v)?v.toLocaleString("en-US",{maximumFractionDigits:p,minimumFractionDigits:p}):"—";
function gridTable(headings,rows){
 const t=document.createElement("table"),h=document.createElement("thead"),b=document.createElement("tbody"),r=document.createElement("tr");
 headings.forEach(v=>r.append(text("th",v)));h.append(r);
 rows.forEach(vals=>{const tr=document.createElement("tr");vals.forEach(v=>tr.append(text("td",v)));b.append(tr)});
 t.append(h,b);return t;
}
function val(d){
 if(d.schema!=="jp.structural.g15.chapter04.source_model_load_graph.v0.1" ||
 d.engineering_approval!==false || d.original_ETABS_model_authenticated!==false ||
 d.original_F3_one_way_shear!=="NOT SAFE IN ONE WAY SHEAR" ||
 d.counts?.nodes!==92 || d.counts?.members!==165 ||
 d.counts?.supports!==23 || d.counts?.trial_load_assignments!==345 ||
 d.counts?.source_gate20_open!==15 || d.counts?.source_unverified_connectors!==6 ||
 d.nodes?.length!==92 || d.elements?.length!==165 || d.trial_nodal_loads?.length!==345 ||
 d.solved_cases?.length!==5 || d.unassigned_source_report_load_rates?.length!==8 ||
 d.solved_cases.some(c=>c.assignment_count!==69||c.signed_member_end_records!==165||
 c.force_residual_kN>=0.001||c.moment_residual_kNm>=0.001) ||
 d.unassigned_source_report_load_rates.some(x=>x.assigned_to_solver!==false || x.physical_object_id!==null))
 throw Error("Chapter 4 ledger invalid or source acceptance changed");
}
function svg(tag,attrs){
 const e=document.createElementNS(svgNS,tag);
 Object.entries(attrs).forEach(([k,v])=>e.setAttribute(k,String(v)));return e;
}
function build(d){
 const ids=new Map(d.nodes.map(n=>[n.id,n])),objects=new Map(d.elements.map(e=>[e.id,e]));
 const viewer=$("c04-plan"),inspector=$("c04-member-view");
 const caseSelect=$("c04-case"), levelSelect=$("c04-level");
 const cases=d.solved_cases.map(c=>c.id);
 caseSelect.replaceChildren(...cases.map(c=>{const x=text("option",c);x.value=c;return x}));
 levelSelect.replaceChildren(...[1,2,3].map(i=>{const x=text("option","Level "+i+" · "+fmt(i*3.048)+" m");x.value=String(i);return x}));
 function show(e){
  const a=ids.get(e.node_i),b=ids.get(e.node_j);
  const props=[
   ["Model member",e.id],["OpenSees element tag",e.solver_tag],
   ["Source classification",e.status],["Connectivity",e.connection_status],
   ["Position i → j",a.xyz_m.map(n=>fmt(n)).join(", ")+" → "+b.xyz_m.map(n=>fmt(n))+" m"],
   ["Section / material",e.section_id+" / "+e.material_id],
   ["Source observation",e.source_observation_id],
   ["Original ETABS object ID","MISSING · not authenticated"],
   ["Structural approval","HOLD · no signed source geometry"]];
  inspector.replaceChildren(gridTable(["Member provenance","Value"],props));
  const link=$("c04-view3d");
  if(link)link.textContent="Open 3D Structural Studio (trial geometry)";
 }
 function renderPlan(){
  const level=Number(levelSelect.value),els=d.elements.filter(x=>x.type==="BEAM"&&x.storey===level);
  viewer.replaceChildren();
  const plan=svg("svg",{viewBox:"-35 -35 750 445",role:"img","aria-label":"Selectable provisional frame plan at level "+level});
  const coords=n=>{const c=ids.get(n).xyz_m;return [18+c[0]*31,375-c[1]*25]};
  plan.append(svg("rect",{x:0,y:0,width:750,height:445,fill:"#f8faf9",rx:9}));
  for(const e of els){
   const a=coords(e.node_i),b=coords(e.node_j);
   const isTrial=e.connection_status==="UNVERIFIED_CONNECTOR";
   const line=svg("line",{x1:a[0],y1:a[1],x2:b[0],y2:b[1],
    stroke:isTrial?"#c16f52":"#2c7b8a","stroke-width":isTrial?7:5,
    "stroke-linecap":"round","stroke-dasharray":isTrial?"7 7":"none",
    tabindex:0,role:"button","aria-label":e.id+" "+e.connection_status});
   line.style.cursor="pointer";
   line.addEventListener("click",()=>show(e));
   line.addEventListener("keydown",event=>{if(event.key==="Enter"||event.key===" "){event.preventDefault();show(e)}});
   plan.append(line);
  }
  const byPoint=d.nodes.filter(n=>n.storey===level);
  byPoint.forEach(n=>{
   const [x,y]=coords(n.id);
   plan.append(svg("circle",{cx:x,cy:y,r:5,fill:"#184e62",stroke:"white","stroke-width":1.3}));
   const lbl=svg("text",{x:x+6,y:y-7,fill:"#344d59","font-size":12});lbl.textContent=n.grid;plan.append(lbl);
  });
  viewer.append(plan);
  $("c04-plan-caption").textContent="Level "+level+" · "+els.length+" provisional beam spans, including 2 unverified orange connectors. Select a beam for source identity; columns and supports are listed separately.";
  if(els.length)show(els[0]);
 }
 levelSelect.addEventListener("change",renderPlan);
 caseSelect.addEventListener("change",()=>{
  const c=d.solved_cases.find(x=>x.id===caseSelect.value);
  if(!c)return;
  $("c04-force-view").replaceChildren(gridTable(["Trial case","Applied ΣFx, Fy, Fz (kN)","OpenSees ΣRx, Ry, Rz (kN)","Residual force / moment"],
   [[c.id,c.sum_applied_force_xyz_kN.map(x=>fmt(x,4)).join(" / "),
   c.sum_opensees_reactions_xyz_kN.map(x=>fmt(x,4)).join(" / "),
   fmt(c.force_residual_kN,8)+" kN / "+fmt(c.moment_residual_kNm,8)+" kN·m"]]));
  $("c04-load-example").replaceChildren(gridTable(["Load record","Target trial node","Force XYZ (kN)","Basis"],
    d.trial_nodal_loads.filter(x=>x.pattern_id===c.id).slice(0,6).map(x=>[
      x.id,x.target_node_id,x.force_xyz_kN.map(y=>fmt(y,4)).join(", "),x.distribution])));
 });
 const metrics=[
  ["Nodes",d.counts.nodes],["Members",d.counts.members],
  ["Trial supports",d.counts.supports],["Assumed connectors",d.counts.source_unverified_connectors],
  ["Trial load records",d.counts.trial_load_assignments],["Signed OpenSees case-actions",d.counts.open_sees_signed_member_case_records]
 ];
 $("c04-metrics").replaceChildren(...metrics.map(([a,b])=>{const v=text("div","");v.className="rb-ch4-stat";
 v.append(text("strong",b),text("small",a));return v}));
 $("c04-unassigned").replaceChildren(gridTable(["Original report rate ID","Source-described use","Source rate","Applied to authentic source object?"],
 d.unassigned_source_report_load_rates.map(x=>[x.id,x.description,fmt(x.reported_value,3)+" "+x.unit,"NO · object ID missing"])));
 $("c04-supports").replaceChildren(gridTable(["Sample support","Trial fixed DOFs","Real foundation evidence"],
 d.supports.slice(0,7).map(s=>[s.node_id,s.restrained_dofs.join(", "),"MISSING — "+s.status])));
 renderPlan();caseSelect.dispatchEvent(new Event("change"));
 $("c04-evidence").textContent="All 15 Gate20 obligations remain open. The model graph indexes OpenSees trial tags only. Original ETABS joint/frame/area identities, slab polygons, floor finishes, wall paths, mass source and foundation fixity are unverified. F3: NOT SAFE IN ONE WAY SHEAR.";
}
fetch("data/g15-chapter04-model-graph.v0.1.json",{cache:"no-store"}).then(r=>r.ok?r.json():Promise.reject(Error("Chapter 4 ledger missing")))
.then(d=>{val(d);build(d)}).catch(e=>{const p=text("p","Evidence withheld: "+e.message);p.style.color="#833b33";$("c04-metrics").replaceChildren(p);});
})();