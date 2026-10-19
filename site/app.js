"use strict";
(function(){
  const $=id=>document.getElementById(id);
  const build=$("build");
  if(build){fetch("build-meta.json",{cache:"no-store"}).then(r=>r.ok?r.json():Promise.reject()).then(d=>{build.textContent="Pages snapshot "+String(d.sha||"").slice(0,10)+" · verified build";}).catch(()=>{build.textContent="Versioned public documentation";});}
  const summary=document.querySelector("[data-coverage-summary]");
  const list=$("coverage-list"),search=$("search"),select=$("status"),count=$("count");
  if(!summary&&!list)return;
  const labels={IMPLEMENTED_BOUNDED:"Bounded",PARTIAL:"Partial",DRAFT_UNVALIDATED:"Draft",MISSING:"Missing"};
  const classes={IMPLEMENTED_BOUNDED:"bounded",PARTIAL:"partial",DRAFT_UNVALIDATED:"draft",MISSING:"missing"};
  const node=(tag,text,cls)=>{const x=document.createElement(tag);if(text!==undefined)x.textContent=text;if(cls)x.className=cls;return x};
  fetch("data/report-calculation-coverage.v0.1.json",{cache:"no-store"})
    .then(r=>r.ok?r.json():Promise.reject(Error("Registry unavailable")))
    .then(obj=>{
      if(obj.schema!=="jp.structural.calculation_coverage.v0.1"||!Array.isArray(obj.requirements))throw Error("Invalid registry");
      const rows=obj.requirements;
      if(summary){const statuses=Object.keys(labels);summary.replaceChildren(...statuses.map(s=>{const box=node("div",undefined,"metric");box.append(node("strong",String(rows.filter(x=>x.status===s).length)),node("span",labels[s]));return box;}));}
      if(!list)return;
      const draw=()=>{
        const term=(search?.value||"").trim().toLowerCase();
        const filter=select?.value||"";
        const items=rows.filter(r=>(!filter||r.status===filter)&&(!term||[r.id,r.title,r.precedent_sections,r.remaining_scope,r.validation_gate].join(" ").toLowerCase().includes(term)));
        list.replaceChildren();
        for(const r of items){
          const card=node("article",undefined,"coverage-item");
          const head=node("div",undefined,"coverage-head");
          head.append(node("span",r.id+" · "+r.priority,"eyebrow"),node("span",labels[r.status]||"Unverified","pill "+(classes[r.status]||"draft")));
          const title=node("h3",r.title),source=node("p","Report sections: "+r.precedent_sections);
          const detail=node("details");detail.append(node("summary","Scope and verification"));
          detail.append(node("h4","Still needed"),node("p",r.remaining_scope),node("h4","Acceptance test"),node("p",r.validation_gate));
          if(r.implemented_paths?.length){
            detail.append(node("h4","Existing source code"));
            const ul=node("ul",undefined,"source-links");
            for(const path of r.implemented_paths){const li=node("li"),a=node("a",path.split("/").slice(-1)[0]);a.href="https://github.com/FabinGurung/JP_Structural_Analysis/blob/feature/post-seq9-first-party-no-e2k-20261015/"+path;a.rel="noopener noreferrer";a.target="_blank";li.append(a);ul.append(li);}
            detail.append(ul);
          }
          card.append(head,title,source,detail);list.append(card);
        }
        if(count)count.textContent=items.length+" of "+rows.length+" report requirements shown";
      };
      search?.addEventListener("input",draw);select?.addEventListener("change",draw);draw();
    })
    .catch(err=>{if(count)count.textContent="Unable to load versioned registry: "+err.message;if(summary)summary.textContent="Coverage source temporarily unavailable";});
})();


/* Engineering Guild interaction: fantasy UX, numeric authority unchanged. */
(function(){
const themeKey='jp-engineering-guild-mode';
const btn=document.getElementById('mode-toggle');
let saved='day';try{saved=localStorage.getItem(themeKey)||'day';}catch(e){}
document.documentElement.dataset.theme=saved==='night'?'night':'day';
function label(){const night=document.documentElement.dataset.theme==='night';if(document.getElementById('mode-label'))document.getElementById('mode-label').textContent=night?'Daylight':'Night raid';btn?.setAttribute('aria-pressed',String(night));}
label();btn?.addEventListener('click',()=>{const val=document.documentElement.dataset.theme==='night'?'day':'night';document.documentElement.dataset.theme=val;try{localStorage.setItem(themeKey,val);}catch(e){}label();});
const stages=[
['Source & model','Source IDs + QA','Governed drawings, materials, soil and code editions enter a typed canonical model.','Gather verified source records before the trial begins.'],
['Loads & seismic','Bounded calculations','Gravity and mass source, NBC105:2025 spectrum coefficients and seismic floor forces.','Forge actions from explicit engineering inputs; never guess a load location.'],
['Solve & compare','Bounded FE','OpenSees static/modal analysis and equilibrium checks, with reference discrepancies retained.','Trial a supported solver configuration, not a complete building certification.'],
['Design & check','Locked strength-design quest','RC beam, column, joint, slab, footing and stair design engines remain incomplete.','The true boss gate: capacity, detailing and independent verification.'],
['Report & preserve','Draft output','Normalized results feed R&D LaTeX, QA manifests and private project PDF archive.','Seal the report only after all engineering checks and review gates.']
];
const list=document.querySelectorAll('#quest-track .stage'),panel=document.getElementById('quest-detail');
function activate(idx){if(!panel||!stages[idx])return;list.forEach((el,i)=>{el.classList.toggle('guild-active',i===idx);el.setAttribute('aria-pressed',String(i===idx));});const s=stages[idx];
panel.replaceChildren();
const eyebrow=document.createElement('div');eyebrow.className='eyebrow';eyebrow.textContent='QUEST '+String(idx+1).padStart(2,'0')+' / '+s[1].toUpperCase();
const title=document.createElement('h3');title.textContent=s[0];const p=document.createElement('p');p.textContent='ENGINEERING / '+s[2];const lore=document.createElement('small');lore.textContent='GUILD OBJECTIVE / '+s[3];panel.append(eyebrow,title,p,lore);}
list.forEach((el,i)=>{el.addEventListener('click',()=>activate(i));el.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();activate(i);}});});if(list.length)activate(0);
})();


/* M09 synthetic numerical evidence, generated from the same tested source code
   during CI and during every Pages deployment. No hardcoded strengths. */
(function(){
  "use strict";
  const views=[...document.querySelectorAll("[data-m09-view]")];
  if(!views.length)return;
  const el=(tag,txt,cls)=>{const n=document.createElement(tag);if(txt!==undefined)n.textContent=txt;if(cls)n.className=cls;return n;};
  const fmt=(v,n=2)=>Number.isFinite(v)?v.toLocaleString("en-US",{minimumFractionDigits:n,maximumFractionDigits:n}):"unverified";
  const metric=(label,value,sub)=>{const x=el("div",undefined,"m09-stat");
    x.append(el("span",label),el("strong",value),el("small",sub));return x;};
  const addDetail=(parent,title,value)=>{const p=el("p");p.append(el("strong",title+" "),document.createTextNode(String(value)));parent.append(p);};
  function draw(view,d){
    const r=d.valid_case,reference=r.legacy_interaction,unsafe=d.intentionally_unsafe_case;
    const x=r.chosen_conservative_Mux1_kNm,y=r.chosen_conservative_Muy1_kNm;
    const ratio=reference.interaction_utilization;
    const head=el("div",undefined,"m09-bar-head");
    head.append(el("strong","NUMERICAL SECTION PRECHECK"),el("span","Code review HOLD","m09-status"));
    const grid=el("div",undefined,"m09-numbers");
    grid.append(metric("Axial load (Pu)",fmt(r.face_capacities[0].input_target_axial_kN)+" kN","Equilibrium from section integration"),
       metric("X-axis section capacity",fmt(x)+" kN·m","Minimum of two compression faces"),
       metric("Y-axis section capacity",fmt(y)+" kN·m","Minimum of two compression faces"),
       metric("Biaxial utilization",fmt(ratio,3),"IS 456 §39.6 screen; not approval"));
    const equilibrium=Math.max(...r.face_capacities.map(f=>Math.abs(f.axial_equilibrium_residual_kN)));
    const checks=el("div",undefined,"m09-evidence");
    checks.append(el("h3","Validation trail"));
    const list=el("ul",undefined,"m09-checks");
    for(const item of [
      ["Axial equilibrium",equilibrium<0.0001?"NUMERIC PASS · max residual "+fmt(equilibrium,6)+" kN":"HOLD"],
      ["Strength direction","Four faces X± / Y±, conservative magnitude"],
      ["Unsafe case",unsafe.status==="FAIL"?"FAIL detected in intentional overload":"HOLD"],
      ["Design approval","HOLD · independent code benchmark outstanding"]]){
      const li=el("li");li.append(el("strong",item[0]),el("span",item[1]));list.append(li);
    }
    checks.append(list);
    const assumptions=el("details",undefined,"m09-assumptions");
    const caption=el("summary","Model assumptions & exclusions");
    assumptions.append(caption);
    for(const [key,val] of Object.entries(d.assumptions||{}))addDetail(assumptions,key.replaceAll("_"," ").toUpperCase()+":",val);
    const source=el("p","Data: "+d.case_id+" · "+d.published_code+" · payload sha256 "+String(d.case_payload_sha256).slice(0,16)+"…","m09-provenance");
    view.replaceChildren(head,grid);
    if(view.dataset.m09View==="full"){
      const bar=el("div",undefined,"m09-util-track"),fill=el("span",undefined,"m09-util-fill");
      fill.style.width=Math.max(0,Math.min(100,ratio*100))+"%";
      bar.setAttribute("role","img");
      bar.setAttribute("aria-label","Numerical biaxial interaction utilization "+fmt(ratio,3)+" of unity; not design approval");
      bar.append(fill);view.append(bar);
    }
    view.append(checks,assumptions,source);
  }
  fetch("data/m09-section-capacity.v0.1.json",{cache:"no-store"})
    .then(r=>r.ok?r.json():Promise.reject(Error("M09 artifact unavailable")))
    .then(d=>{
      if(d.schema!=="jp.structural.m09_column_section.v0.1"||
         d.engineering_approval!==false||d.report_accepted!==false||
         d.valid_case?.face_capacities?.length!==4||
         d.valid_case?.status!=="BOUNDED_NUMERICAL_PRECHECK_SP16_CHART_AND_DETAILING_HOLD"||
         d.intentionally_unsafe_case?.status!=="FAIL"||
         !Number.isFinite(d.valid_case?.legacy_interaction?.interaction_utilization))
         throw Error("M09 evidence schema or safety states invalid");
      views.forEach(v=>draw(v,d));
    }).catch(err=>views.forEach(v=>v.replaceChildren(el("p","M09 numerical display on HOLD: "+err.message,"m09-error"))));
})();
