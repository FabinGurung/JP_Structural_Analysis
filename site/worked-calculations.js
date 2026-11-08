/* R6.7 linked provisional member views and transparent quantity teaching estimator.
 * No current ETABS21 coordinates, results, approval, or reinforcement schedule is implied.
 */
(()=>{"use strict";
const by=id=>document.getElementById(id);
const ns="http://www.w3.org/2000/svg";
const fmt=(x,n=3)=>Number.isFinite(x)?x.toLocaleString("en-US",{minimumFractionDigits:n,maximumFractionDigits:n}):"—";
const make=(tag,attrs,txt)=>{
 const e=document.createElementNS(ns,tag);
 for(const [k,v] of Object.entries(attrs||{}))e.setAttribute(k,String(v));
 if(txt!==undefined)e.textContent=txt;
 return e;
};
const rx=(name)=>document.createElement(name);
let grid=null,level=1,selected="B:0";
const coords=new Map();
const beams=[];
const columns=[];
const max={x:21000,y:12530};
function plan(p){return [30+p[1]/max.x*530, 336-p[2]/max.y*298];}
function iso(p,z){const x=p[1]/1000,y=p[2]/1000,h=z/1000;
 return [190+(x*.9-y*.65)*14, 210+(x*.22+y*.5-h*1.1)*9];}
function line(svg,p1,p2,active,hypothetical,ref,view){
 const obj=make("line",{x1:p1[0],y1:p1[1],x2:p2[0],y2:p2[1],
  stroke:active?"#df4941":hypothetical?"#b68e8d":"#557c91",
  "stroke-width":active?5:hypothetical?2.4:1.8,
  "stroke-linecap":"round",opacity:active?1:.64,
  tabindex:"0",role:"button","aria-label":"Select provisional member "+ref,
  "data-ref":ref});
 const choose=()=>{selected=ref;by("worked-member").value=ref;render();};
 obj.addEventListener("click",choose);
 obj.addEventListener("keydown",ev=>{if(ev.key==="Enter"||ev.key===" "){ev.preventDefault();choose();}});
 if(active)svg.append(obj);
 else svg.insertBefore(obj,svg.firstChild);
}
function drawPlan(){
 const svg=by("worked-plan");svg.replaceChildren();
 svg.append(make("rect",{x:1,y:1,width:598,height:368,rx:10,fill:"#f7f9fc"}));
 for(let k=0;k<beams.length;k++){
  const o=beams[k],a=coords.get(o[0]),b=coords.get(o[1]);
  line(svg,plan(a),plan(b),selected==="B:"+k,k>=30,"B:"+k,"plan");
 }
 for(let k=0;k<columns.length;k++){
  const o=columns[k],p=plan(o);
  const active=selected==="C:"+k;
  const circle=make("circle",{cx:p[0],cy:p[1],r:active?7:4.4,
   fill:active?"#df4941":"#23485d",stroke:"#fff","stroke-width":"1.5",
   tabindex:"0",role:"button","aria-label":"Select provisional column "+o[0]});
  const choose=()=>{selected="C:"+k;by("worked-member").value=selected;render();};
  circle.addEventListener("click",choose);circle.addEventListener("keydown",e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();choose();}});
  svg.append(circle);
  const text=make("text",{x:p[0]+5,y:p[1]-6,fill:"#243f4e","font-size":"9"},o[0]);
  svg.append(text);
 }
 svg.append(make("text",{x:15,y:20,fill:"#667481","font-size":"12"},"Provisional centerline plan · NOT ETABS21 geometry"));
}
function draw3d(){
 const svg=by("worked-perspective");svg.replaceChildren();
 svg.append(make("rect",{x:1,y:1,width:598,height:368,rx:10,fill:"#f7f9fc"}));
 for(let lv=1;lv<=3;lv++){
  const z=lv*3048;
  for(let i=0;i<beams.length;i++){
   const o=beams[i],a=coords.get(o[0]),b=coords.get(o[1]);
   const focus=lv===level&&selected==="B:"+i;
   const item=make("line",{x1:iso(a,z)[0],y1:iso(a,z)[1],x2:iso(b,z)[0],y2:iso(b,z)[1],
      stroke:focus?"#df4941":i>=30?"#b68e8d":"#5e8eab",
      "stroke-width":focus?5:1.25,opacity:focus?1:.43,
      tabindex:"0",role:"button","aria-label":"Select beam "+o.join("–")+" on level "+lv});
   item.addEventListener("click",()=>{level=lv;selected="B:"+i;by("worked-level").value=lv;by("worked-member").value=selected;render();});
   item.addEventListener("keydown",e=>{if(e.key==="Enter"){level=lv;selected="B:"+i;by("worked-level").value=lv;by("worked-member").value=selected;render();}});
   svg.append(item);
  }
 }
 for(let i=0;i<columns.length;i++){
  const p=columns[i];
  for(let lv=1;lv<=3;lv++){
   const a=iso(p,(lv-1)*3048),b=iso(p,lv*3048),focus=lv===level&&selected==="C:"+i;
   const member=make("line",{x1:a[0],y1:a[1],x2:b[0],y2:b[1],
     stroke:focus?"#df4941":"#365a7c","stroke-width":focus?5:1.6,opacity:focus?1:.55,
     tabindex:"0",role:"button","aria-label":"Select column "+p[0]+" on level "+lv});
   member.addEventListener("click",()=>{level=lv;selected="C:"+i;by("worked-level").value=lv;by("worked-member").value=selected;render();});
   member.addEventListener("keydown",e=>{if(e.key==="Enter"){level=lv;selected="C:"+i;by("worked-level").value=lv;by("worked-member").value=selected;render();}});
   svg.append(member);
  }
 }
 svg.append(make("text",{x:14,y:20,fill:"#667481","font-size":"12"},"L"+level+" highlighted · provisional centerlines only"));
}
function selectedData(){
 if(selected[0]==="B"){
  const id=Number(selected.slice(2)),edge=beams[id],a=coords.get(edge[0]),b=coords.get(edge[1]);
  const length=Math.hypot(b[1]-a[1],b[2]-a[2]);
  return {label:"Beam "+edge.join("–")+" / L"+level,length_mm:length,
    width:304.8,depth:406.4,circular:false,kind:"beam",hypothetical:id>=30};
 }
 const idx=Number(selected.slice(2)),p=columns[idx],sec=grid.section_definitions_mm[p[3]];
 const circular=sec.shape==="circle";
 return {label:"Column "+p[0]+" / L"+(level-1)+"–L"+level,length_mm:3048,
   width:circular?sec.diameter:sec.width,depth:circular?sec.diameter:sec.depth,circular,
   kind:"column",hypothetical:false,section_id:p[3]};
}
function readNumber(id,low,high){
 const raw=by(id).value.trim();
 const n=Number(raw);
 if(raw===""||!Number.isFinite(n)||n<low||n>high)throw Error(id.replace("worked-","")+" must be "+low+"–"+high);
 return n;
}
function quantity(){
 if(!grid)return;
 const x=selectedData(),L=x.length_mm,b=x.width,h=x.depth;
 const vol=(x.circular?Math.PI*b*b/4:b*h)*L/1e9;
 const detail=by("worked-member-detail");
 detail.textContent=x.label+" · trial section "+fmt(b,1)+" × "+fmt(h,1)+" mm"+
   (x.circular?" (round section)":"")+", length "+fmt(L/1000,3)+" m"+
   ", gross concrete "+fmt(vol,5)+" m³."+
   (x.hypothetical?" HYPOTHETICAL connector — not actual.":"")+
   " Geometry from older public provisional grid; NOT mapped to governing ETABS21 member ID.";
 try{
  const count=readNumber("worked-nbars",1,40);
  const d=readNumber("worked-longdia",6,40);
  const ds=readNumber("worked-tiedia",6,16);
  const spacing=readNumber("worked-spacing",50,500);
  const cover=readNumber("worked-cover",10,100);
  const anch=readNumber("worked-anchorage",0,1500);
  if(cover*2+2*ds>=Math.min(b,h))throw Error("Cover / tie diameter exceeds section interior");
  if(L-2*cover<0)throw Error("Selected member too short for cover");
  const nTies=Math.ceil((L-2*cover)/spacing)+1;
  const bInner=b-2*cover,hInner=h-2*cover;
  const tieCut=x.circular?Math.PI*bInner+20*ds:2*(bInner+hInner)+20*ds;
  const longCut=L+2*anch;
  const longArea=Math.PI*d*d/4,tieArea=Math.PI*ds*ds/4;
  const longKg=count*longArea*longCut/1e9*7850;
  const tieKg=nTies*tieArea*tieCut/1e9*7850;
  const el=by("worked-quantity");
  el.replaceChildren();
  const items=[
    ["Gross concrete",fmt(vol,5)+" m³","Area × length; no joint deductions."],
    ["Longitudinal steel",fmt(longKg,3)+" kg",
      count+" × π×"+fmt(d,0)+"²/4 × ("+fmt(L,0)+" + 2×"+fmt(anch,0)+") × 7850 / 10⁹"],
    ["Stirrups / ties",fmt(nTies,0)+" pieces",
      "ceil[("+fmt(L,0)+"−2×"+fmt(cover,0)+")/"+fmt(spacing,0)+"] + 1"],
    ["Approx. tie cut length",fmt(tieCut,1)+" mm",
      x.circular?"π("+fmt(b,1)+"−2×"+fmt(cover,0)+") + 20×"+fmt(ds,0):
        "2[("+fmt(b,1)+"−2×"+fmt(cover,0)+")+("+fmt(h,1)+"−2×"+fmt(cover,0)+")] + 20×"+fmt(ds,0)],
    ["Tie steel weight",fmt(tieKg,3)+" kg",fmt(nTies,0)+" × π×"+fmt(ds,0)+"²/4 × "+fmt(tieCut,1)+" × 7850 / 10⁹"],
    ["Total demonstration steel",fmt(longKg+tieKg,3)+" kg",
      "Illustrative inputs and simplistic hooks only; NOT source-scheduled reinforcement."]
  ];
  for(const [title,num,explain] of items){
   const card=rx("div");card.className="quantity-card";
   const h3=rx("strong");h3.textContent=title;
   const result=rx("b");result.textContent=num;
   const p=rx("small");p.textContent=explain;
   card.append(h3,result,p);el.append(card);
  }
 }catch(err){
  by("worked-quantity").textContent="Cannot calculate illustrative quantity: "+err.message;
 }
}
function render(){if(!grid)return;drawPlan();draw3d();quantity();}
function init(d){
 if(d.schema!=="jp.structural.g15.public_working_grid.v0.1"||
 d.status!=="SOURCE_DERIVED_HYPOTHETICAL_FRAME_NOT_VERIFIED_AS_BUILT"||
 d.safety.engineering_approval!==false||d.safety.F3_footing_one_way_shear!=="NOT SAFE IN ONE WAY SHEAR"||
 d.column_positions_mm?.length!==23||d.beam_edges?.length!==32||d.hypothetical_beam_edge_indices?.join(",")!=="30,31")
 throw Error("Provisional model changed, reconciliation required");
 grid=d;
 for(const p of d.column_positions_mm){coords.set(p[0],p);columns.push(p);}
 for(const e of d.beam_edges){if(!coords.has(e[0])||!coords.has(e[1]))throw Error("Invalid beam reference");beams.push(e);}
 const sel=by("worked-member");
 for(let i=0;i<beams.length;i++){
  const item=rx("option");item.value="B:"+i;
  item.textContent="Beam "+beams[i].join("–")+(i>=30?" [hypothetical]":"");
  sel.append(item);
 }
 for(let i=0;i<columns.length;i++){
  const item=rx("option");item.value="C:"+i;item.textContent="Column "+columns[i][0];sel.append(item);
 }
 sel.value=selected;
 const u=new URL(window.location.href);
 const requested=u.searchParams.get("member");
 if(requested&&Array.from(sel.options).some(o=>o.value===requested)){selected=requested;sel.value=requested;}
 by("worked-level").addEventListener("change",()=>{level=Number(by("worked-level").value);render();});
 sel.addEventListener("change",()=>{selected=sel.value;render();});
 const cycle=d=>{const options=Array.from(sel.options);const idx=options.findIndex(o=>o.value===selected);
  selected=options[(idx+d+options.length)%options.length].value;sel.value=selected;render();};
 by("worked-prev").addEventListener("click",()=>cycle(-1));
 by("worked-next").addEventListener("click",()=>cycle(1));
 for(const id of ["worked-nbars","worked-longdia","worked-tiedia","worked-spacing","worked-cover","worked-anchorage"]){
   by(id).addEventListener("input",quantity);
 }
 render();
}
fetch("data/g15-working-grid.public.v0.1.json",{cache:"no-store"}).then(r=>{
 if(!r.ok)throw Error("Geometry source unavailable");
 return r.json();
}).then(init).catch(err=>{
 by("worked-member-detail").textContent="Model viewer unavailable: "+err.message+". The hand-calculation chapters remain readable.";
 by("worked-quantity").textContent="Quantity preview requires verified public provisional geometry.";
});
})();
