/* Public actual-source 3D working-frame editor; no login needed for viewing. */
(()=>{
"use strict";
const $=id=>document.getElementById(id),ns="http://www.w3.org/2000/svg";
const fmt=(x,d=2)=>Number.isFinite(x)?x.toLocaleString("en-US",{maximumFractionDigits:d,minimumFractionDigits:d}):"—";
const node=(name,attrs,txt)=>{const v=document.createElementNS(ns,name);for(const [k,val] of Object.entries(attrs))v.setAttribute(k,String(val));if(txt!==undefined)v.textContent=txt;return v;};
const make=(name,txt,klass)=>{const v=document.createElement(name);if(txt!==undefined)v.textContent=txt;if(klass)v.className=klass;return v;};
const refs=["g15-beam","g15-e","g15-stiff","g15-w1","g15-w2","g15-w3","g15-c","g15-t","g15-bridges"];
const defaults=Object.fromEntries(refs.map(id=>[id,$(id).type==="checkbox"?$(id).checked:$(id).value]));
let model=null,yaw=-.67,beamVisible=true,request=null;
function bounds(v,name,lo,hi){
 const x=Number(v);
 if(String(v).trim()===""||!Number.isFinite(x)||x<lo||x>hi)throw Error(name+" must be "+lo+"–"+hi);
 return x;
}
function read(){
 return {schema:"jp.structural.g15.open3d.request.v1",
 beam_width_mm:bounds($("g15-beam").value,"Beam width",200,650),
 concrete_E_MPa:bounds($("g15-e").value,"Ec",10000,50000),
 stiffness:$("g15-stiff").value,
 bridges:$("g15-bridges").checked,
 floor_weights_kN:[
  bounds($("g15-w1").value,"Floor 1 weight",20,10000),
  bounds($("g15-w2").value,"Floor 2 weight",20,10000),
  bounds($("g15-w3").value,"Floor 3 weight",20,10000)],
 C_design:bounds($("g15-c").value,"Cd",.01,.5),
 T_seconds:bounds($("g15-t").value,"T",.1,3)};
}
function project(x,y,z){
 const xr=x*Math.cos(yaw)-y*Math.sin(yaw),depth=x*Math.sin(yaw)+y*Math.cos(yaw);
 return [275+xr*19, 320+depth*8-z*26];
}
function segment(scene,a,b,color,width,label){
 const [x1,y1]=project(...a),[x2,y2]=project(...b);
 const l=node("line",{x1,y1,x2,y2,stroke:color,"stroke-width":width,
                       "stroke-linecap":"round","data-member":label,tabindex:0});
 const choose=()=>$("g15-inspector").textContent=label+" · assumed elastic element centerline · source grid-based connectivity, not confirmed as-built.";
 l.addEventListener("click",choose);l.addEventListener("keydown",e=>{if(e.key==="Enter")choose();});
 scene.append(l);
}
function render(){
 if(!model)return;
 const c=model.column_positions_mm,
 sections=Object.fromEntries(c.map(x=>[x[0],x])),
 edgeList=model.beam_edges,stage=$("g15-scene");
 stage.replaceChildren();
 // Background is conceptual, not an architectural slab boundary.
 stage.append(node("text",{x:12,y:24,fill:"currentColor","font-size":13},
  "23 column grids · 3 levels · Source-derived 3D frame"));
 for(const p of c){
  const xyz=[p[1]/1000,p[2]/1000];
  for(let level=0;level<3;level++){
   segment(stage,[...xyz,3.048*level],[...xyz,3.048*(level+1)],
        "#80bed2",3,"COLUMN "+p[0]+" @ L"+level+"–L"+(level+1));
  }
 }
 if(beamVisible){
  edgeList.forEach((e,i)=>{
   if(i>=30&&!$("g15-bridges").checked)return;
   const a=sections[e[0]],b=sections[e[1]];
   for(let level=1;level<=3;level++){
    segment(stage,[a[1]/1000,a[2]/1000,3.048*level],
     [b[1]/1000,b[2]/1000,3.048*level],
     i>=30?"#dc8256":"#47bb9e",i>=30?4:2.2,
     "BEAM "+e[0]+"–"+e[1]+" / L"+level+(i>=30?" / HYPOTHETICAL CONNECTOR":""));
   }
  });
 }
 for(const p of c){
  const [x,y]=project(p[1]/1000,p[2]/1000,9.144);
  stage.append(node("circle",{cx:x,cy:y,r:3.3,fill:"#e5e9f3"}));
  stage.append(node("text",{x:x+5,y:y-6,fill:"currentColor","font-size":10},p[0]));
 }
 const mem=69+( $("g15-bridges").checked?96:90);
 $("g15-model-numbers").textContent="92 nodes · "+mem+" members · 69 columns · "+(mem-69)+" inferred beams · 23 column grid marks · 4 elevation planes";
}
function compute(){
 try{
 const d=read();
 if(!model)throw Error("Public model not loaded");
 if(!["ULS","SLS","GROSS"].includes(d.stiffness))throw Error("Bad stiffness option");
 const W=d.floor_weights_kN.reduce((s,x)=>s+x,0);
 const k=d.T_seconds<=.5?1:d.T_seconds>=2.5?2:1+(d.T_seconds-.5)/2;
 const h=[3.048,6.096,9.144],fact=d.floor_weights_kN.map((w,i)=>w*h[i]**k);
 const sum=fact.reduce((a,b)=>a+b,0),V=d.C_design*W;
 const fi=fact.map(x=>V*x/sum);
 if(Math.abs(fi.reduce((a,b)=>a+b,0)-V)>1e-7)throw Error("Force equilibrium failure");
 request=d;
 const cells=[["Seismic weight",fmt(W)+" kN"],["Base shear",fmt(V)+" kN"],
   ["Exponent k",fmt(k,3)],["Model elements",String(69+(d.bridges?96:90))]];
 $("g15-preview").replaceChildren(...cells.map(([key,val])=>{const box=make("div",undefined,"lab-kpi");box.append(make("small",key),make("strong",val));return box;}));
 $("g15-forces").replaceChildren(...fi.map((x,i)=>{const tr=make("tr");for(const v of [i+1,fmt(d.floor_weights_kN[i]),fmt(h[i],3),fmt(x)])tr.append(make("td",v));return tr;}));
 $("g15-equilibrium").textContent="NBC 105:2025 §6.3: Fi = V Wi hi^k / Σ Wj hj^k. ΣFi = "+fmt(fi.reduce((a,b)=>a+b,0))+" kN. PASS (arithmetic only). No verified code-site coefficient or diaphragm.";
 $("g15-status").textContent="Inputs valid. Press Queue to submit authenticated 3D OpenSees analysis on GitHub; public model and source code require no Vercel.";
 $("g15-queue").disabled=false;$("g15-export").disabled=false;
 render();
 }catch(e){request=null;$("g15-queue").disabled=true;$("g15-export").disabled=true;
 $("g15-status").textContent="Cannot run: "+e.message;}
}
$("g15-turn-left").addEventListener("click",()=>{yaw-=Math.PI/8;render();});
$("g15-turn-right").addEventListener("click",()=>{yaw+=Math.PI/8;render();});
$("g15-fit").addEventListener("click",()=>{yaw=-.67;render();});
$("g15-toggle-beams").addEventListener("click",()=>{
 beamVisible=!beamVisible;$("g15-toggle-beams").textContent=beamVisible?"Hide beams":"Show beams";render();
});
$("g15-point").addEventListener("change",()=>{
 const c=model?.column_positions_mm.find(v=>v[0]===$("g15-point").value);
 if(c)$("g15-inspector").textContent=c[0]+": x="+fmt(c[1]/1000,3)+" m, y="+fmt(c[2]/1000,3)+" m; scheduled type "+c[3]+"; node exists on levels 0–3.";
});
for(const id of refs){$(id).addEventListener("input",compute);$(id).addEventListener("change",compute);}
$("g15-reset").addEventListener("click",()=>{for(const id of refs){$(id).type==="checkbox"?$(id).checked=defaults[id]:$(id).value=defaults[id];}compute();});
$("g15-export").addEventListener("click",()=>{
 if(!request)return;
 const u=URL.createObjectURL(new Blob([JSON.stringify(request,null,2)+"\n"],{type:"application/json"}));
 const a=make("a");a.href=u;a.download="G15_3D_open_source_scenario.v1.json";a.click();URL.revokeObjectURL(u);
});
$("g15-queue").addEventListener("click",()=>{
 if(!request)return;
 const cfg=JSON.stringify(request);
 if(cfg.length>1200)throw Error("Oversized source-safe numeric request");
 const title="[JP G15 3D] source-derived 3D OpenSees trial";
 const body="JP_G15_3D_RUN_V1\n"+cfg+"\n\nPublic 165-member source-derived working hypothesis. An authorized repository contributor must submit this GitHub issue to run Actions. Not a construction approval.";
 const url="https://github.com/FabinGurung/JP_Structural_Analysis/issues/new?title="+encodeURIComponent(title)+"&body="+encodeURIComponent(body);
 window.open(url,"_blank","noopener,noreferrer");
 $("g15-status").textContent="Prefilled GitHub issue opened. Submit it when signed into the repo owner account; GitHub Actions will post a link to the signed FE results.";
});
let solved=null,baselineSolved=null,resultOrigin="Published baseline";
function validResult(d){
 const count=d?.model_counts?.members;
 if(d?.schema!=="jp.structural.g15.open3d.result.v1"||
   ![159,165].includes(count)||d?.model_counts?.nodes!==92||
   d?.cases?.length!==5||d?.engineering_approval!==false||
   d?.report_accepted!==false||
   d?.foundation_F3_one_way_shear!=="NOT SAFE IN ONE WAY SHEAR")return false;
 const cases=["GRAVITY","EQ_PLUS_X","EQ_MINUS_X","EQ_PLUS_Y","EQ_MINUS_Y"];
 return d.cases.every((c,i)=>
  c.case===cases[i] && c.member_signed_local_end_forces?.length===count &&
  Number.isFinite(c.max_roof_horizontal_displacement_mm) &&
  Number.isFinite(c.equilibrium_residual_kN) && c.equilibrium_residual_kN<.001 &&
  Number.isFinite(c.equilibrium_moment_residual_kNm) && c.equilibrium_moment_residual_kNm<.001 &&
  c.roof_displacement_metric==="MAX_NODE_HORIZONTAL_EUCLIDEAN_NORM" &&
  c.member_signed_local_end_forces.every(m=>m.local_components?.length===12&&
    m.signed?.length===12&&m.signed.every(Number.isFinite)));
}
function renderReference(){
 if(!solved)return;
 const current=solved.cases[Number($("g15-solved-case").value)||0];
 if(!current)return;
 const elArr=current.member_signed_local_end_forces;
 $("g15-solved-member").replaceChildren(...elArr.map((a,i)=>{
   const o=make("option",a.id);o.value=String(i);return o;
 }));
 $("g15-solved-member").disabled=false;
 $("g15-solved-summary").replaceChildren(...[
   ["Load case",current.case],["Max roof movement",fmt(current.max_roof_horizontal_displacement_mm,3)+" mm"],
   ["Signed member ends",String(elArr.length)],["Force residual",fmt(current.equilibrium_residual_kN,7)+" kN"]
 ].map(([key,v])=>{const box=make("div",undefined,"lab-kpi");box.append(make("small",key),make("strong",v));return box;}));
 renderLocalForces();
}
function renderLocalForces(){
 if(!solved)return;
 const c=solved.cases[Number($("g15-solved-case").value)||0];
 const m=c?.member_signed_local_end_forces[Number($("g15-solved-member").value)||0];
 if(!m)return;
 $("g15-member-components").replaceChildren(...m.local_components.map((k,i)=>{
  const tr=make("tr");tr.append(make("td",k),make("td",fmt(m.signed[i],5)),
    make("td",k.startsWith("N")||k.startsWith("V")?"kN":"kN·m"));
  return tr;
 }));
 $("g15-solved-message").textContent=resultOrigin+" · "+m.id+" in "+c.case+
 ". 12 signed end actions from one OpenSees case; force residual "+fmt(c.equilibrium_residual_kN,7)+
 " kN, moment residual "+fmt(c.equilibrium_moment_residual_kNm,7)+
 " kN·m. F3 source FAIL retained. Engineering approval HOLD.";
}
$("g15-solved-case").addEventListener("change",renderReference);
$("g15-solved-member").addEventListener("change",renderLocalForces);

$("g15-load-result").addEventListener("change",async()=>{
 const file=$("g15-load-result").files?.[0];
 if(!file)return;
 try{
  if(file.size<100||file.size>20000000)throw Error("Select extracted results.json (max 20 MB), not the Actions ZIP");
  const d=JSON.parse(await file.text());
  if(!validResult(d))throw Error("Results require five complete signed OpenSees cases, source counts, 3D vector drift and full force/moment equilibrium; older artifacts must be rerun");
  solved=d;resultOrigin="Local result: "+file.name;
  $("g15-solved-case").replaceChildren(...d.cases.map((c,i)=>{const o=make("option",c.case);o.value=String(i);return o;}));
  $("g15-solved-case").disabled=false;renderReference();
 }catch(e){$("g15-solved-message").textContent="Local result rejected: "+e.message;}
 finally{$("g15-load-result").value="";}
});
$("g15-restore-reference").addEventListener("click",()=>{
 if(!baselineSolved){$("g15-solved-message").textContent="Baseline not loaded yet.";return;}
 solved=baselineSolved;resultOrigin="Published baseline";renderReference();
});
fetch("data/g15-open3d-reference.v1.json",{cache:"no-store"})
.then(r=>r.ok?r.json():Promise.reject(Error("Baseline OpenSees result unavailable")))
.then(d=>{
 if(!validResult(d))throw Error("Baseline source/counts/HOLD or force/moment equilibrium invalid");
 baselineSolved=d;solved=d;resultOrigin="Published baseline";
 $("g15-solved-case").replaceChildren(...d.cases.map((c,i)=>{
  const o=make("option",c.case);o.value=String(i);return o;
 }));
 $("g15-solved-case").disabled=false;renderReference();
}).catch(e=>$("g15-solved-message").textContent="OpenSees baseline HOLD: "+e.message);
fetch("data/g15-working-grid.public.v0.1.json",{cache:"no-store"}).then(x=>x.ok?x.json():Promise.reject(Error("model JSON unavailable"))).then(d=>{
 if(d.schema!=="jp.structural.g15.public_working_grid.v0.1"||
 d.column_positions_mm?.length!==23||d.beam_edges?.length!==32||
 d.safety?.engineering_approval!==false||
 d.safety?.F3_footing_one_way_shear!=="NOT SAFE IN ONE WAY SHEAR")
 throw Error("Model integrity or required engineering HOLD failed");
 model=d;$("g15-point").replaceChildren(...d.column_positions_mm.map(c=>{const o=make("option",c[0]);o.value=c[0];return o;}));
 $("g15-point").dispatchEvent(new Event("change"));compute();
}).catch(e=>$("g15-status").textContent="Model source unavailable: "+e.message);
})();
