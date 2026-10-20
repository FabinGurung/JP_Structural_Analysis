/* Local-only FE detail reader. No fetch, upload, storage or telemetry in this file.
   Works on the private Gate06 complete JSON extracted from its ZIP. */
(function(){
"use strict";
const $=id=>document.getElementById(id);
const input=$("lab-private-files"),cases=$("lab-private-case"),members=$("lab-private-member");
if(!input||!cases||!members)return;
const status=$("lab-private-status"),details=$("lab-private-case-detail"),forceBody=$("lab-private-forces");
const make=(tag,txt,cls)=>{const e=document.createElement(tag);if(txt!==undefined)e.textContent=txt;if(cls)e.className=cls;return e;};
const fmt=x=>typeof x==="number"&&Number.isFinite(x)?x.toLocaleString("en-US",{minimumFractionDigits:3,maximumFractionDigits:5}):"—";
const unit=k=>/^[NV]/.test(k)?"kN":"kN·m";
let registry=[],selected=null;
function clear(){cases.replaceChildren(make("option","No cases loaded"));members.replaceChildren(make("option","Choose a case"));cases.disabled=true;members.disabled=true;details.replaceChildren();forceBody.replaceChildren();registry=[];selected=null;}
function chosen(){
 const index=Number(cases.value);
 return Number.isInteger(index)&&index>=0&&index<registry.length?registry[index]:null;
}
function renderMember(){
 const row=selected?.rows?.find(x=>x.member_id===members.value);
 forceBody.replaceChildren();
 if(!row){details.append(make("p","No source member selected."));return;}
 const vector=row.signed_local_end_forces;
 if(!vector||typeof vector!=="object"){status.textContent="Member vector missing; local output cannot be inspected.";return;}
 const ordered=["Ni","Vyi","Vzi","Ti","Myi","Mzi","Nj","Vyj","Vzj","Tj","Myj","Mzj"];
 for(const k of ordered){
  const v=vector[k];if(typeof v!=="number"||!Number.isFinite(v)){status.textContent="Malformed local signed force vector; result held.";return;}
  const tr=make("tr");tr.append(make("td",k),make("td",fmt(v)),make("td",unit(k)));forceBody.append(tr);
 }
}
function renderCase(){
 selected=chosen();forceBody.replaceChildren();details.replaceChildren();
 if(!selected){members.disabled=true;return;}
 const r=selected.caseResult,rows=selected.rows;
 if(!r||!rows.length){status.textContent="Selected case has no solver results or signed member vectors.";return;}
 const list=Array.from(new Set(rows.map(x=>x.member_id))).sort();
 members.replaceChildren(...list.map(id=>{const x=make("option",id);x.value=id;return x;}));
 members.disabled=false;
 const capsule=make("div",undefined,"lab-private-values");
 for(const [label,v,unitLabel] of [
  ["Maximum roof movement",r.max_roof_lateral_displacement_mm,"mm"],
  ["Maximum chord ratio",r.max_storey_lateral_chord_rotation_dimensionless,"ratio"],
  ["Force/moment equilibrium residual",r.max_global_equilibrium_residual,"mixed kN/kNm"],
  ["Signed member vectors",rows.length,"records"]
 ]){const item=make("div",undefined,"lab-private-value");item.append(make("small",label),make("strong",fmt(v)),make("span",unitLabel));capsule.append(item);}
 const notice=make("p","Exact case: "+selected.key+". The 12 signed components below belong to the SAME selected case and member; do not combine unrelated maximum component values.","lab-chart-note");
 details.replaceChildren(capsule,notice);
 renderMember();
}
input.addEventListener("change",async()=>{
 clear();const files=Array.from(input.files||[]);
 if(!files.length){status.textContent="No private file selected.";return;}
 if(files.length>8||files.some(f=>f.size>32*1024*1024)){
  status.textContent="Maximum 8 files, 32 MiB per file, to keep in-browser inspection bounded.";return;
 }
 status.textContent="Reading "+files.length+" locally selected JSON file(s) in this tab…";
 let accepted=0,skipped=[];
 for(const file of files){
  try{
   const d=JSON.parse(await file.text());
   // Gate08 is a full-analysis PRIVATE local file, same signed-member vectors
   // as Gate06, but the FE data are at document root and never uploaded.
   const gate08=d.source_report_sha256===
      "f122904444a2e2f75230d9d4e41da0093d050da25c6e8140c86d466b7e37cc52" &&
      d.trial_ESM_mass_basis==="RECONSTRUCTED_COMPONENTS" &&
      d.variant && ["FLEXIBLE","RIGID_TRIAL"].includes(d.variant.diaphragm);
   const frame=gate08?d:d.frame;
   const approvedInput=gate08?
      (frame.case_results?.length===51&&frame.element_actions?.length===8415&&
       frame.variant.hypothetical_diagonal_bridges_retained===true):
      (d.engineering_approval===false&&d.real_source_verified===false);
   if(!frame||!approvedInput||
     !Array.isArray(frame.case_results)||!Array.isArray(frame.element_actions)||
     frame.case_results.length<1){
     skipped.push(file.name+": unsupported or missing engineering HOLD");continue;
   }
   const actionMap=new Map();
   for(const row of frame.element_actions){
     if(!row||typeof row.case!=="string"||typeof row.member_id!=="string")continue;
     if(!actionMap.has(row.case))actionMap.set(row.case,[]);
     actionMap.get(row.case).push(row);
   }
   for(const row of frame.case_results){
     if(!row||typeof row.case!=="string"||!actionMap.has(row.case))continue;
     registry.push({key:file.name+" · "+row.case,caseResult:row,rows:actionMap.get(row.case)});
   }
   accepted++;
  }catch(e){skipped.push(file.name+": invalid JSON");}
 }
 if(!registry.length){status.textContent="No compatible full-analysis JSON found. "+skipped.join(" | ");return;}
 cases.replaceChildren(...registry.map((r,i)=>{const x=make("option",r.key);x.value=String(i);return x;}));
 cases.disabled=false;
 status.textContent="Loaded "+accepted+" local Gate06/Gate08 private dataset(s), "+registry.length+
   " same-case solver records. Nothing transmitted or saved to the site."+
   (skipped.length?" Skipped: "+skipped.join(" | "):"");
 renderCase();
});
cases.addEventListener("change",renderCase);
members.addEventListener("change",renderMember);
})();
