/* Chapter 3 is a read-only projection of a *real* OpenSees model solve with explicit safety holds. */
(()=>{"use strict";
const $=x=>document.getElementById(x);
if(!$("c03-stage-table"))return;
const td=x=>{const q=document.createElement("td");q.textContent=String(x);return q};
const fmt=(x,n=4)=>Number.isFinite(x)?x.toLocaleString("en-US",{minimumFractionDigits:n,maximumFractionDigits:n}):"—";
function table(headers,rows){
 const out=document.createElement("table"),h=document.createElement("thead"),b=document.createElement("tbody"),row=document.createElement("tr");
 headers.forEach(x=>{const t=document.createElement("th");t.textContent=x;row.append(t)});
 h.append(row);
 rows.forEach(vals=>{const tr=document.createElement("tr");vals.forEach(v=>tr.append(td(v)));b.append(tr)});
 out.append(h,b);return out;
}
function fail(s){
 for(const id of ["c03-programs","c03-member-schedule","c03-stage-table","c03-solver-metrics","c03-solved-cases"]){
  const e=$(id);if(!e)continue;const p=document.createElement("p");p.textContent="NUMERICAL EVIDENCE WITHHELD: "+s;
  p.style.color="#963e36";e.replaceChildren(p);
 }
}
fetch("data/g15-chapter03-method.v0.1.json",{cache:"no-store"})
.then(r=>{if(!r.ok)throw Error("Chapter 3 machine ledger missing");return r.json()})
.then(d=>{
 const s=d.real_OpenSees_numerical_snapshot;
 if(d.schema!=="jp.structural.g15.chapter03.method_execution.v0.1"||
 d.engineering_approval!==false||d.original_native_ETABS_model_authenticated!==false||
 d.source_floor_loads_and_mass_authenticated!==false||d.actual_structural_member_design_completed!==false||
 d.original_F3_one_way_shear!=="NOT SAFE IN ONE WAY SHEAR"||
 d.source_gates_open!==15||d.accepted_engineering_method_stages!==0||
 d.stages?.length!==12||d.original_programs?.length!==4||d.original_member_schedule?.length!==8||
 s.nodes!==92||s.members!==165||s.case_count!==5||s.signed_member_end_action_records!==825||
 s.signed_local_components_per_record!==12||
 s.max_equilibrium_force_residual_kN>=.001||s.max_equilibrium_moment_residual_kNm>=.001||
 d.stages.some(x=>x.physical_building_accepted!==false)||
 !Number.isFinite(s.max_abs_member_bending_kNm)||!Number.isFinite(s.max_roof_displacement_mm_provisional))
 throw Error("Method authenticity, numerical equilibrium, stage list or engineering safety conditions failed");
 $("c03-programs").replaceChildren(table(["Original reported task","Original program","Admitted status"],
   d.original_programs.map(x=>[x.function,x.program,"SOURCE-REPORTED · editable original unavailable"])));
 $("c03-member-schedule").replaceChildren(table(["Original structural element","Printed size / dimension","Reported grade","Verified project section?"],
   d.original_member_schedule.map(x=>[x.member,x.reported_size,x.concrete,x.source_status])));
 $("c03-stage-table").replaceChildren(table(["ID · Method","Original task","Our Python execution","Current state","Evidence needed for acceptance"],
   d.stages.map(x=>[x.id+" · "+x.title,x.reported,x.engine+"\n"+x.source_code.join(", "),x.state,x.acceptance])));
 const mv=[
  ["Analysis nodes",s.nodes],["Provisional members",s.members],["Real OpenSees cases",s.case_count],
  ["Signed action records",s.signed_member_end_action_records],
  ["Largest force equilibrium residual",fmt(s.max_equilibrium_force_residual_kN,6)+" kN"],
  ["Largest moment equilibrium residual",fmt(s.max_equilibrium_moment_residual_kNm,6)+" kN·m"],
  ["Largest provisional roof displacement",fmt(s.max_roof_displacement_mm_provisional,5)+" mm"],
  ["Largest signed axial magnitude",fmt(s.max_abs_member_axial_kN,4)+" kN"],
  ["Largest signed bending magnitude",fmt(s.max_abs_member_bending_kNm,4)+" kN·m"]];
 $("c03-solver-metrics").replaceChildren(...mv.map(([label,value])=>{
  const box=document.createElement("div"),strong=document.createElement("strong"),small=document.createElement("small");
  box.className="rb-ch3-metric";strong.textContent=value;small.textContent=label;box.append(strong,small);return box;
 }));
 $("c03-solved-cases").replaceChildren(table(["Actual OpenSees case","Numerical status","Physical building approval"],
   s.case_labels.map(x=>[x,"SOLVED · force and moment equilibrium within 0.001", "NO · provisional frame"])));
}).catch(e=>fail(e.message));
})();
