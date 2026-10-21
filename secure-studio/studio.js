(() => {
"use strict";
const $ = id => document.getElementById(id);
const fmt = n => typeof n==="number" && Number.isFinite(n) ? n.toFixed(3) : "—";
const tableRow = values => {
  const tr=document.createElement("tr");
  for(const v of values){const td=document.createElement("td");td.textContent=String(v);tr.append(td);}
  return tr;
};
let key="",result=null;
async function call(path,options={}){
 if(!key) throw new Error("Authentication required");
 const resp=await fetch(path,{...options,headers:{Authorization:"Bearer "+key,"Content-Type":"application/json"},cache:"no-store"});
 const data=await resp.json();
 if(!resp.ok)throw new Error(String(data.detail||"Request denied"));
 return data;
}
$("connect").addEventListener("click",async()=>{
 key=$("key").value.trim();$("key").value="";
 $("auth-state").textContent="Checking model…";
 try{
 const d=await call("/api/status");
 if(d.members!==165||d.columns!==23||d.engineering_approval!==false)throw new Error("Unexpected model");
 $("auth-state").textContent="Authenticated: 165 model elements, 23 column grid positions; still a hypothesis.";
 $("solve").disabled=false;
 }catch(err){$("auth-state").textContent="Authentication/source unavailable: "+err.message;key="";$("solve").disabled=true;}
});
$("solve").addEventListener("click",async()=>{
 const request={
  beam_width_mm:Number($("width").value),
  concrete_E_MPa:Number($("elastic").value),
  stiffness_state:$("stiff").value,
  diaphragm:$("diaphragm").value,
  footprint_proxy:$("footprint").value,
  wall_proxy:$("walls").value==="true",
  bridges:$("bridges").value==="true"
 };
 if(!(request.beam_width_mm>=200&&request.beam_width_mm<=600&&
      request.concrete_E_MPa>=10000&&request.concrete_E_MPa<=50000)){
  $("work-state").textContent="Outside accepted engineering input bounds";return;
 }
 $("solve").disabled=true;$("download").disabled=true;
 $("work-state").textContent="Executing 51 private 3D frame load cases…";
 try{
  const d=await call("/api/analyze",{method:"POST",body:JSON.stringify(request)});
  if(d.engineering_approval!==false||d.model_counts?.members!==165||
     d.F3_source_failure!=="NOT SAFE IN ONE WAY SHEAR")throw new Error("Source QA HOLD");
  result=d;$("download").disabled=false;
  $("work-state").textContent="Solved "+d.case_count+" cases. Engineering acceptance remains HOLD.";
  const metrics=[
    ["Frame elements",d.model_counts.members],
    ["Load cases",d.case_count],
    ["Unreconciled seismic mass",fmt(d.report_mass_kN-d.modeled_mass_kN)+" kN"],
    ["Maximum roof displacement",fmt(Math.max(...d.case_results.map(x=>x.max_roof_lateral_displacement_mm)))+" mm"]
  ];
  $("metrics").replaceChildren(...metrics.map(([k,v])=>{
   const a=document.createElement("article"),b=document.createElement("strong"),s=document.createElement("small");
   s.textContent=k;b.textContent=String(v);a.append(s,b);return a;
  }));
  $("cases").replaceChildren(...d.case_results.map(x=>tableRow([
    x.case,fmt(x.max_roof_lateral_displacement_mm),
    fmt(100*x.max_storey_lateral_chord_rotation_dimensionless)+"%",
    fmt(x.max_global_equilibrium_residual)])));
  $("member").replaceChildren(...d.signed_member_actions.map((x,i)=>{
   const option=document.createElement("option");option.value=String(i);option.textContent=x.member_id;return option;
  }));
  $("member").disabled=false;showMember();
 }catch(e){$("work-state").textContent="Calculation HOLD: "+e.message;}
 finally{$("solve").disabled=false;}
});
function showMember(){
 if(!result)return;
 const m=result.signed_member_actions[Number($("member").value)];
 if(!m)return;
 $("forces").replaceChildren(...Object.entries(m.signed_local_end_forces).map(([k,v])=>
  tableRow([k,fmt(v),k.startsWith("N")||k.startsWith("V")?"kN":"kN·m"])));
}
$("member").addEventListener("change",showMember);
$("download").addEventListener("click",()=>{
 if(!result)return;
 const blob=new Blob([JSON.stringify(result,null,2)],{type:"application/json"});
 const url=URL.createObjectURL(blob),a=document.createElement("a");
 a.href=url;a.download="private-g15-3d-signed-analysis.json";a.click();URL.revokeObjectURL(url);
});
})();