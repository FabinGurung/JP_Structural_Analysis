/* De-identified real-source G+1.5 calculation journal, no private file access. */
(function(){
"use strict";
const $=id=>document.getElementById(id);
const create=(tag,text,cls)=>{const x=document.createElement(tag);if(text!==undefined)x.textContent=text;if(cls)x.className=cls;return x;};
const num=(v,n=2)=>Number.isFinite(v)?Number(v).toLocaleString("en-US",{maximumFractionDigits:n,minimumFractionDigits:n}):"—";
const pct=v=>num(v*100,2)+"%";
const rows=(table,contents)=>table.replaceChildren(...contents);
let data=null,stage="G07",filter="ALL",view="roof";
const stagesById={};
function badge(status){return create("span",status.replaceAll("_"," "),"lab-status lab-status-"+status.toLowerCase());}
function renderSummary(){
 const m=data.gravity_mass;
 const values=[
  ["Solved FE cases",data.derived.total_gate05_gate06_gate07_case_solves.toLocaleString(),"G05–G07 trial scenarios"],
  ["Working elements",String(data.scope.member_count),"source-derived hypothetical frame"],
  ["Current mass gap",num(data.derived.conditional_gate07_mass_shortfall_pct,1)+"%","after conditional wall study"],
  ["Unresolved source FAIL","1","F3 one-way shear"]
 ];
 const root=$("lab-kpis");
 root.replaceChildren(...values.map(([label,value,caption])=>{
  const x=create("div",undefined,"lab-kpi");
  x.append(create("small",label),create("strong",value),create("span",caption));return x;
 }));
 $("lab-state").replaceChildren(badge("PROVISIONAL"),create("span",data.source_qualification));
}
function selectStage(id){
 stage=id;const x=stagesById[id];if(!x)return;
 document.querySelectorAll(".lab-gate").forEach(b=>{const yes=b.dataset.gate===id;b.setAttribute("aria-pressed",String(yes));});
 const target=$("lab-selected");
 const top=create("div",undefined,"lab-selected-top");top.append(create("span",x.id+" / "+x.subtitle,"eyebrow"),badge(x.status));
 target.replaceChildren(top,create("h3",x.title),create("p",x.summary));
 const note=id==="G07"?"Latest study: grid-weighted floor loads, candidate exterior wall lines and flexible/rigid diaphragm bounds. No verified diaphragm polygons.":
   id==="G06"?"Results: 153 individual FE solves, ±5% accidental eccentricity, three elastic stiffness variants and signed same-case member actions.":
   id==="G05"?"Mass and ESM loads are anchored to report coefficients, not independently validated site hazard or soil profiles.":
   id==="G04"?"TF C24 steel schedule choice remains conditional and source footing F3 one-way shear remains explicitly unsafe.":
   "The source is private. We preserve the distinction between extracted drawing statements and hypothesized model geometry.";
 target.append(create("p",note,"lab-stage-note"));
}
function renderStages(){
 Object.assign(stagesById,Object.fromEntries(data.workflow.map(x=>[x.id,x])));
 $("lab-timeline").replaceChildren(...data.workflow.map(x=>{
  const b=create("button",undefined,"lab-gate");b.type="button";b.dataset.gate=x.id;
  b.append(create("small",x.id),create("strong",x.title),badge(x.status));
  b.addEventListener("click",()=>selectStage(x.id));return b;
 }));
 selectStage(stage);
}
function bar(label,value,maxVal,cls){
 const outer=create("div",undefined,"lab-meter-wrap");
 const head=create("div",undefined,"lab-meter-caption");
 head.append(create("span",label),create("strong",num(value)+" kN"));
 const track=create("div",undefined,"lab-meter-track");
 const inside=create("span",undefined,"lab-meter-fill "+cls);inside.style.width=(100*value/maxVal).toFixed(3)+"%";
 track.append(inside);outer.append(head,track);return outer;
}
function renderMass(){
 const m=data.gravity_mass,root=$("lab-mass-graphic"),limit=m.report_W_kN;
 root.replaceChildren(
  bar("Report ETABS seismic weight",m.report_W_kN,limit,"lab-ref"),
  bar("Gate06 reconstructed",m.gate06_reconstructed_kN,limit,"lab-prev"),
  bar("Gate07 conditional with walls",m.gate07_conditionally_reconstructed_kN,limit,"lab-new"));
 const components=[
  ["Member dead load",m.member_selfweight_kN],
  ["Area-based floor dead",m.floor_added_dead_kN],
  ["Seismic share of live",m.seismic_live_share_kN],
  ["Candidate wall edges · two floors",m.wall_trial_added_weight_kN],
  ["Still unexplained",m.gate07_remaining_gap_kN],
  ["ETABS reference total",m.report_W_kN]
 ];
 rows($("lab-mass-rows"),components.map(([k,v])=>{
  const r=create("tr");r.append(create("td",k),create("td",num(v)));return r;
 }));
 $("lab-mass-note").textContent=
  "Earlier gap "+num(m.gate06_gap_kN)+" kN; this trial allocates "+num(m.wall_trial_added_weight_kN)+
  " kN to "+m.wall_proxy_length_per_level_m+" m of candidate line walls at two levels. "+num(m.gate07_remaining_gap_kN)+
  " kN remains. Source wall placement is not verified and the added weight has not independently recalibrated ESM inertia.";
}
function renderResponse(){
 const elements=[
  ...data.gate06.stiffness.map(x=>({label:"G06 "+x.id,state:x.id,roof_mm:x.roof_mm,kind:"G06",drift:null})),
  ...data.gate07.variants.map(x=>({label:"G07 "+x.id,state:x.state,roof_mm:x.roof_mm,drift:x.drift,kind:"G07"}))
 ];
 const isDrift=view==="drift";
 const visible=isDrift?[
  ...data.gate06.eccentric_scenarios.filter(x=>(x.axis==="X"&&x.sign==="NEG")||(x.axis==="Y"&&x.sign==="POS"))
    .map(x=>({label:"G06 "+x.state+" "+x.axis+" / "+x.sign,value:x.design_drift*100,kind:"G06"})),
  ...data.gate07.variants.map(x=>({label:"G07 "+x.id,value:x.drift*100,kind:"G07"}))
 ]:elements.map(x=>({label:x.label,value:x.roof_mm,kind:x.kind}));
 const max=Math.max(...visible.map(x=>x.value),1)*1.12;
 const chart=$("lab-response-chart");
 chart.replaceChildren(...visible.map(q=>{
  const line=create("div",undefined,"lab-chart-line");
  const left=create("span",q.label,"lab-chart-label");
  const track=create("div",undefined,"lab-chart-track");
  const fill=create("span",undefined,"lab-chart-fill "+(q.kind==="G07"?"lab-chart-g07":"lab-chart-g06"));
  fill.style.width=(100*q.value/max).toFixed(2)+"%";
  track.append(fill);
  line.append(left,track,create("strong",num(q.value,isDrift?3:2)+(isDrift?"%":" mm")));
  return line;
 }));
 $("lab-response-note").textContent=isDrift?
  "ULS numerical screening limit = 2.50%; SLS = 0.60%; design drift depends on assumed source model and Rμ scaling. The report does not establish a compliant diaphragm.":
  "These roof movements are different assumed load-path/stiffness models, not multiple measurements of the same built structure. A rigid diaphragm can appear more favorable without being physically justified.";
}
function renderTables(){
 const values=data.gate06.eccentric_scenarios.map(x=>({stage:"G06",name:x.state+" / "+x.axis+" / ECC "+x.sign,roof:x.roof_mm,drift:x.design_drift,limit:x.numerical_limit,over:x.screening_exceeds_limit}))
  .concat(data.gate07.variants.map(x=>({stage:"G07",name:x.id,roof:x.roof_mm,drift:x.drift,limit:x.numerical_limit,over:x.screening_exceeds_limit})));
 rows($("lab-response-rows"),values.map(x=>{
  const row=create("tr");for(const text of [x.stage,x.name,num(x.roof)+" mm",pct(x.drift),pct(x.limit)]){
    row.append(create("td",text));
  }
  const result=create("td");result.append(badge(x.over?"WARNING":"HOLD"));row.append(result);return row;
 }));
}
function renderModules(){
 const source=data.calculation_families;
 const matches=source.filter(m=>filter==="ALL"||
   (filter==="WARNING"&&(m.status==="WARNING"||m.status==="FAIL_SOURCE"))||
   (filter==="OPEN"&&(m.status==="OPEN"||m.status==="HOLD"||m.status==="ASSUMED"||m.status==="PROVISIONAL"||m.status==="PARTIAL")));
 $("lab-modules").replaceChildren(...matches.map(m=>{
  const x=create("article",undefined,"lab-module panel");
  const head=create("div",undefined,"lab-module-head");head.append(create("span",m.id,"eyebrow"),badge(m.status));
  const title=create("h3",m.title);
  x.append(head,title,create("p",m.note),create("small",m.provenance));
  const link=create("button","See "+m.ref+" gate →","lab-inline-button");link.type="button";
  link.addEventListener("click",()=>{selectStage(m.ref);$("lab-journey").scrollIntoView({behavior:"smooth",block:"start"});});
  x.append(link);
  return x;
 }));
 document.querySelectorAll(".lab-filter").forEach(b=>b.setAttribute("aria-pressed",String(b.dataset.statusFilter===filter)));
}
function renderFindings(){
 const facts=[
  ["SOURCE FAIL · NOT DISMISSED","F3 one-way shear",data.member_checks.F3_source_status+". Footing remains unresolved; no valid redesign is claimed.","lab-fail"],
  ["NUMERIC WARNING · NOT AN AS-BUILT FAILURE","Flexible-frame drift","Gate06 and Gate07 assumed flexible-frame drift screens exceed provisional NBC limits in some cases. Rigid diaphragm trials differ materially; actual slab stiffness and connectivity are unverified.","lab-warn"],
  ["SOURCE RECONCILIATION OPEN","Seismic weight","Remaining "+num(data.gravity_mass.gate07_remaining_gap_kN)+" kN mass gap after conditional wall hypothesis. Real wall mapping, true floor polygons and mass-source definitions required.","lab-warn"],
  ["ENGINEERING HOLD","C24 longitudinal reinforcement",data.member_checks.C24_reinforcement_candidate+" was selected for testing; actual member/grid foreign key and bar anchorage not verified.","lab-hold"],
  ["ENGINEERING HOLD","Seismic site and signed model","True Vs30 hazard, diaphragm and torsion force path, ETABS parity, modal combinations, P-Delta and final independent acceptance remain open.","lab-hold"]
 ];
 $("lab-findings").replaceChildren(...facts.map(([status,title,detail,cls])=>{
   const x=create("article",undefined,"lab-finding panel "+cls);x.append(create("small",status),create("h3",title),create("p",detail));return x;
 }));
}
function verify(d){
 if(!d||d.schema!=="jp.structural.deidentified.project_calculation_ledger.public.v0.1"||
    d.source_visibility!=="PRIVATE_DRIVE_SOURCE_NOT_PUBLISHED"||
    d.publication!=="USER_REQUESTED_DEIDENTIFIED_AGGREGATE_ONLY"||
    d.safety?.actual_building_approved!==false||
    d.gravity_mass?.mass_reconciled!==false||
    d.member_checks?.F3_source_status!=="NOT SAFE IN ONE WAY SHEAR"||
    d.derived?.professional_design_approved!==false||
    d.workflow?.length!==6||d.gate07?.variants?.length!==4)
    throw Error("Journal integrity / approval-HOLD check failed");
 return d;
}
$("lab-view-select").addEventListener("change",e=>{view=e.target.value;renderResponse();});
document.querySelectorAll(".lab-filter").forEach(x=>x.addEventListener("click",()=>{filter=x.dataset.statusFilter;renderModules();}));
fetch("data/g15-project-ledger.v0.1.json",{cache:"no-store"})
.then(r=>r.ok?r.json():Promise.reject(Error("project ledger unavailable")))
.then(d=>{
 data=verify(d);renderSummary();renderStages();renderMass();renderResponse();renderTables();renderModules();renderFindings();
}).catch(error=>{
 $("lab-state").replaceChildren(create("strong","PROJECT EVIDENCE HOLD: "+error.message));
 $("lab-modules").replaceChildren(create("p","Unable to validate the public projection; no calculation claims shown."));
});
})();
