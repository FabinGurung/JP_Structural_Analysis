/* Native ETABS21 SOURCE geometry, not an executed ETABS/OpenSees result.
 * All numbers rendered below are computed from the verified source-derived
 * ULS/SLS model assignment catalogue (original raw E2K bytes NOT public).
 */
(()=>{"use strict";
const $=id=>document.getElementById(id), ns="http://www.w3.org/2000/svg";
const f=(v,n=3)=>Number.isFinite(Number(v))?Number(v).toLocaleString("en-US",{maximumFractionDigits:n,minimumFractionDigits:n}):"—";
const tag=(name,attrs={},content)=>{const el=document.createElementNS(ns,name);
 for(const [k,v] of Object.entries(attrs))el.setAttribute(k,String(v));
 if(content!==undefined)el.textContent=content;
 return el;
};
const text=(s,klass)=>{const el=document.createElement("div");if(klass)el.className=klass;el.textContent=s;return el;};
let model=null,chosen="GF:B46",yaw=-.68,viewLevel="GF",kind="BEAM";
const structural=m=>m.kind==="BEAM"||m.kind==="COLUMN"||m.kind==="LINE";
const levels=["GF","FF","TF"];
const bounds={minX:-1350,maxX:21350,minY:-700,maxY:12550};
const spanX=bounds.maxX-bounds.minX,spanY=bounds.maxY-bounds.minY;
function xy(x,y){return [42+(x-bounds.minX)/spanX*646,415-(y-bounds.minY)/spanY*350];}
function xyz(x,y,z){
 const px=(x-(bounds.minX+bounds.maxX)/2)/1000;
 const py=(y-(bounds.minY+bounds.maxY)/2)/1000;
 const pz=z/1000;
 const rx=px*Math.cos(yaw)-py*Math.sin(yaw);
 const ry=px*Math.sin(yaw)+py*Math.cos(yaw);
 return [365+rx*19,315+ry*8.8-pz*19];
}
function addChoiceClick(node,key){
 node.dataset.select=key;node.setAttribute("tabindex","0");
 node.setAttribute("role","button");
 node.setAttribute("aria-label","Select source element "+key);
 node.addEventListener("click",()=>choose(key));
 node.addEventListener("keydown",e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();choose(key);}});
}
function choose(key){
 const [level,id]=key.split(":");const mem=model.members.find(v=>v.key===key);
 const shell=model.shells.find(v=>v.key===key);
 if(!mem&&!shell)return;
 viewLevel=level;kind=mem?mem.kind:shell.kind;chosen=key;
 $("r68-storey").value=level;$("r68-category").value=kind;
 fillSelect();$("r68-id").value=key;render();
}
function fillSelect(){
 const choices=kind==="BEAM"||kind==="COLUMN"||kind==="LINE"?model.members.filter(m=>m.kind===kind&&m.storey===viewLevel):
 model.shells.filter(m=>m.kind===kind&&m.storey===viewLevel);
 const sel=$("r68-id");sel.replaceChildren();
 for(const m of choices){
  const option=document.createElement("option");option.value=m.key;
  option.textContent=m.id+" · "+m.section;sel.append(option);
 }
 if(!choices.some(x=>x.key===chosen))chosen=choices[0]?.key??"";
 if(chosen)sel.value=chosen;
}
function selected(){return model.members.find(m=>m.key===chosen)??model.shells.find(m=>m.key===chosen);}
function plan(){
 const svg=$("r68-plan");svg.replaceChildren(tag("rect",{x:1,y:1,width:738,height:468,fill:"#fafdff",rx:10}));
 for(const [name,x] of Object.entries(model.grid_axes.X)){
  const [sx]=xy(x,bounds.minY);
  svg.append(tag("line",{x1:sx,y1:28,x2:sx,y2:433,stroke:"#c6d3db","stroke-dasharray":"3,5","stroke-width":.8}));
  svg.append(tag("text",{x:sx,y:20,"text-anchor":"middle",fill:"#42617a","font-size":11},name));
 }
 for(const [name,y] of Object.entries(model.grid_axes.Y)){
  const [,sy]=xy(bounds.minX,y);
  svg.append(tag("line",{x1:29,y1:sy,x2:702,y2:sy,stroke:"#c6d3db","stroke-dasharray":"3,5","stroke-width":.8}));
  svg.append(tag("text",{x:711,y:sy+4,fill:"#42617a","font-size":11},name));
 }
 for(const slab of model.shells.filter(s=>s.storey===viewLevel&&s.kind==="FLOOR")){
  const p=slab.vertices_xyz_mm.map(v=>xy(v[0],v[1]).join(",")).join(" ");
  const active=chosen===slab.key;
  const poly=tag("polygon",{points:p,stroke:active?"#d75d4d":"#b1d3d3",
   fill:active?"#ffd9c2":"#8fcfc6","fill-opacity":active?.9:.23,
   "stroke-width":active?2.4:.8});
  addChoiceClick(poly,slab.key);svg.append(poly);
 }
 for(const mem of model.members.filter(m=>m.storey===viewLevel&&structural(m))){
  const p=xy(mem.start_xyz_mm[0],mem.start_xyz_mm[1]),q=xy(mem.end_xyz_mm[0],mem.end_xyz_mm[1]);
  const active=chosen===mem.key;
  if(mem.kind==="COLUMN"){
   const circle=tag("circle",{cx:p[0],cy:p[1],r:active?7:4.3,
       fill:active?"#e95745":"#275e7d",stroke:"white","stroke-width":1});
   addChoiceClick(circle,mem.key);svg.append(circle);
  } else {
   const line=tag("line",{x1:p[0],y1:p[1],x2:q[0],y2:q[1],
     stroke:active?"#db4c40":mem.kind==="LINE"?"#a58e72":"#2d7990","stroke-width":active?5:mem.kind==="LINE"?1.6:2.0,
     opacity:active?1:.78,"stroke-linecap":"round"});
   addChoiceClick(line,mem.key);svg.append(line);
  }
 }
 const p=tag("text",{x:12,y:456,fill:"#617b8b","font-size":12},viewLevel+" · actual source centreline IDs (no report-force transfer)");
 svg.append(p);
}
function scene(){
 const svg=$("r68-scene");svg.replaceChildren(tag("rect",{x:1,y:1,width:738,height:468,fill:"#fafdff",rx:10}));
 const order=["GF","FF","TF"];
 for(const lv of order){
  for(const s of model.shells.filter(x=>x.storey===lv&&x.kind==="FLOOR")){
   const active=chosen===s.key;
   const pts=s.vertices_xyz_mm.map(v=>xyz(...v).join(",")).join(" ");
   const pl=tag("polygon",{points:pts,fill:active?"#efaa71":"#b3d5ca",
       "fill-opacity":active?.77:.09,stroke:active?"#c87032":"#aac6bd","stroke-width":active?2:0.7});
   addChoiceClick(pl,s.key);svg.append(pl);
  }
  for(const m of model.members.filter(x=>x.storey===lv&&structural(x))){
   const a=xyz(...m.start_xyz_mm),b=xyz(...m.end_xyz_mm),active=chosen===m.key;
   const el=tag("line",{x1:a[0],y1:a[1],x2:b[0],y2:b[1],
     stroke:active?"#e25748":m.kind==="COLUMN"?"#315879":m.kind==="LINE"?"#aa9e83":"#438d8f",
     "stroke-width":active?5:1.5,"stroke-linecap":"round",
     opacity:active?1:lv===viewLevel?.85:.28});
   addChoiceClick(el,m.key);svg.append(el);
  }
 }
 svg.append(tag("text",{x:12,y:24,fill:"#58768b","font-size":12},"ETABS21 source E2K · all 3 storeys · "+viewLevel+" selected"));
}
function box(parent,title,body){
 const x=text("","r68-inputbox"),b=document.createElement("strong");
 b.textContent=title;x.append(b);x.append(text(body));parent.append(x);
}
function step(parent,label,formula){
 const outer=text("","r68-step"),a=document.createElement("b"),b=document.createElement("code");
 a.textContent=label;b.textContent=formula;outer.append(a,b);parent.append(outer);
}
function panelDetail(m){
 $("r68-member-name").textContent=m.storey+" · "+m.kind.toLowerCase()+" "+m.id+" · "+m.section;
 const input=$("r68-numeric-input"),steps=$("r68-steps"),loads=$("r68-loads"),rebar=$("r68-rebar");
 input.replaceChildren();steps.replaceChildren();loads.replaceChildren();rebar.replaceChildren();
 const isFrame=m.start_xyz_mm!==undefined;
 if(isFrame){
  const a=m.start_xyz_mm,b=m.end_xyz_mm,L=m.length_mm;
  box(input,"Source end coordinates (mm)","I: ("+a.map(x=>f(x,2)).join(", ")+"); J: ("+b.map(x=>f(x,2)).join(", ")+").");
  box(input,"Section and actual model length",m.section+"; L = "+f(L/1000,4)+" m; source identity "+m.key);
  step(steps,"01 · Length","L = √[(Δx)² + (Δy)² + (Δz)²] for beams. For vertical column, L = "+f(L,1)+" mm (successive source storeys).");
  if(m.section_area_mm2!==undefined){
   const area=m.section_area_mm2,vol=m.section_gross_volume_m3,
       gamma=model.materials[m.material].unit_weight_N_mm3*1e6;
   step(steps,"02 · Section","Gross A = "+f(area,3)+" mm² (from source section "+m.section+"); material "+m.material);
   step(steps,"03 · Concrete","V = A × L / 10⁹ = "+f(area,3)+" × "+f(L,3)+" / 10⁹ = "+f(vol,6)+" m³");
   step(steps,"04 · Source selfweight proxy","γ = "+f(gamma,4)+" kN/m³; W≈γV = "+f(gamma,4)+" × "+f(vol,6)+" = "+f(m.source_dead_selfweight_proxy_kN,4)+" kN");
  } else step(steps,"02 · Missing frame section","Section NONE: line reference is not counted as an actual concrete beam.");
  const rb=m.rebar_model_section||{};
  if(Object.keys(rb).length){
   const desc=Object.entries(rb).map(([k,v])=>k+" = "+v).join(" · ");
   box(rebar,"Recorded ETABS section reinforcement inputs",desc);
  }
  const caveat=m.kind==="COLUMN"?
   "Column reinforcement pattern/bar areas are ETABS model-section inputs, not independently approved longitudinal rebar counts, lap lengths or tie cutting lengths. Applied axial reaction requires an actual frame solution.":
   m.kind==="LINE"?"An unsectioned ETABS LINE is geometric/loaded input, not an authenticated concrete beam. Its wall load can transfer to surrounding shell or frame mesh according to solver connectivity; do not assign beam selfweight, moments or reinforcement to it.":"Beam section cover and zero model design area fields do not establish final tension/compression bars. Shear/moment/reinforcement design requires the actual frame solver and signed combinations.";
  rebar.append(text(caveat,"r68-rebar-note"));
 }else{
  const s=model.shell_sections[m.section],area=m.projected_area_mm2;
  box(input,"Original polygon vertex coordinates",m.vertices_xyz_mm.map(x=>"("+x.map(v=>f(v,1)).join(",")+")").join(" · "));
  box(input,"Shell section",m.section+" · thickness "+f(m.thickness_mm,1)+" mm · material "+m.material);
  step(steps,"01 · Plan area","A_plan = ½ |Σ(xi·y(i+1) − x(i+1)·yi)| = "+f(area/1e6,5)+" m²");
  step(steps,"02 · Gross volume proxy","V_plan ≈ A_plan × t = "+f(area,2)+" × "+f(m.thickness_mm,1)+" / 10⁹ = "+f(m.plan_prism_volume_m3_proxy,6)+" m³");
  step(steps,"03 · Source selfweight proxy","V_plan × "+f(model.materials[m.material].unit_weight_N_mm3*1e6,3)+" kN/m³ ≈ "+f(m.source_dead_selfweight_proxy_kN,4)+" kN");
  rebar.append(text("Slab/panel vertices can have local Z offsets and sloping surfaces. The plan-projected area and prism volume are gross proxies, NOT exact three-dimensional shell concrete volumes or approved slab rebar schedules.","r68-rebar-note"));
 }
 if(!m.applied_loads.length)loads.append(text("No directly assigned wall, floor-finish or live gravity load rows on this object. Structural selfweight is handled separately by the Dead pattern; do not interpret absent direct rows as zero total force."));
 for(const r of m.applied_loads){
  const line=text("","r68-loadrow");
  const name=document.createElement("strong");name.textContent=r.pattern+" · "+r.method;
  line.append(name);line.append(text("Source formula: "+r.working.formula));
  const terms=Object.entries(r.working).filter(([k])=>k!=="formula").map(([k,v])=>k+" = "+f(v,5)).join(" · ");
  line.append(text(terms));
  line.append(text("Integrated "+f(r.raw_integrated_kN,6)+" kN × seismic participation "+f(r.mass_participation_factor,2)+" = "+f(r.mass_eligible_load_kN,6)+" kN"));
  loads.append(line);
 }
 if(m.kind==="BEAM"){
  const uniform=m.applied_loads.find(l=>l.pattern==="WALL LOAD"&&l.method==="U");
  if(uniform){
   const w=uniform.working.w_N_per_mm,L=m.length_mm/1000;
   const caution=text("","r68-inputbox");
   const head=document.createElement("strong");head.textContent="Optional hand-equilibrium benchmark — simply supported surrogate ONLY";
   caution.append(head);
   caution.append(text("w = "+f(w,3)+" kN/m, L = "+f(L,3)+" m. If (contrary to the actual multistorey frame) this isolated member were pin supported under only its uniform wall load: R_i = R_j = wL/2 = "+f(w*L/2,4)+" kN; M_max = wL²/8 = "+f(w*L*L/8,4)+" kN·m. These are NOT ETABS21 signed beam end actions, design combinations or reinforcement demand."));
   loads.append(caution);
  }
 }
}
function summary(){
 const rows=$("r68-floor-rows");rows.replaceChildren();
 for(const level of ["GF","FF","TF"]){
  const v=model.level_summary[level];const tr=document.createElement("tr");
  for(const val of [level,v.source_structural_beam_count,v.source_structural_column_count,v.source_floor_shell_count,
    f(v.source_floor_projected_area_m2,3)+" m²",f(v.source_frame_gross_concrete_m3,3)+" m³",
    f(v.source_mass_eligible_applied_gravity_kN,3)+" kN"]){
    const td=document.createElement("td");td.textContent=val;tr.append(td);
  }rows.append(tr);
 }
 const k=$("r68-kpis");k.replaceChildren();
 for(const [name,value] of [
  ["Native E2K points",model.source?Object.keys(model.points_xyz_local_mm).length:0],
  ["Frame assignments",model.members.length],
  ["Area assignments",model.shells.length],
  ["Assigned gravity records",model.members.reduce((n,m)=>n+m.applied_loads.length,0)+model.shells.reduce((n,m)=>n+m.applied_loads.length,0)],
  ["Source-applied participating load",f(model.reconciled_source_applied_mass_eligible_loads_kN,2)+" kN"]]){
  const card=text("","r68-kpi");const sm=document.createElement("small"),strong=document.createElement("strong");
  sm.textContent=name;strong.textContent=value;card.append(sm,strong);k.append(card);
 }
}
function render(){if(!model)return;const m=selected();if(!m)return;plan();scene();panelDetail(m);}
function init(d){
 if(d.schema!=="jp.structural.r6p8.native_input_member_calculation_book.v0.1" ||
 !d.source?.same_native_uls_sls_geometry_and_applied_gravity_assignments ||
 d.result_scope.engineering_approval!==false || d.result_scope.F3_one_way_shear_unsafe!==true ||
 d.members?.length!==199 || d.shells?.length!==115 || Object.keys(d.points_xyz_local_mm||{}).length!==127)
  throw Error("Source model is absent or unexpectedly changed; stop.");
 model=d;summary();fillSelect();render();
 $("r68-storey").addEventListener("change",()=>{viewLevel=$("r68-storey").value;fillSelect();render();});
 $("r68-category").addEventListener("change",()=>{kind=$("r68-category").value;fillSelect();render();});
 $("r68-id").addEventListener("change",()=>{chosen=$("r68-id").value;render();});
 for(const [button,delta] of [["r68-prev",-1],["r68-next",1]])$(button).addEventListener("click",()=>{
  const sel=$("r68-id"),index=sel.selectedIndex,next=(index+delta+sel.options.length)%sel.options.length;
  if(next>=0){sel.selectedIndex=next;chosen=sel.value;render();}
 });
 $("r68-turn-left").addEventListener("click",()=>{yaw-=Math.PI/10;scene();});
 $("r68-turn-right").addEventListener("click",()=>{yaw+=Math.PI/10;scene();});
 $("r68-fit").addEventListener("click",()=>{yaw=-.68;scene();});
}
fetch("data/r6p8-etabs21-source-member-catalogue.json",{cache:"no-store"})
 .then(r=>r.ok?r.json():Promise.reject(Error("Source catalogue not deployed")))
 .then(init).catch(err=>{
  $("r68-member-name").textContent="Native source catalogue unavailable";
  $("r68-numeric-input").textContent=err.message;
  $("r68-kpis").textContent="The ETABS21-derived source database failed its readback. No calculations were fabricated.";
 });
})();
