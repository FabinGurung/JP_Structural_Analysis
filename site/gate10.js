/* Gate10: research assumptions only — no verified structural approvals. */
(()=>{
"use strict";
const $=id=>document.getElementById(id);
if(!$("g10-head"))return;
const fmt=x=>Number.isFinite(x)?x.toLocaleString("en-US",{maximumFractionDigits:2}):"—";
const el=(name,value,klass)=>{const e=document.createElement(name);if(value!==undefined)e.textContent=String(value);if(klass)e.className=klass;return e;};
const SVG="http://www.w3.org/2000/svg";
const shape=(kind,props)=>{const e=document.createElementNS(SVG,kind);for(const [k,v] of Object.entries(props))e.setAttribute(k,String(v));return e;};
let source=null;
function draw(){
 const polys=source.footprints.assumed_per_floor;
 const root=$("g10-floor");root.replaceChildren();
 const pts=polys.flatMap(p=>p.scaled_convex_hull_outline_xy_m);
 const minX=Math.min(...pts.map(p=>p[0])),maxX=Math.max(...pts.map(p=>p[0]));
 const minY=Math.min(...pts.map(p=>p[1])),maxY=Math.max(...pts.map(p=>p[1]));
 const sc=Math.min(355/(maxX-minX),230/(maxY-minY));
 ["#2e9585","#4d8dbd","#bc8e57"].forEach((clr,i)=>{
  const p=polys[i];
  const vertices=p.scaled_convex_hull_outline_xy_m.map(([x,y])=>
     [48+(x-minX)*sc,276-(y-minY)*sc].join(",")).join(" ");
  root.append(shape("polygon",{points:vertices,fill:"none",stroke:clr,"stroke-width":3}));
  const title=shape("text",{x:24,y:20+i*17,fill:clr,"font-size":12});
  title.textContent="Assumed floor "+(i+1)+" · "+fmt(p.source_caption_area_m2)+" m²";
  root.append(title);
 });
 $("g10-floor-note").textContent="Scaled area-matched convex hulls. Actual slab outlines, terrace boundaries, openings, supporting beams and diaphragm are not verified.";
}
function select(){
 const c=source?.model_cases.find(v=>v.id===$("g10-case").value);if(!c)return;
 const a=$("g10-case-mass");a.replaceChildren();
 for(const [name,val] of [["Source ETABS W",source.source_seismic_W_kN],
       ["Trial seismic W",c.trial_seismic_weight_kN],["Source minus trial",c.source_minus_trial_kN]]){
  const row=el("div",undefined,"lab-meter-wrap");
  const cap=el("div",undefined,"lab-meter-caption");cap.append(el("span",name),el("strong",fmt(val)+" kN"));
  const track=el("div",undefined,"lab-meter-track");
  const meter=el("span",undefined,"lab-meter-fill lab-new");
  meter.style.width=Math.min(100,100*Math.abs(val)/source.source_seismic_W_kN)+"%";
  track.append(meter);row.append(cap,track);a.append(row);
 }
 const inverse=c.classification==="INVERSE_NUMERICAL_FIT_NOT_EVIDENCE";
 $("g10-case-note").textContent=(inverse?
    "WARNING: a zero residual obtained by reverse-fitting unknown partitions is NOT source verification. ":
    "Provisional sensitivity, NOT an accepted load assignment. ")+c.explanation;
 $("g10-to-studio").href="g15-3d.html?assumption="+encodeURIComponent(c.id);
}
fetch("data/g15-gate10-assumptions.v0.1.json",{cache:"no-store"})
.then(r=>r.ok?r.json():Promise.reject(Error("Numerical source unavailable")))
.then(d=>{
 if(d.schema!=="jp.structural.g15.gate10.assumption_sensitivity.v0.1"||
    d.engineering_approval!==false||d.seismic_mass_source_reconciled!==false||
    d.source_F3_one_way_shear!=="NOT SAFE IN ONE WAY SHEAR"||
    d.model_cases?.length!==9||d.footprints?.assumed_per_floor?.length!==3||
    d.model_cases.some(c=>c.seismic_mass_accepted!==false))
    throw Error("Engineering provenance or HOLD mismatch");
 source=d;
 const head=[["Hypothetical floor outlines","3 source area captions"],
 ["Assumed walls",d.wall_candidates.edges.length+" edges"],
 ["Mass sensitivity cases",d.model_cases.length],
 ["Engineering sign-off","HOLD"]];
 $("g10-head").replaceChildren(...head.map(([key,value])=>{
  const b=el("div",undefined,"lab-kpi");b.append(el("small",key),el("strong",value));return b;
 }));
 $("g10-case").replaceChildren(...d.model_cases.map(c=>{
   const option=el("option",c.label);option.value=c.id;return option;
 }));
 const table=el("table",undefined,"lab-table");
 const tr=el("tr");["ETABS mass-source trial","Weight kN","Issue"].forEach(t=>tr.append(el("th",t)));table.append(tr);
 d.etabs_mass_source_alternatives.forEach(x=>{
  const row=el("tr");
  [x.id,fmt(x.trial_W_kN),x.double_count_flag?"DOUBLED SELFWEIGHT":"NO DOUBLE COUNT"].forEach(t=>row.append(el("td",t)));
  table.append(row);
 });
 $("g10-etabs").replaceChildren(table);
 $("g10-case").addEventListener("change",select);
 draw();select();
}).catch(e=>$("g10-head").replaceChildren(el("p","Gate10 assumption HOLD: "+e.message)));
})();
