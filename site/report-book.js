/* Chapter-first report reader: runs on static GitHub Pages, consumes actual OpenSees output.
 * No dynamic calculations or safety claims happen in the browser.
 */
(() => {
"use strict";
const byId = id => document.getElementById(id);
const n = (v,d=3) => typeof v==="number" && Number.isFinite(v)
 ? v.toLocaleString("en-US",{minimumFractionDigits:d,maximumFractionDigits:d}) : "—";
const node = (tag,text,cl) => { const e=document.createElement(tag);if(text!==undefined)e.textContent=String(text);if(cl)e.className=cl;return e; };
const fill = (id, elems) => {const root=byId(id);if(root)root.replaceChildren(...elems);};
const block = (label,value) => {const e=node("div",undefined,"rb-metric");e.append(node("small",label),node("strong",value));return e;};
const table=(headers,rows)=>{
 const t=node("table"); const h=node("thead"),tr=node("tr");
 for(const x of headers)tr.append(node("th",x));
 h.append(tr);t.append(h);const b=node("tbody");
 for(const row of rows){const r=node("tr");for(const val of row)r.append(node("td",val));b.append(r);}
 t.append(b);return t;
};
const render= d =>{
 if(d.schema!=="jp.structural.g15.gate21.open_reproducible_sar.v0.1" ||
 d.model_ETABS_source_verified!==false || d.engineering_approval!==false ||
 d.F3_verdict!=="NOT SAFE IN ONE WAY SHEAR"||d.counts?.members!==165 ||
 d.case_count!==5||d.cases?.length!==5||d.signed_end_action_count!==825 ||
 d.source_gates_open!==15|| !Array.isArray(d.provenance) ||
 d.provenance.length!==7 ||!d.ESM?.floor ||d.ESM.floor.length!==3 ||
 d.cases.some(c=>!(c.force_residual_kN<0.001)||!(c.moment_residual_kNm<0.001)))
 throw Error("Generated report missing, inconsistent or unexpectedly claims acceptance");
 const exec=byId("rb-executive");
 if(exec){
   const p=node("p","This chapter is shown first but its numerical summary is assembled from the completed OpenSees job. "+
    d.case_count+" independently solved static cases use "+d.counts.members+" provisional frame members and "+d.counts.nodes+
    " nodes. The equivalent-static trial base shear is "+n(d.ESM.V_kN,3)+" kN. Original reported seismic weight: "+
    n(d.ESM.W_reported_ETABS_kN,4)+" kN; conditionally converted floor weights total "+n(d.ESM.W_kN,4)+" kN.");
   const w=node("p","These are working numerical results, not an accepted assessment of the original building. "+
    "Authentic ETABS member/area assignments, site-specific coefficients and full foundation redesign remain missing.");
   exec.replaceChildren(p,w);
 }
 fill("rb-seismic-metrics",[block("Conditional seismic W",n(d.ESM.W_kN,3)+" kN"),
 block("Original ETABS reported W",n(d.ESM.W_reported_ETABS_kN,4)+" kN"),
 block("Assumed / source-reported Cd",n(d.ESM.Cd,3)),
 block("Calculated trial base shear",n(d.ESM.V_kN,3)+" kN")]);
 fill("rb-provenance",[table(["Input parameter","Value","Source classification","Citation","Uncertainty"],d.provenance.map(p=>[
 p.id,JSON.stringify(p.value),p.class,p.citation,p.uncertainty]))]);
 fill("rb-floor-table",[table(["Storey","Elevation (m)","Conditional Wi (kN)","Computed Fi (kN)"],d.ESM.floor.map(f=>[
 f.story,n(f.elevation_m,3),n(f.Wi_kN,4),n(f.Fi_kN,4)]))]);
 fill("rb-solver-case-summary",[table(["OpenSees case","Roof horizontal (mm)","Reaction X (kN)","Reaction Y (kN)","Reaction Z (kN)","Max force residual (kN)","Max moment residual (kN·m)"],d.cases.map(c=>[
 c.name,n(c.roof_max_mm,4),n(c.reactions_kN_xyz[0],3),n(c.reactions_kN_xyz[1],3),n(c.reactions_kN_xyz[2],3),
 n(c.force_residual_kN,8),n(c.moment_residual_kNm,8)]))]);
 fill("rb-result-metrics",[block("Solved cases",String(d.cases.length)),
 block("Signed member actions",d.signed_end_action_count+" rows"),
 block("Max lateral roof trial",n(Math.max(...d.cases.map(x=>x.roof_max_mm)),4)+" mm"),
 block("Source F3 verdict","UNSAFE")]);
 fill("rb-chord-table",[table(["Load case","Storey","Elastic chord (mm)","Elastic chord / height","NBC design check"],d.cases.flatMap(c=>c.story_chord_metrics.map(s=>[
 c.name,s.story,n(s.max_elastic_chord_mm,5),n(s.elastic_chord_ratio,7),"NOT EVALUATED"])))]);
 fill("rb-hold-metrics",[block("Gate20 source obligations",d.source_gates_open+" OPEN"),
 block("Original ETABS authenticated","NO"),
 block("P–Delta executed","NO"),
 block("F3 design verdict","NOT SAFE")]);
};
const print=byId("rb-print");if(print)print.addEventListener("click",()=>window.print());
const chapters=[...document.querySelectorAll(".rb-chapter")];
const links=[...document.querySelectorAll("[data-nav-chapter]")];
if(typeof IntersectionObserver!=="undefined"){
 const observer=new IntersectionObserver(entries=>{
  const visible=entries.filter(e=>e.isIntersecting).sort((a,b)=>a.boundingClientRect.top-b.boundingClientRect.top);
  if(!visible.length)return;
  const id=visible[0].target.dataset.chapter;
  for(const l of links){if(l.dataset.navChapter===id)l.setAttribute("aria-current","location");else l.removeAttribute("aria-current");}
 },{rootMargin:"-15% 0px -65% 0px",threshold:0});
 chapters.forEach(ch=>observer.observe(ch));
}
fetch("reports/g15-gate21-report.v0.1.json",{cache:"no-store"})
 .then(res=>res.ok?res.json():Promise.reject(Error("numerical report fetch failed")))
 .then(render).catch(err=>{
  for(const id of ["rb-executive","rb-seismic-metrics","rb-provenance","rb-floor-table",
      "rb-solver-case-summary","rb-result-metrics","rb-chord-table","rb-hold-metrics"])
     fill(id,[node("p","Numerical evidence withheld: "+err.message,"rb-error")]);
 });
})();
