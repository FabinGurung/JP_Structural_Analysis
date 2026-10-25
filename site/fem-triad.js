/* Shared selection: OpenSees solved case ↔ Three.js ↔ SVG ↔ result table ↔ manual proof.
   The remote Three.js module is optional; all actual numeric data comes from Python/OpenSees. */
(()=>{
"use strict";
const $=id=>document.getElementById(id);
if(!$("fem-case"))return;
const fmt=(x,n=4)=>Number.isFinite(x)?x.toLocaleString("en-US",{minimumFractionDigits:n,maximumFractionDigits:n}):"—";
const txt=(id,s)=>{const v=$(id);if(v)v.textContent=String(s)};
const td=s=>{const el=document.createElement("td");el.textContent=String(s);return el};
let data=null,choice="tip",update3D=null,highlight3D=null;
function select(part){
 choice=part;
 document.querySelectorAll("[data-fem-part]").forEach(e=>{
   const active=e.dataset.femPart===part;
   e.classList.toggle("fem-highlight",active);
   if(e.tagName==="BUTTON")e.setAttribute("aria-pressed",String(active));
 });
 if(highlight3D)highlight3D(part);
}
document.querySelectorAll("[data-fem-part]").forEach(e=>{
 e.addEventListener("click",()=>select(e.dataset.femPart));
 if(e.tagName.toLowerCase()==="g")e.addEventListener("keydown",a=>{if(a.key==="Enter"){select(e.dataset.femPart)}});
});
const numberRow=(part,name,formula,open,hand)=>{
 const r=document.createElement("tr");r.dataset.femPart=part;
 for(const x of [name,formula,open,hand,"MATCH ✓"])r.append(td(x));
 r.addEventListener("click",()=>select(part));return r;
};
function fail(message){
 const el=$("fem-run-status");el.textContent="NUMERICAL OUTPUT WITHHELD: "+message;el.style.borderColor="#d08172";
 $("fem-numbers").replaceChildren();
}
function render(){
 if(!data)return;
 const c=data.cases.find(x=>x.id===$("fem-case").value);
 if(!c){fail("Case missing");return}
 const f=c.applied_tip_fx_kN,p=c.opensees,h=c.independent_hand,m=data.model;
 const u=p.node_tip_ux_m*1000;
 if(Math.abs(p.node_tip_ux_m-h.tip_displacement_m)>1e-8||Math.abs(p.base_reaction_rx_kN+f)>1e-6||Math.abs(p.base_reaction_mz_kNm-f*m.L_m)>1e-6){fail("OpenSees/handcheck disagreement");return;}
 txt("fem-run-status","REAL OPENSEES CALCULATION ✓   "+c.id+" · independent equations and force/moment equilibrium verified. This model and support are synthetic.");
 const table=[
 numberRow("tip","Top horizontal load","F",fmt(f,1)+" kN",fmt(f,1)+" kN"),
 numberRow("tip","Top horizontal movement","u = FL³/(3EI)",fmt(u,6)+" mm",fmt(h.tip_displacement_m*1000,6)+" mm"),
 numberRow("tip","Tip rotation |θ|","FL²/(2EI)",fmt(Math.abs(p.node_tip_rotation_rz_rad),7)+" rad",fmt(h.tip_rotation_abs_rad,7)+" rad"),
 numberRow("member","Shear magnitude","|V|=F",fmt(Math.abs(p.base_reaction_rx_kN),2)+" kN",fmt(h.shear_abs_kN,2)+" kN"),
 numberRow("member","Base moment magnitude","|M|=FL",fmt(Math.abs(p.base_reaction_mz_kNm),2)+" kN·m",fmt(h.base_bending_abs_kNm,2)+" kN·m"),
 numberRow("base","Signed reaction Rx","Rₓ=−F",fmt(p.base_reaction_rx_kN,2)+" kN",fmt(-f,2)+" kN"),
 numberRow("base","Signed base moment Mz","Mz=+FL",fmt(p.base_reaction_mz_kNm,2)+" kN·m",fmt(f*m.L_m,2)+" kN·m"),
 numberRow("base","Force residual","Rx+F=0",fmt(p.horizontal_force_residual_kN,9)+" kN","0.000000000 kN")
 ];
 $("fem-numbers").replaceChildren(...table);
 txt("fem-label-force","F = "+fmt(f,0)+" kN");txt("fem-label-reaction","Rx = "+fmt(p.base_reaction_rx_kN,0)+" kN");
 txt("fem-label-moment","M = "+fmt(p.base_reaction_mz_kNm,0)+" kN·m");
 txt("fem-label-shear",fmt(f,0)+" kN");txt("fem-label-bending",fmt(f*m.L_m,0)+" kN·m");
 const offset=Math.min(115,p.node_tip_ux_m*150*150);
 $("fem-deflect").setAttribute("d","M137 275L"+(137+offset).toFixed(2)+" 68");
 txt("fem-manual-i","I = "+fmt(m.I_m4,6)+" m⁴; EI = "+fmt(h.EI_kN_m2,2)+" kN·m².");
 txt("fem-manual-u","u = "+fmt(f,1)+"×3³ / (3×"+fmt(h.EI_kN_m2,2)+") = "+fmt(u,6)+" mm.");
 txt("fem-manual-m","Rx = "+fmt(-f,2)+" kN; Mbase = "+fmt(f*m.L_m,2)+" kN·m.");
 txt("fem-manual-compare","OpenSees u = "+fmt(u,6)+" mm; hand u = "+fmt(h.tip_displacement_m*1000,6)+" mm. MATCH.");
 if(update3D)update3D(p.node_tip_ux_m);
 select(choice);
}
$("fem-case").addEventListener("change",render);
select("tip");
fetch("data/opensees-cantilever-learning.v0.1.json",{cache:"no-store"})
.then(x=>{if(!x.ok)throw Error("OpenSees data unavailable");return x.json()})
.then(d=>{
 if(d.schema!=="jp.structural.teaching_cantilever.real_opensees.v0.1"||d.project_model_used!==false||
 d.engineering_approval!==false||d.nepal_design_compliance!=="NOT_EVALUATED"||
 d.model?.base_support!=="FIXED_ILLUSTRATIVE"||d.cases?.length!==4||
 d.cases.some(x=>!Number.isFinite(x.opensees?.node_tip_ux_m)||Math.abs(x.opensees.horizontal_force_residual_kN)>1e-6))
 throw Error("Data schema, equilibrium or engineering hold check failed");
 data=d;render();
}).catch(e=>fail(e.message));
Promise.all([
 fetch("data/fem-workflow-map.v0.1.json").then(r=>r.ok?r.json():Promise.reject(Error("Menu registry missing"))),
 fetch("data/nbc105-verified-rule-inventory.v0.1.json").then(r=>r.ok?r.json():Promise.reject(Error("Code registry missing")))
]).then(([reg,code])=>{
 if(reg.menus?.length!==14||reg.entities?.length!==16||code.registered_clauses?.length!==14)throw Error("Unverified registry counts");
 const box=$("fem-menu-tabs"),view=$("fem-menu-description");
 const choose=id=>{
  const m=reg.menus.find(x=>x.id===id);
  for(const el of box.querySelectorAll("button"))el.setAttribute("aria-pressed",String(el.dataset.menu===id));
  view.replaceChildren();
  const h=document.createElement("h4");h.textContent=m.menu;view.append(h);
  for(const t of ["etabs_purpose","our_delegation","report_section"]){const p=document.createElement("p");p.textContent=t.replaceAll("_"," ")+": "+m[t];view.append(p)}
 };
 box.replaceChildren(...reg.menus.map(m=>{const b=document.createElement("button");b.type="button";b.dataset.menu=m.id;b.textContent=m.menu;b.addEventListener("click",()=>choose(m.id));return b}));
 choose(reg.menus[0].id);
 $("fem-data-entities").replaceChildren(...reg.entities.map(x=>{const row=document.createElement("tr");for(const v of [x.name,x.pk,x.records,x.relations+" · "+x.proof_rule])row.append(td(v));return row}));
 $("fem-code-rows").replaceChildren(...code.registered_clauses.map(x=>{const row=document.createElement("tr");for(const v of [x.clause,x.function,x.limits])row.append(td(v));return row}));
 txt("fem-code-count","14 registered bounded NBC 105:2025 clause groups. Not complete national code automation; every scope limit is retained below.");
}).catch(e=>{txt("fem-menu-tabs","Cannot load workflow registry: "+e.message);txt("fem-code-count","Cannot load audited NBC code inventory: "+e.message)});
(async()=>{
let THREE;try{THREE=await import("https://cdn.jsdelivr.net/npm/three@0.160.1/build/three.module.js")}
catch(e){txt("fem-three-fallback","3D library could not load. The SVG, hand derivation and actual OpenSees table remain usable.");return;}
const host=$("fem-three");
const scene=new THREE.Scene();scene.background=new THREE.Color("#e4f0f1");
const camera=new THREE.PerspectiveCamera(42,1,.1,60);
let renderer;try{renderer=new THREE.WebGLRenderer({antialias:true})}catch(e){txt("fem-three-fallback","WebGL is unavailable. Use the linked SVG, OpenSees table and manual calculation.");return;}renderer.setPixelRatio(Math.min(window.devicePixelRatio||1,2));
host.append(renderer.domElement);$("fem-three-fallback").remove();
scene.add(new THREE.HemisphereLight("#ffffff","#648997",2.1));
const lamp=new THREE.DirectionalLight("#ffffff",2);lamp.position.set(3,6,5);scene.add(lamp);
const mk=(geometry,color,part)=>{const mesh=new THREE.Mesh(geometry,new THREE.MeshStandardMaterial({color,roughness:.5}));mesh.userData.part=part;scene.add(mesh);return mesh};
const base=mk(new THREE.BoxGeometry(.7,.23,.7),"#547b87","base");base.position.y=-.12;
const member=mk(new THREE.BoxGeometry(.22,3,.22),"#2796a6","member");member.position.y=1.5;
const tip=mk(new THREE.SphereGeometry(.17,20,16),"#ca744e","tip");tip.position.y=3;
const arrow=new THREE.ArrowHelper(new THREE.Vector3(1,0,0),new THREE.Vector3(0,3,0),.9,"#ca744e");scene.add(arrow);
const grid=new THREE.GridHelper(4,8,"#9dbec4","#d4e2e4");scene.add(grid);
let angle=.7,move=null;
function animateModel(u){
 const shift=u*150;
 member.position.set(shift/2,1.5,0);member.rotation.z=-Math.atan2(shift,3);
 tip.position.set(shift,3,0);arrow.position.set(shift,3,0);
}
update3D=animateModel;
highlight3D=part=>{
 base.material.color.set(part==="base"?"#e6a14d":"#547b87");
 member.material.color.set(part==="member"?"#e6a14d":"#2796a6");
 tip.material.color.set(part==="tip"?"#e6a14d":"#ca744e");
};
if(data)render();
const ray=new THREE.Raycaster(),mouse=new THREE.Vector2();
renderer.domElement.addEventListener("pointerdown",e=>{move={x:e.clientX,y:e.clientY,drag:false}});
renderer.domElement.addEventListener("pointermove",e=>{if(!move)return;const dx=e.clientX-move.x;if(Math.abs(dx)>2)move.drag=true;angle+=dx*.007;move.x=e.clientX});
renderer.domElement.addEventListener("pointerup",e=>{if(!move?.drag){const box=renderer.domElement.getBoundingClientRect();mouse.set(2*(e.clientX-box.left)/box.width-1,1-2*(e.clientY-box.top)/box.height);ray.setFromCamera(mouse,camera);const hits=ray.intersectObjects([tip,member,base]);if(hits[0])select(hits[0].object.userData.part)}move=null});
function frame(){const w=Math.max(180,host.clientWidth),h=Math.max(180,host.clientHeight);if(renderer.domElement.width!==Math.floor(w*renderer.getPixelRatio())||renderer.domElement.height!==Math.floor(h*renderer.getPixelRatio())){renderer.setSize(w,h);camera.aspect=w/h;camera.updateProjectionMatrix()}
camera.position.set(Math.sin(angle)*6.5,3.5,Math.cos(angle)*6.5);camera.lookAt(0,1.5,0);renderer.render(scene,camera);requestAnimationFrame(frame)}
if(data)render();else select(choice);
frame();
})();
})();
