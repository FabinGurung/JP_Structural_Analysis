/* Public-only, deterministic NBC105:2025 ESM preview. No tokens, storage or private data. */
(function(){
"use strict";
const f=document.getElementById("studio-form");
if(!f)return;
const $=id=>document.getElementById(id);
const el=(tag,text,css)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(css)n.className=css;return n;};
const fmt=(x,dp=2)=>Number.isFinite(x)?x.toLocaleString("en-US",{minimumFractionDigits:dp,maximumFractionDigits:dp}):"—";
const MINMAX={
 span_m:[2,15],storey_height_m:[2.4,4.5],period_s:[.1,3],
 elastic_site_C:[.01,2],Rmu:[1,6],overstrength:[1,2.5],
 beam_width_m:[.2,.6],beam_depth_m:[.3,.9],column_width_m:[.25,.9],column_depth_m:[.25,.9],
 Ec_MPa:[10000,50000],beam_EI_factor:[.1,1],column_EI_factor:[.1,1],
};
let active=null;
const start=Object.fromEntries([...f.querySelectorAll("input")].map(n=>[n.name,n.value]));
function read(){
 const n={schema:"jp.structural.portal.frame.v1",model:"SYNTHETIC_FRAME_ONLY"};
 for(const [name,[lo,hi]] of Object.entries(MINMAX)){
  const field=f.elements.namedItem(name);
  const value=Number(field.value);
  if(field.value.trim()===""||!Number.isFinite(value)||value<lo||value>hi)
    throw Error(name+" must be between "+lo+" and "+hi);
  n[name]=value;
 }
 n.floor_weights_kN=[1,2,3].map(i=>{
   const field=f.elements.namedItem("floor_"+i);
   const x=Number(field.value);
   if(field.value.trim()===""||!Number.isFinite(x)||x<20||x>10000)
     throw Error("Floor "+i+" weight must be 20–10000 kN");
   return x;
 });
 return n;
}
function calculate(d){
 const k=d.period_s<=.5?1:d.period_s>=2.5?2:1+(d.period_s-.5)/2;
 const W=d.floor_weights_kN.reduce((a,b)=>a+b,0);
 const Cd=d.elastic_site_C/(d.Rmu*d.overstrength);
 const V=Cd*W;
 const heights=[1,2,3].map(i=>d.storey_height_m*i);
 const weights=d.floor_weights_kN.map((w,i)=>w*heights[i]**k);
 const sum=weights.reduce((a,b)=>a+b,0);
 const floors=weights.map(x=>x/sum*V);
 if(![k,W,Cd,V,...floors].every(Number.isFinite)||Math.abs(floors.reduce((a,b)=>a+b,0)-V)>1e-7)
   throw Error("ESM equilibrium failed");
 return {k,W,Cd,V,heights,floors};
}
const svgNS="http://www.w3.org/2000/svg";
function s(name,attrs,text){
 const node=document.createElementNS(svgNS,name);
 for(const [k,v] of Object.entries(attrs))node.setAttribute(k,String(v));
 if(text!==undefined)node.textContent=String(text);
 return node;
}
function drawFrame(d,out){
 const svg=$("studio-frame");svg.replaceChildren();
 svg.append(s("rect",{x:6,y:5,width:468,height:368,rx:12,fill:"transparent"}));
 const x0=82,x1=350,y0=335,dy=86,scale=2.7/d.span_m;
 for(let i=0;i<=3;i++){
  const y=y0-dy*i;
  if(i>0)svg.append(s("line",{x1:x0,y1:y,x2:x1,y2:y,stroke:"#2c9b92","stroke-width":5,"stroke-linecap":"round"}));
  if(i<3)for(const x of [x0,x1]){
    svg.append(s("line",{x1:x,y1:y-dy,x2:x,y2:y,stroke:"#7199b6","stroke-width":5,"stroke-linecap":"round"}));
  }
  for(const x of [x0,x1]){
    svg.append(s("circle",{cx:x,cy:y,r:5,fill:"#1c806f"}));
    if(i===0)svg.append(s("path",{d:"M"+(x-17)+" "+(y+9)+"h34M"+(x-13)+" "+(y+12)+"l-5 7",stroke:"#7a8ea2","stroke-width":2,fill:"none"}));
  }
  if(i>0){
    const fx=out.floors[i-1],yArrow=y-23;
    svg.append(s("line",{x1:365,y1:yArrow,x2:405,y2:yArrow,stroke:"#b87d46","stroke-width":3}));
    svg.append(s("path",{d:"M405 "+yArrow+"l-9 -6v12z",fill:"#b87d46"}));
    svg.append(s("text",{x:360,y:yArrow-8,fill:"currentColor","font-size":12},fmt(fx,1)+" kN"));
    svg.append(s("text",{x:22,y:y-9,fill:"currentColor","font-size":12},"L"+i));
  }
 }
 svg.append(s("text",{x:145,y:368,fill:"currentColor","font-size":12},"Span "+fmt(d.span_m,1)+" m"));
 svg.append(s("text",{x:12,y:18,fill:"currentColor","font-size":11},"3-level elastic frame · schematic"));
}
function render(d,out){
 const values=[
 ["ULS base shear",fmt(out.V)+" kN"],["Seismic weight",fmt(out.W)+" kN"],
 ["ULS coefficient Cᵈ",fmt(out.Cd,5)],["Distribution exponent k",fmt(out.k,3)]
 ];
 $("studio-kpis").replaceChildren(...values.map(([label,value])=>{
   const box=el("div",undefined,"lab-kpi");
   box.append(el("small",label),el("strong",value));return box;
 }));
 $("studio-force-bars").replaceChildren(...out.floors.map((force,i)=>{
   const row=el("div",undefined,"lab-meter-wrap"),head=el("div",undefined,"lab-meter-caption");
   head.append(el("span","Floor "+(i+1)),el("strong",fmt(force)+" kN"));
   const track=el("div",undefined,"lab-meter-track"),fill=el("span",undefined,"lab-meter-fill");
   fill.style.width=(100*force/Math.max(...out.floors)).toFixed(2)+"%";
   track.append(fill);row.append(head,track);return row;
 }));
 $("studio-floor-table").replaceChildren(...out.floors.map((force,i)=>{
   const tr=el("tr");for(const val of [String(i+1),fmt(out.heights[i],2),fmt(d.floor_weights_kN[i],1),fmt(force)])
   tr.append(el("td",val));return tr;
 }));
 drawFrame(d,out);
 $("studio-error").textContent="Numerical ESM preview recalculated. Global lateral force equilibrium: PASS · Full FE not yet run.";
 $("studio-error").classList.add("studio-good");
}
function update(){
 try{
   const d=read(),calc=calculate(d);
   active=d;render(d,calc);
   $("studio-queue").disabled=false;
   $("studio-export").disabled=false;
   $("studio-queue-note").textContent="Ready: synthetic numeric inputs only. The prepared GitHub issue is public; no private building details are included.";
 }catch(e){
  active=null;
  $("studio-error").textContent="Correct the input: "+e.message;
  $("studio-error").classList.remove("studio-good");
  $("studio-queue").disabled=true;$("studio-export").disabled=true;
  $("studio-queue-note").textContent="Inputs invalid; GitHub FE submission disabled.";
 }
}
f.addEventListener("input",update);
$("studio-reset").addEventListener("click",()=>{
 for(const field of f.querySelectorAll("input"))field.value=start[field.name];
 update();f.scrollIntoView({behavior:"smooth",block:"start"});
});
function issueUrl(){
 const json=JSON.stringify(active);
 if(json.length>1400)throw Error("Scenario too large");
 const title="[JP Frame MVP] synthetic OpenSees 3-level frame";
 const body="JP_FRAME_RUN_V1\n"+json+"\n\nOnly synthetic public numerical inputs. Submit this issue to start the owner-authorized OpenSees GitHub Action. No private building files or client data.";
 return "https://github.com/FabinGurung/JP_Structural_Analysis/issues/new?title="+encodeURIComponent(title)+"&body="+encodeURIComponent(body);
}
$("studio-queue").addEventListener("click",()=>{
 if(!active)return;
 const url=issueUrl();
 const win=window.open(url,"_blank","noopener,noreferrer");
 if(!win)window.location.href=url;
 $("studio-queue-note").textContent="GitHub issue page opened. You must submit it while signed into the owning GitHub account; afterwards open the Actions run or issue comment for the OpenSees JSON artifact.";
});
$("studio-export").addEventListener("click",()=>{
 if(!active)return;
 const blob=new Blob([JSON.stringify(active,null,2)+"\n"],{type:"application/json"});
 const u=URL.createObjectURL(blob);
 const link=el("a");link.href=u;link.download="jp_synthetic_frame_scenario.v1.json";
 document.body.append(link);link.click();link.remove();URL.revokeObjectURL(u);
});
update();
})();
