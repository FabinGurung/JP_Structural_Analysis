/* Bounded source-derived Gate09 evidence; zero extrapolated slab/wall mass. */
(()=>{"use strict";
const $=id=>document.getElementById(id);
if(!$("g09-summary"))return;
const mk=(name,text,cls)=>{const e=document.createElement(name);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;};
const fmt=n=>Number.isFinite(n)?n.toLocaleString("en-US",{maximumFractionDigits:3}):"—";
const ns="http://www.w3.org/2000/svg";
const svg=(n,at,txt)=>{const e=document.createElementNS(ns,n);for(const [k,v] of Object.entries(at))e.setAttribute(k,v);if(txt!==undefined)e.textContent=txt;return e;};
fetch("data/g15-gate09-source-audit.v0.1.json",{cache:"no-store"})
.then(r=>r.ok?r.json():Promise.reject(Error("Gate09 source audit unavailable")))
.then(d=>{
 const m=d.mass_reconciliation,p=d.panel;
 if(d.schema!=="jp.structural.g15.gate09.sample_panel_and_mass_audit.v0.1"||
    d.engineering_approval!==false||d.source_F3_status!=="NOT SAFE IN ONE WAY SHEAR")
    throw Error("Evidence schema or engineering HOLD invalid");
 if(!p||!m||p.grid_vertices.length!==4||m.source_mass_reconciled!==false||
    p.illustrative_panel_loads.additional_weight_to_gate08_reconciliation_kN!==0)
    throw Error("Source/mass validation failed");
 const values=[["Sample slab bay",fmt(p.area_m2)+" m²"],["Verified mapped wall segments",String(d.wall_rates.verified_wall_segments)],
 ["ETABS mass residual",fmt(m.unexplained_W_kN)+" kN"],["Source mass reconciliation","OPEN"]];
 $("g09-summary").replaceChildren(...values.map(([a,b])=>{const n=mk("div",undefined,"lab-kpi");n.append(mk("small",a),mk("strong",b));return n;}));
 const scene=$("g09-panel");scene.replaceChildren();
 const polygon=p.vertices_xy_m;
 const x0=Math.min(...polygon.map(z=>z.x)),y0=Math.min(...polygon.map(z=>z.y));
 const vertices=polygon.map(v=>({label:v.grid,x:45+(v.x-x0)*58,y:242-(v.y-y0)*55}));
 scene.append(svg("polygon",{points:vertices.map(v=>v.x+","+v.y).join(" "),fill:"#52b5a12a",stroke:"#308d80","stroke-width":3}));
 vertices.forEach(v=>{scene.append(svg("circle",{cx:v.x,cy:v.y,r:5,fill:"#308d80"}));scene.append(svg("text",{x:v.x+7,y:v.y-9,fill:"currentColor","font-size":14},v.label));});
 scene.append(svg("text",{x:45,y:273,fill:"currentColor","font-size":12},"Source grid spans: 4.965 m × 3.600 m"));
 $("g09-panel-text").textContent="Original sample page 55: 4.97 × 3.60 m; four candidate beam lines traced. G2 is a beam-line intersection, not a source column. Storey, openings and actual slab extent remain unknown.";
 const source=m.reported_ETABS_W_kN;
 const bars=[["Source ETABS W",source],["Gate08 conditional trial",m.working_trial_W_kN],["Unexplained difference",m.unexplained_W_kN]];
 $("g09-bars").replaceChildren(...bars.map(([name,val],i)=>{
 const box=mk("div",undefined,"lab-meter-wrap"),head=mk("div",undefined,"lab-meter-caption");
 head.append(mk("span",name),mk("strong",fmt(val)+" kN"));
 const track=mk("div",undefined,"lab-meter-track"),fill=mk("span",undefined,"lab-meter-fill "+(i===2?"lab-ref":"lab-new"));
 fill.style.width=(100*val/source)+"%";track.append(fill);box.append(head,track);return box;
 }));
 $("g09-mass-text").textContent=fmt(m.unexplained_pct_source_W)+"% unresolved. Source sample adds zero new mass (already represented in assumed floor loads). Main/partition inverse lengths are diagnostic only; none is mapped to actual wall geometry.";
 }).catch(err=>$("g09-summary").replaceChildren(mk("p","Gate09 evidence HOLD: "+err.message)));
})();