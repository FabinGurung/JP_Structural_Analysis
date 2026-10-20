/* Public Gate08: versioned REAL source-derived aggregates, no private FE geometry. */
(function(){
"use strict";
const $=s=>document.getElementById(s), el=(tag,value,cls)=>{const x=document.createElement(tag);if(value!==undefined)x.textContent=value;if(cls)x.className=cls;return x;};
const fmt=(n,d=2)=>typeof n==="number"&&Number.isFinite(n)?n.toLocaleString("en-US",{minimumFractionDigits:d,maximumFractionDigits:d}):"—";
const number=(n,d=2)=>fmt(n,d);
const selects=["gate08-state","gate08-metric","gate08-walls"];
let raw=null;
function kv(root,label,value){
 const row=el("div",undefined,"lab-meter-caption");row.append(el("span",label),el("strong",value));root.append(row);return row;
}
function showSummary(){
 const d=raw,m=d.mass_kN;
 $("gate08-source-state").replaceChildren(el("span","SOURCE-DERIVED / ENGINEERING HOLD","lab-status lab-status-warning"),
    el("span",d.scenario_description));
 $("gate08-kpis").replaceChildren(...[
  ["16","Variant models","ULS/SLS × diaphragm × footprint × walls"],
  ["816","New load cases","51 per model"],
  ["134,640","Signed vectors","Same-case member-end records"],
  [fmt(m.remaining_residual)+" kN","Unreconciled weight","After hypothetical wall trial"]
 ].map(([val,label,note])=>{const x=el("div",undefined,"lab-kpi");x.append(el("small",label),el("strong",val),el("span",note));return x;}));
 const feet=$("gate08-footprint-rows");feet.replaceChildren();
 for(const [name,area] of [
  ["Grid bounding rectangle",d.grid_bbox_area_m2],
  ["Column convex hull",d.column_convex_hull_area_m2],
  ["Source ground floor",d.source_floor_caption_m2[0]],
  ["Source first floor",d.source_floor_caption_m2[1]],
  ["Source upper/terrace caption",d.source_floor_caption_m2[2]]
 ]) kv(feet,name,fmt(area)+" m²");
 const masses=$("gate08-mass-rows");masses.replaceChildren();
 for(const [name,v] of [
 ["Source ETABS seismic W",m.source_ETABS_W],
 ["Without hypothesized walls",m.without_walls],
 ["With hypothesized walls",m.with_wall_hypothesis],
 ["Unreconciled residual",m.remaining_residual],
 ["Hypothetical residual after full hull walls",m.hypothetical_residual_after_full_perimeter_kN]
 ]) kv(masses,name,fmt(v)+" kN");
 masses.append(el("p","Equivalent still-unassigned: "+fmt(d.equivalent_missing_wall_length_per_level_m)+" m full wall per level across two levels; not a physical observation.","lab-chart-note"));
}
function draw(){
 if(!raw)return;
 const state=$("gate08-state").value,metric=$("gate08-metric").value,walls=$("gate08-walls").value;
 const all=raw.scenarios.filter(s=>s.limit_state===state&&(walls==="ALL"||String(s.wall)===walls));
 if(!all.length){$("gate08-chart").replaceChildren(el("p","No model variant with these constraints"));return;}
 const factor=metric==="drift_ratio"?100:1;
 const max=Math.max(...all.map(s=>s[metric]*factor),.01)*1.12;
 const chart=$("gate08-chart");chart.replaceChildren();
 for(const s of all){
  const label=(s.diaphragm==="FLEXIBLE"?"Flexible":"Rigid trial")+" / "+
       (s.footprint==="COLUMN_CONVEX_HULL"?"Hull":"Rectangle")+" / "+(s.wall?"walls":"no walls");
  const value=s[metric]*factor;
  const row=el("div",undefined,"lab-chart-line");
  const bar=el("div",undefined,"lab-chart-track");
  const fill=el("span",undefined,"lab-chart-fill "+(s.diaphragm==="FLEXIBLE"?"lab-chart-g06":"lab-chart-g07"));
  fill.style.width=(100*value/max).toFixed(2)+"%";bar.append(fill);
  const suffix=metric==="drift_ratio"?"%":metric==="roof_mm"?" mm":" kN·m";
  const labelValue=fmt(value,metric==="drift_ratio"?3:2)+suffix;
  row.append(el("span",label,"lab-chart-label"),bar,el("strong",labelValue));
  if(metric==="drift_ratio"&&s.numerical_drift_screen_exceeded){
    row.title="Numerical screen exceeds "+(state==="ULS"?"2.50":"0.60")+"%; not an as-built assessment";
  }
  chart.append(row);
 }
 const limit=state==="ULS"?2.5:.6;
 $("gate08-legend").textContent=
  (metric==="drift_ratio"?"Nominal "+state+" drift screen: "+fmt(limit)+"%. ":"")+
  "Same source report, competing floor-mass and diaphragm assumptions; plotted variation is not proof of compliant seismic design. Original F3 footing FAIL retained.";
}
function table(){
 const body=$("gate08-variant-rows");body.replaceChildren(...raw.scenarios.map(s=>{
  const tr=el("tr");
  for(const txt of [
    s.limit_state,
    s.diaphragm==="FLEXIBLE"?"Flexible frame":"Ideal rigid",
    s.footprint==="COLUMN_CONVEX_HULL"?"Convex hull":"Grid rectangle",
    s.wall?"Yes, assumed":"No",fmt(s.roof_mm)+" mm",
    fmt(100*s.drift_ratio,3)+"%",fmt(s.max_member_end_moment_kNm)+" kN·m"
  ])tr.append(el("td",txt));
  const check=el("td");check.append(el("span",s.numerical_drift_screen_exceeded?"EXCEEDS":"HOLD","lab-status "+(s.numerical_drift_screen_exceeded?"lab-status-warning":"lab-status-hold")));
  tr.append(check);return tr;
 }));
}
function validate(d){
 const m=d.mass_kN;
 if(d.schema!=="jp.structural.g15.gate08.public_source_reconciliation.v0.1"||
    d.public_view_only!==true||d.report_accepted!==false||d.engineering_approval!==false||
    d.f3_source_failure!=="NOT SAFE IN ONE WAY SHEAR"||
    d.seismic_mass_reconciled!==false||d.exact_slab_edges_verified!==false||
    d.grid_hull_used_as_slab_geometry!==false||
    d.cohort?.variants!==16||d.cohort?.solved_cases!==816||
    d.scenarios?.length!==16||m?.remaining_residual<=0||
    !d.scenarios.every(s=>s.design_approved===false&&
        s.numerical_drift_screen_exceeded===(s.drift_ratio>s.numerical_drift_screen_limit)))
   throw Error("Gate08 source integrity, scenario count or engineering-HOLD flags failed");
 return d;
}
for(const id of selects)$(id).addEventListener("change",draw);
fetch("data/g15-gate08-reconciliation.v0.1.json",{cache:"no-store"})
 .then(r=>r.ok?r.json():Promise.reject(Error("source projection unavailable")))
 .then(d=>{raw=validate(d);showSummary();draw();table();})
 .catch(err=>{$("gate08-source-state").replaceChildren(el("strong","Gate08 DATA HOLD: "+err.message));
    $("gate08-chart").replaceChildren(el("p","Evidence integrity is unresolved; no results displayed."));});
})();
