(()=>{"use strict";
const $=x=>document.getElementById(x),txt=(x,t)=>{$(x).textContent=t},fmt=(n,k=3)=>Number.isFinite(n)?n.toLocaleString("en-US",{maximumFractionDigits:k}):"—";
let token="",result=null;
function row(values){const tr=document.createElement("tr");for(const value of values){const td=document.createElement("td");td.textContent=String(value);tr.append(td)}return tr;}
async function api(path,opts={}){
 if(!token)throw Error("Session credential required");
 const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),120000);
 try{
 const res=await fetch(path,{...opts,headers:{"Authorization":"Bearer "+token,"Content-Type":"application/json"},cache:"no-store",signal:controller.signal});
 const body=await res.json();if(!res.ok)throw Error(body.detail||"Server rejected request");
 return body;
 }finally{clearTimeout(timer)}
}
$("connect").addEventListener("click",async()=>{
 token=$("key").value.trim();$("key").value="";
 if(!token){txt("auth-state","Enter an access credential.");return;}
 txt("auth-state","Checking private source integrity…");
 try{const d=await api("/api/status");if(d.members!==165||d.columns!==23||d.engineering_approval!==false)throw Error("Model integrity failed");
 txt("auth-state","Authorized · "+d.members+" members · "+d.columns+" column grid points · Working hypothesis only");$("solve").disabled=false;
 }catch(e){token="";$("solve").disabled=true;txt("auth-state","Authentication/model check failed: "+e.message);}
});
$("solve").addEventListener("click",async()=>{
 const req={beam_width_mm:Number($("width").value),concrete_E_MPa:Number($("elastic").value),stiffness_state:$("stiff").value,diaphragm:$("diaphragm").value,wall_proxy:$("walls").value==="true",footprint_proxy:$("footprint").value,bridges:$("bridges").value==="true"};
 if(!Number.isFinite(req.beam_width_mm)||req.beam_width_mm<200||req.beam_width_mm>600||
   !Number.isFinite(req.concrete_E_MPa)||req.concrete_E_MPa<10000||req.concrete_E_MPa>50000){txt("work-state","Invalid geometry/material inputs.");return;}
 $("solve").disabled=true;$("download").disabled=true;txt("work-state","Solving full private working frame server-side…");
 try{
  const d=await api("/api/analyze",{method:"POST",body:JSON.stringify(req)});
  if(d.engineering_approval!==false||d.model_counts?.members!==165||d.F3_source_failure!=="NOT SAFE IN ONE WAY SHEAR")throw Error("Missing engineering HOLD");
  result=d;$("download").disabled=false;txt("work-state","Solved "+d.case_count+" linear-elastic cases. NOT an approved building design.");
  const max=Math.max(...d.case_results.map(x=>x.max_roof_lateral_displacement_mm));
  const delta=d.report_mass_kN-d.modeled_mass_kN;
  $("metrics").replaceChildren(...[["Frame members","165"],["Signed cases",String(d.case_count)],["Mass gap",fmt(delta,2)+" kN"],["Maximum roof movement",fmt(max,2)+" mm"]].map(([l,v])=>{const a=document.createElement("article"),s=document.createElement("small"),b=document.createElement("strong");s.textContent=l;b.textContent=v;a.append(s,b);return a;}));
  $("cases").replaceChildren(...d.case_results.map(x=>row([x.case,fmt(x.max_roof_lateral_displacement_mm),fmt(x.max_storey_lateral_chord_rotation_dimensionless*100)+"%",fmt(x.max_global_equilibrium_residual,7)])));
  const all=d.signed_member_actions;
  $("member").replaceChildren(...all.map((a,i)=>{const o=document.createElement("option");o.value=String(i);o.textContent=a.member_id;return o;}));$("member").disabled=false;displayMember();
 }catch(e){txt("work-state","Numerical analysis HOLD: "+e.message);}finally{$("solve").disabled=false;}
});
function displayMember(){
 if(!result)return;const a=result.signed_member_actions[Number($("member").value)];
 if(!a)return;
 const vals=Object.entries(a.signed_local_end_forces||{}).map(([k,v])=>[k,fmt(v,6),k.startsWith("N")||k.startsWith("V")?"kN":"kN·m"]);
 $("forces").replaceChildren(...vals.map(row));
}
$("member").addEventListener("change",displayMember);
$("download").addEventListener("click",()=>{
 if(!result)return;const url=URL.createObjectURL(new Blob([JSON.stringify(result,null,2)],{type:"application/json"}));
 const a=document.createElement("a");a.href=url;a.download="G15_working_3D_analysis_PRIVATE.json";a.click();URL.revokeObjectURL(url);
});
})();