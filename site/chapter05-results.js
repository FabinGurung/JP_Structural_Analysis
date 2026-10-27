/* Chapter 5: actual OpenSees member-end resisting forces, separate original-PDF claims. */
(()=>{"use strict";
const $=id=>document.getElementById(id),ns="http://www.w3.org/2000/svg";
if(!$("c05-member-diagram"))return;
const el=(tag,txt)=>{const x=document.createElement(tag);if(txt!==undefined)x.textContent=String(txt);return x};
const fmt=(v,n=3)=>Number.isFinite(v)?v.toLocaleString("en-US",{maximumFractionDigits:n,minimumFractionDigits:n}):"—";
const svg=(tag,attrs)=>{const x=document.createElementNS(ns,tag);Object.entries(attrs).forEach(([k,v])=>x.setAttribute(k,String(v)));return x};
function table(headings,rows){
 const t=el("table"),hd=el("thead"),body=el("tbody"),first=el("tr");
 headings.forEach(x=>first.append(el("th",x)));hd.append(first);
 rows.forEach(vals=>{const r=el("tr");vals.forEach(v=>r.append(el("td",v)));body.append(r)});
 t.append(hd,body);return t;
}
function valid(d){
 if(d.schema!=="jp.structural.g15.chapter05.signed_numerical_source_comparison.v0.1"||
 d.engineering_approval!==false||d.original_F3_one_way_shear!=="NOT SAFE IN ONE WAY SHEAR"||
 d.original_ETABS_model_authenticated!==false||d.authentic_modal_analysis_performed!==false||
 d.project_specific_NBC_compliance_evaluated!==false||
 d.counts?.source_gates_open!==15||d.counts?.signed_member_case_records!==825||
 d.member_case_end_actions?.length!==825||d.trial_node_displacements?.length!==345||
 d.case_summaries?.length!==5||
 d.original_report_claims?.modal_period_source_conflict_s?.resolved!==false||
 d.member_case_end_actions.some(x=>x.span_diagram_verified!==false))
 throw Error("Chapter 5 source/solver consistency or engineering HOLD verification failed");
}
function signedPairChart(container,title,values,unit){
 const frame=svg("svg",{viewBox:"0 0 440 150",role:"img",
 "aria-label":title+" signed OpenSees local end resisting actions in "+unit});
 frame.append(svg("line",{x1:40,x2:405,y1:80,y2:80,stroke:"#9bb3bd","stroke-width":1.5}));
 const max=Math.max(...values.map(v=>Math.abs(v)),0.000001),scale=42/max;
 values.forEach((v,i)=>{
  const center=120+i*190,height=Math.abs(v)*scale;
  frame.append(svg("rect",{x:center-34,y:v>=0?80-height:80,width:68,height,
   fill:v>=0?"#286b7e":"#bc705b",rx:3}));
  const label=svg("text",{x:center,y:130,"text-anchor":"middle","font-size":12,fill:"#385767"});
  label.textContent=(i===0?"i end":"j end")+" · "+fmt(v,4);frame.append(label);
 });
 const top=svg("text",{x:220,y:18,"text-anchor":"middle","font-size":13,fill:"#244957"});
 top.textContent=title+" ["+unit+"]";frame.append(top);
 container.append(frame);
}
function model(){
 fetch("data/g15-chapter05-signed-results.v0.1.json",{cache:"no-store"})
 .then(r=>r.ok?r.json():Promise.reject(Error("Missing signed Chapter 5 numerical ledger")))
 .then(d=>{
  valid(d);
  const casePicker=$("c05-case"),memberPicker=$("c05-member");
  const list=d.case_summaries.map(x=>x.id);
  casePicker.replaceChildren(...list.map(v=>{const x=el("option",v);x.value=v;return x}));
  const ids=[...new Set(d.member_case_end_actions.filter(x=>x.case_id===list[0]).map(x=>x.member_id))];
  memberPicker.replaceChildren(...ids.map(v=>{const x=el("option",v);x.value=v;return x}));
  const pairs=d.signed_pair_groups;
  const display=[["axial","Axial"],["shear_local_y","Local shear Vy"],["shear_local_z","Local shear Vz"],
   ["bending_local_y","Local bending My"],["bending_local_z","Local bending Mz"],["torsion","Torsion"]];
  function render(){
   const kind=casePicker.value,member=memberPicker.value;
   const a=d.member_case_end_actions.find(x=>x.case_id===kind&&x.member_id===member);
   const caseData=d.case_summaries.find(x=>x.id===kind);
   if(!a||!caseData)throw Error("Unknown member/case reference");
   const board=$("c05-member-diagram");board.replaceChildren();
   display.forEach(([key,title])=>{
    const box=el("div");box.className="rb-ch5-chart";
    signedPairChart(box,title,pairs[key].map(k=>a.local_components[k]),
     key.startsWith("axial")||key.startsWith("shear")?"kN":"kN·m");
    board.append(box);
   });
   $("c05-member-evidence").textContent="Actual OpenSeesPy · "+kind+" · "+member+
    " · 12 signed local element-end resisting actions. Separate i/j values are NOT a verified continuous-span axial/shear/moment diagram; original source member ID and project load map remain missing.";
   $("c05-case-extrema").replaceChildren(table(["Signed action","Extremal member / component","Value"],
     Object.entries(caseData.absolute_signed_end_action_extrema).map(([k,v])=>[
      k,v.member_id+" / "+v.component,fmt(v.signed_value,4)+" "+v.unit])));
   $("c05-case-equilibrium").textContent=kind+": OpenSees support reactions "+
    caseData.reactions_kN_xyz.map(x=>fmt(x,4)).join(" / ")+" kN; force residual "+
    fmt(caseData.force_residual_kN,8)+" kN; moment residual "+
    fmt(caseData.moment_residual_kNm,8)+" kN·m. This is trial-frame equilibrium, not source-model design acceptance.";
   renderDeflected(d,kind);
  }
  casePicker.addEventListener("change",render);
  memberPicker.addEventListener("change",render);
  const orig=d.original_observations,claim=d.original_report_claims;
  $("c05-seismic-compare").replaceChildren(table(["Original ETABS §5.1","Reported V (kN)","Source arithmetic V (kN)","Difference (kN)","Original building validity"],
    ["ULS","SLS"].map(limit=>{
     const c=claim.auto_seismic_arithmetic[limit];
     return [limit,fmt(c.printed_kN,4),fmt(c.recalculated_kN,7),fmt(c.difference_kN,7),"NOT authenticated"];
    })));
  $("c05-modal-source").replaceChildren(table(["Original report §5.5 source figure","Value","Source status"],
  [["First tabulated modal period",fmt(claim.modal_period_source_conflict_s.first_reported_table_s,3)+" s","SOURCE-REPORTED"],
   ["Neighboring narrative period",fmt(claim.modal_period_source_conflict_s.surrounding_narrative_s,3)+" s","CONFLICT"],
   ["First tabulated mode exceeding 90% UX",claim.modal_90_percent_first_table_mode.UX,"SOURCE-TABLE ARITHMETIC"],
   ["First tabulated mode exceeding 90% UY",claim.modal_90_percent_first_table_mode.UY,"SOURCE-TABLE ARITHMETIC"],
   ["First tabulated mode exceeding 90% RZ",claim.modal_90_percent_first_table_mode.RZ,"SOURCE-TABLE ARITHMETIC"]]));
  $("c05-claim-register").replaceChildren(table(["Original source (§5)","Printed source metric","What is actually accepted?"],
   [["5.6 ULS / SLS roof displacement",fmt(orig.reported_roof_displacements.ULS_max_mm,4)+
     " / "+fmt(orig.reported_roof_displacements.SLS_max_mm,6)+" mm","SOURCE-REPORTED, not revalidated"],
    ["5.7 ULS / SLS drift",fmt(orig.reported_drift.ULS_max_ratio,6)+" / "+
      fmt(orig.reported_drift.SLS_max_ratio,6),"SOURCE-REPORTED, not NBC accepted"],
    ["5.8 ULS torsion example",fmt(orig.reported_torsion.ULS_example_X_max_ratio,2)+" X; "+
      fmt(orig.reported_torsion.ULS_example_Y_max_ratio,2)+" Y","Source table only"],
    ["5.9 soft-storey stiffness",orig.reported_story_stiffness.X_kN_per_m.length+
      " printed X and Y storey entries","Unverified original mass/stiffness model"],
    ["5.10 mass irregularity",orig.reported_story_masses.reported.length+" mass values; original units absent",
      "Units unresolved"],
    ["5.12 ULS base reaction",fmt(orig.reported_base_reaction.ULS_X_kN,4)+" kN X",
      "Reported ETABS, not recovered model parity"],
    ["5.13 element section verification","Original figure, no native result export","No approved project-specific element design"],
    ["5.14 second base reaction","Original support reaction image","No authentic DL+LL support recovery"],
    ["5.15 mass and rigidity centres","Source D1/D2/D3 table","No verified rigidity centre or diaphragm"]]));
  render();
 }).catch(err=>{
  $("c05-member-diagram").replaceChildren(el("p","Signed evidence withheld: "+err.message));
 });
}
function renderDeflected(d,caseId){
 const p=$("c05-deformed"),rows=d.trial_node_displacements.filter(x=>x.case_id===caseId&&x.level===3);
 const img=svg("svg",{viewBox:"0 0 720 420",role:"img",
  "aria-label":"Source-derived roof plan, actual OpenSees horizontal displacement vectors exaggerated for visibility"});
 img.append(svg("rect",{x:0,y:0,width:720,height:420,fill:"#f6faf9",rx:8}));
 const scale=27,mag=14; // 14 displayed pixels per mm, purely graphical exaggeration
 for(const x of rows){
  const px=35+x.xy_m[0]*scale,py=385-x.xy_m[1]*25;
  const dx=x.ux_mm*mag,dy=-x.uy_mm*mag;
  img.append(svg("circle",{cx:px,cy:py,r:3,fill:"#416877"}));
  img.append(svg("line",{x1:px,y1:py,x2:px+dx,y2:py+dy,
   stroke:"#bd7154","stroke-width":1.9,"stroke-linecap":"round"}));
  img.append(svg("circle",{cx:px+dx,cy:py+dy,r:2.5,fill:"#bd7154"}));
 }
 const title=svg("text",{x:24,y:23,fill:"#2f5967","font-size":13});
 title.textContent="Level 3 · 23 nodal displacement vectors · graphical scale 14 px/mm (exaggerated)";
 img.append(title);p.replaceChildren(img);
 $("c05-displaced-caption").textContent=caseId+" · 23 actual OpenSees roof trial nodal UX/UY pairs (mm) from the provisional model; no authenticated diaphragm, deformed ETABS building or ULS/SLS drift approval.";
}
model();
})();