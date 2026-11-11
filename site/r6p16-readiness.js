/* R6.16 source-to-report readiness, explicitly NOT structural design acceptance. */
(()=>{"use strict";
const el=id=>document.getElementById(id);
const txt=(tag,value,cls)=>{const n=document.createElement(tag);if(value!==null&&value!==undefined)n.textContent=String(value);if(cls)n.className=cls;return n};
const pretty=x=>String(x).toLowerCase().replaceAll("_"," ").replace(/\b\w/g,m=>m.toUpperCase());
let state;
function addKpis(d){
 const r=d.reproduction,c=d.module_coverage_status_counts;
 const pairs=[
  ["Bounded OpenSees cases",r.Gate21_assumption_frame_solved_cases],
  ["Signed member-action records",r.Gate21_assumption_frame_member_end_action_rows],
  ["Original shell inputs",r.R610_original_source_shells],
  ["Research shells included",r.R610_source_shells_in_bounded_coarse_solver],
  ["Unsupported shells excluded",r.R610_source_shells_excluded],
  ["Source-edge checks",r.R615_original_edges_inspected],
  ["Partial modules",c.PARTIAL],
  ["Missing modules",c.MISSING]];
 const host=el("r616-kpis");host.replaceChildren();
 for(const [key,value] of pairs){
  const box=txt("div",null,"r616-kpi");
  box.append(txt("small",key),txt("strong",value));host.append(box);
 }
 const statuses=el("r616-statuses");statuses.replaceChildren();
 for(const [name,count] of Object.entries(c))
  statuses.append(txt("span",pretty(name)+" · "+count,"r616-status"));
}
function stageCards(d){
 const host=el("r616-stages");host.replaceChildren();
 for(const [i,stage] of d.reproducibility_stages.entries()){
  const card=txt("article",null,"r616-stage");
  card.append(txt("p","Stage "+(i+1)+" / "+d.reproducibility_stages.length,"r616-label"),
      txt("h3",stage.title),txt("code",stage.state),txt("p",stage.evidence),
      txt("div",stage.original_model_equivalence?"Original model equivalent":"Original ETABS21 equivalence NOT established","r616-gate"));
  host.append(card);
 }
}
function filteredModules(){
 const status=el("r616-module-status").value,priority=el("r616-module-priority").value,
 q=el("r616-module-query").value.trim().toUpperCase();
 return state.modules.filter(m=>
  (status==="ALL"||m.status===status)&&
  (priority==="ALL"||m.priority===priority)&&
  (!q||(m.id+" "+m.name+" "+m.remaining_scope).toUpperCase().includes(q)));
}
function cell(row,value){row.append(txt("td",value));}
function modules(){
 const rows=filteredModules(),host=el("r616-modules");host.replaceChildren();
 for(const item of rows){
  const tr=txt("tr");
  [item.id,item.name,pretty(item.status),item.priority,item.remaining_scope].forEach(x=>cell(tr,x));
  host.append(tr);
 }
 if(!rows.length){const tr=txt("tr"),td=txt("td","No modules match these filters");td.colSpan=5;tr.append(td);host.append(tr)}
 el("r616-filter-count").textContent=rows.length+" of "+state.module_count+" versioned report modules displayed. None is certified for this building.";
}
function blockers(d){
 const host=el("r616-blockers");host.replaceChildren();
 for(const entry of d.critical_gates){
  const card=txt("article",null,"r616-blocker");
  card.append(txt("small",entry.priority+" · "+entry.id),
   txt("h3",entry.title),txt("p",entry.missing),
   txt("small","Completion evidence required: "+entry.completion_evidence));
  host.append(card);
 }
}
function init(d){
 if(d?.schema!=="jp.structural.r6p16.report_engine_reproduction_readiness.v0.1"||
 d.module_count!==18||d.modules?.length!==18||d.reproducibility_stages?.length!==7||
 d.critical_gates?.length!==6||d.module_coverage_status_counts?.MISSING!==4||
 d.module_coverage_status_counts?.PARTIAL!==11||
 d.reproduction?.Gate21_assumption_frame_solved_cases!==5||
 d.reproduction?.R610_source_shells_excluded!==12||
 d.reproduction?.R615_original_edges_inspected!==308||
 d.reproduction?.engineering_approval!==false||
 d.reproduction?.full_governing_ETABS21_model_equivalent!==false||
 d.reproduction?.all_historical_report_results_recomputed!==false||
 d.F3_one_way_shear_unsafe!==true||d.twelve_unsupported_shells_excluded!==true||
 d.engineering_approval!==false||d.public_pages_are_not_live_gdrive_editors!==true)
   throw Error("Source-engine reproducibility statement or safety HOLD no longer matches");
 state=d;addKpis(d);stageCards(d);blockers(d);
 for(const id of ["r616-module-status","r616-module-priority","r616-module-query"])
   el(id).addEventListener(id==="r616-module-query"?"input":"change",modules);
 modules();
}
fetch("../../data/r6p16-report-reproducibility-readiness.json",{cache:"no-store"})
 .then(r=>r.ok?r.json():Promise.reject(Error("No generated R6.16 evidence JSON")))
 .then(init).catch(err=>{
   el("r616-kpis").textContent="Evidence unavailable: "+err.message;
   el("r616-stages").textContent="No building report reproducibility can be assumed.";
   el("r616-modules").replaceChildren();
 });
})();