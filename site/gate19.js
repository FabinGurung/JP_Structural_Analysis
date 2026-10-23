/* Original ETABS model is PRIVATE: selected E2K is read only inside browser.
   Static readiness JSON is the ONLY network request. */
(function(){
"use strict";
function triage(text,name){
 const o={status:"REJECT",complete:false,units:"UNKNOWN",stories:0,points:0,
   lines:0,areas:0,lineAssignments:0,areaAssignments:0,massSource:false,
   sourceIdentityVerified:false,engineeringApproval:false};
 if(!name.toLowerCase().endsWith(".e2k")||typeof text!=="string"||!text)return o;
 let section="";
 for(const raw of text.split(/\r?\n/)){
   const t=raw.trim();
   if(t.startsWith("$")){section=t.slice(1).trim();if(section==="END OF MODEL FILE")o.complete=true;continue}
   if(section==="CONTROLS"&&/^UNITS /.test(t)) {
     const m=t.match(/^UNITS\s+"([^"]+)"\s+"([^"]+)"/);if(m)o.units=m[1]+"/"+m[2];
   }
   if(section==="STORIES - IN SEQUENCE FROM TOP"&&/^STORY /.test(t))o.stories++;
   if(section==="POINT COORDINATES"&&/^POINT /.test(t))o.points++;
   if(section==="LINE CONNECTIVITIES"&&/^LINE /.test(t))o.lines++;
   if(section==="AREA CONNECTIVITIES"&&/^AREA /.test(t))o.areas++;
   if(section==="LINE ASSIGNS"&&/^LINEASSIGN /.test(t))o.lineAssignments++;
   if(section==="AREA ASSIGNS"&&/^AREAASSIGN /.test(t))o.areaAssignments++;
   if(section==="MASS SOURCE"&&/^MASSSOURCE /.test(t))o.massSource=true;
 }
 const other=/narayani|rambazzar|nabin|saugat|sabitri/i.test(name);
 if(!other&&o.complete&&o.units==="N/MM"&&o.stories>=4&&o.points>0&&
    o.lines>0&&o.areas>0&&o.lineAssignments>0&&o.areaAssignments>0&&o.massSource)
  o.status="LOCAL_SHAPE_CANDIDATE_IDENTITY_HOLD";
 return o;
}
if(typeof module!=="undefined"&&module.exports)module.exports={triage};
if(typeof document==="undefined")return;
const el=id=>document.getElementById(id);
if(!el("g19-status"))return;
fetch("data/g15-gate19-e2k-readiness.v0.1.json",{cache:"no-store"})
.then(r=>r.ok?r.json():Promise.reject(Error("Readiness missing")))
.then(d=>{
 if(d.schema!=="jp.structural.g15.gate19.e2k_source_intake.v0.1"||
    d.source_model_admitted!==false||d.physical_mass_reconciled!==false||
    d.status!=="BLOCKED_ORIGINAL_ETABS_MODEL_NOT_FOUND"||
    d.f3_source_status!=="NOT SAFE IN ONE WAY SHEAR")throw Error("Engineering gate violated");
 el("g19-status").textContent="Original ETABS source file missing. Local E2K triage is ready; NO engineering source admitted.";
}).catch(e=>{el("g19-status").textContent="Gate19 withheld: "+e.message});
el("g19-file").addEventListener("change",async function(){
 const f=this.files&&this.files[0];if(!f)return;
 const out=el("g19-local");
 if(f.size>40*1024*1024||!f.name.toLowerCase().endsWith(".e2k")){
 out.textContent="Rejected: select a local E2K no larger than 40MB";return;}
 try{
 const d=triage(await f.text(),f.name);
 out.textContent="Local triage: "+d.status+
 ". Stories: "+d.stories+"; points: "+d.points+"; lines: "+d.lines+
 "; areas: "+d.areas+"; mass-source section: "+d.massSource+
 ". Project identity, model mass inputs, F3 and approval remain on HOLD. No file uploaded.";
 }catch(_){out.textContent="Local file read failed. No file uploaded."}
});
})();
