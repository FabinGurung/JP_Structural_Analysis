/* R6.9: source-verified, bounded OpenSees frame-only gravity result viewer.
 * Not full ETABS21 design, not a source modal or diaphragm solution.
 */
(()=>{"use strict";
const get=id=>document.getElementById(id);
let model=null,source=null,role="ULS",current="GF:B46";
const fmt=(a,n=3)=>Number.isFinite(Number(a))?Number(a).toLocaleString("en-US",{minimumFractionDigits:n,maximumFractionDigits:n}):"—";
const div=(cls,content)=>{const x=document.createElement("div");x.className=cls;if(content!==undefined)x.textContent=content;return x;};
function metric(name,val){const outer=div("r69-metric");outer.append(div("",""));outer.firstChild.remove();
 const a=document.createElement("small");a.textContent=name;const b=document.createElement("b");b.textContent=val;outer.append(a,b);return outer;
}
function itemRows(parent,items){parent.replaceChildren();for(const [name,value] of items){const el=div("r69-line");
 const strong=document.createElement("strong");strong.textContent=name;el.append(strong,div("",value));parent.append(el);}}
function cases(){return model?.roles?.[role]??null;}
function member(){
 const s=cases();const sel=get("r69-member");sel.replaceChildren();
 const names=Object.keys(s?.actual_source_member_end_actions_bounded_only||{}).sort((a,b)=>a.localeCompare(b,undefined,{numeric:true}));
 for(const name of names){const opt=document.createElement("option");opt.value=name;opt.textContent=name;sel.append(opt);}
 if(!names.includes(current))current=names[0]||"";if(current)sel.value=current;
}
function sourceRecord(){return source?.members?.find(v=>v.key===current)||null;}
function choose(name){const memberSource=sourceRecord();current=name;get("r69-member").value=name;renderMember();}
function draw(values){
 const svg=get("r69-forces");
 const ns="http://www.w3.org/2000/svg";
 const node=(tag,attrs={},content)=>{const x=document.createElementNS(ns,tag);for(const [k,v] of Object.entries(attrs))x.setAttribute(k,String(v));if(content!==undefined)x.textContent=content;return x;};
 svg.replaceChildren(node("rect",{x:1,y:1,width:758,height:438,rx:11,fill:"#f9fcfd"}));
 if(!values?.length)return;
 // Forces N,V and moments T,M have distinct scales, never compare kg to m.
 for(const [g,head,offset] of [[0,"Forces · kN",30],[1,"Moments · kN·m",237]]){
  const ids=g?[3,4,5,9,10,11]:[0,1,2,6,7,8];
  const max=Math.max(...ids.map(i=>Math.abs(values[i])),1e-8);
  svg.append(node("text",{x:21,y:offset,fill:"#2a5168","font-size":"15","font-weight":"650"},head));
  svg.append(node("line",{x1:370,y1:offset+10,x2:370,y2:offset+180,stroke:"#8a9ca7","stroke-width":1.4}));
  ids.forEach((i,j)=>{
   const value=values[i],y=offset+31+j*25;
   const length=Math.abs(value)/max*230,x=value>=0?370:370-length;
   const rect=node("rect",{x,y:y-9,width:Math.max(length,.6),height:13,
      fill:value>=0?"#3984ad":"#cc7062",rx:2});
   svg.append(rect);
   svg.append(node("text",{x:16,y:y+2,fill:"#486375","font-size":"12"},
      (g?["Ti","Myi","Mzi","Tj","Myj","Mzj"]:["Ni","Vyi","Vzi","Nj","Vyj","Vzj"])[j]));
   svg.append(node("text",{x:value>=0?Math.min(608,375+length+5):Math.max(90,365-length-60),
      y:y+2,fill:"#345971","font-size":"12"},fmt(value,2)));
  });
  svg.append(node("text",{x:650,y:offset+170,fill:"#6b7f8d","font-size":"10"},"max |value| = "+fmt(max,2)));
 }
}
function renderMember(){
 const a=cases(),values=a?.actual_source_member_end_actions_bounded_only?.[current];
 const m=source?.members?.find(v=>v.key===current);
 get("r69-label").textContent=current+" · "+(m?.section||"Original source section");
 if(!values){get("r69-method").textContent="No solved bounded end actions for this member.";return;}
 const sourceUniform=m?.applied_loads?.filter(x=>x.pattern==="WALL LOAD"&&x.method==="U")??[];
 get("r69-method").textContent="Member geometry from native ETABS21: "+(m?.kind??"frame")+
  " · L="+fmt((m?.length_mm??0)/1000,4)+"m · concrete "+(m?.section??"")+
  ". OpenSees computed local end actions for supported frame-only WALL LOAD subset (not a full-source model). "+
  (sourceUniform.length?"This beam has original applied w="+fmt(sourceUniform[0]?.working?.w_N_per_mm,3)+" N/mm.":"This member receives only indirect actions through the incomplete supported frame subset.");
 const labels=["N","Vy","Vz","T","My","Mz"],units=["kN","kN","kN","kN·m","kN·m","kN·m"];
 for(const [id,start] of [["r69-end-i",0],["r69-end-j",6]]){
  const parent=get(id);parent.replaceChildren();
  for(let i=0;i<6;i++){
   const row=div("r69-action-row");
   const key=document.createElement("span");key.textContent=labels[i];
   const value=document.createElement("strong");value.textContent=fmt(values[start+i],4)+" "+units[i];
   row.append(key,value);parent.append(row);
  }
 }
 draw(values);
 const holder=get("r69-source-link");holder.replaceChildren();
 const link=document.createElement("a");link.href="etabs21-member-book.html?member="+encodeURIComponent(current);
 link.textContent="Inspect source coordinates, dimensions and assigned load equations for "+current;
 holder.append(link);
}
function render(){
 const d=cases(),cov=model.coverage;if(!d)return;
 get("r69-state").textContent="SOURCE BOUNDED · "+role+" STIFFNESS ONLY";
 const metrics=get("r69-metrics");metrics.replaceChildren(
  metric("Original concrete members",cov.original_frame_elements),
  metric("Supported frame elements solved",d.solved_elements),
  metric("Uniform source wall loads",cov.direct_uniform_wall_beam_loads_included+" of "+cov.source_wall_load_records),
  metric("Frame gravity reaction",fmt(d.reconstructed_base_reaction_kN[2],3)+" kN"),
  metric("Equilibrium residual",fmt(d.reaction_vertical_residual_N,5)+" N")
 );
 itemRows(get("r69-reactions"),[
  ["Applied wall load",fmt(d.applied_vertical_load_kN,6)+" kN downward"],
  ["Calculated summed Rz",fmt(d.reconstructed_base_reaction_kN[2],6)+" kN upward"],
  ["Equilibrium residual",fmt(d.reaction_vertical_residual_N,6)+" N"],
  ["Max node translation",fmt(d.maximum_nodal_translation_mm,5)+" mm, incomplete frame subset"],
  ["Active frame source stiffness",role+" I2/I3 modifiers from authenticated ETABS 21 "+role+" file"]
 ]);
 itemRows(get("r69-holds"),[
  ["Unsupported original frame islands",cov.unanchored_islands+" / "+cov.frame_components+" components; "+cov.unsupported_island_nodes+" original points"],
  ["Withheld original concrete member segments",cov.source_frame_elements_withheld_without_support],
  ["Unsectioned loaded lines deferred",cov.unsectioned_loaded_line_records_deferred],
  ["Partial span or unsupported BEAM wall-load rows",cov.direct_beam_wall_loads_deferred],
  ["Full area shells not transferred",cov.original_shell_assignments],
  ["Source rigid diaphragms not imposed",cov.original_rigid_diaphragm_point_assignments],
  ["Original structural selfweight","NOT included in bounded solved case"],
  ["Original full ETABS solver verification","NOT completed"],
  ["Footing F3 one-way shear","UNSAFE per historical source report"]
 ]);
 member();renderMember();
}
function init(d,s){
 if(d.schema!=="jp.structural.r6p9.bounded_source_openSees_results.v0.1"||
 d.coverage.unanchored_islands!==4||d.coverage.direct_uniform_wall_beam_loads_included!==70||
 d.coverage.F3_one_way_shear_unsafe!==true||d.professional_engineering_approval!==false||
 d.roles.ULS.status!=="SOURCE_NATIVE_BOUNDED_GRAVITY_FRAME_NUMERICALLY_SOLVED"||
 d.roles.SLS.status!=="SOURCE_NATIVE_BOUNDED_GRAVITY_FRAME_NUMERICALLY_SOLVED"||
 s.schema!=="jp.structural.r6p8.native_input_member_calculation_book.v0.1")
 throw Error("Expected verified bounded source solver and native member catalogue are unavailable");
 model=d;source=s;render();
 get("r69-role").addEventListener("change",()=>{role=get("r69-role").value;render();});
 get("r69-member").addEventListener("change",()=>{current=get("r69-member").value;renderMember();});
 for(const [id,dir] of [["r69-prev",-1],["r69-next",1]]){
  get(id).addEventListener("click",()=>{
    const sel=get("r69-member");
    if(!sel.options.length)return;
    sel.selectedIndex=(sel.selectedIndex+dir+sel.options.length)%sel.options.length;
    current=sel.value;renderMember();
  });
 }
}
Promise.all([
 fetch("data/r6p9-etabs21-bounded-frame-solver.json",{cache:"no-store"}).then(r=>r.ok?r.json():Promise.reject(new Error("Solver result missing"))),
 fetch("data/r6p8-etabs21-source-member-catalogue.json",{cache:"no-store"}).then(r=>r.ok?r.json():Promise.reject(new Error("Native source catalogue missing")))
]).then(([a,b])=>init(a,b)).catch(err=>{
 get("r69-metrics").textContent="R6.9 solver output unavailable: "+err.message;
 get("r69-label").textContent="No verified solved case to display";
 get("r69-method").textContent="No member forces are shown until both source input and solver residual checks are available.";
});
})();
