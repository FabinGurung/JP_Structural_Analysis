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
