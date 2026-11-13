"use strict";
(function () {
  const d=document, ns="http://www.w3.org/2000/svg";
  const $=id=>d.getElementById(id);
  let data=null;
  let choice={floor:"1",mode:"FLEXIBLE_SHELL",case:"DL",selected:null};
  function fmt(v,n=4){return typeof v==="number"&&Number.isFinite(v)
    ?v.toLocaleString(undefined,{maximumFractionDigits:n}):"—";}
  function put(id,v){let el=$(id);if(el)el.textContent=String(v);}
  function element(tag,attrs,parent){
    const el=d.createElementNS(ns,tag);
    Object.entries(attrs||{}).forEach(([k,v])=>el.setAttribute(k,String(v)));
    if(parent)parent.appendChild(el);return el;
  }
  function infoSelection(run){
    const sel=choice.selected;
    if(!sel){put("selected-detail","Select a blue slab cell or purple beam to inspect signed OpenSees forces.");return;}
    if(sel.type==="beam"){
      const a=run.signed_frame_end_actions[sel.id];
      if(!a){put("selected-detail","No signed frame actions for this selection.");return;}
      const line=end=>Object.entries(a[end]).map(([k,v])=>k+" "+fmt(v,6)).join(" · ");
      put("selected-detail",sel.id+"\nLocal I: "+line("I")+"\nLocal J: "+line("J")+
        "\nSigned local end forces in kN and kNm; not a member-capacity verdict.");
    }else{
      const a=run.shell_nodal_resisting_force_vectors[sel.id]||[];
      put("selected-detail",sel.id+"\nShell area "+fmt(sel.area,4)+" m²\n"+
       a.map((x,i)=>"Component "+(i+1)+": "+fmt(x,5)).join(" · ")+
       "\n24 signed ShellMITC4 nodal components (6 per corner); not a reinforcement design.");
    }
  }
  function show(){
    if(!data)return;
    const t=data.topology,s=data.source_geometry,f=Number(choice.floor);
    const run=data.solutions[choice.mode][choice.case];
    const xs=s.x_grid_m,ys=s.y_grid_m,ylast=ys[ys.length-1];
    const plan=$("plan");plan.replaceChildren();
    const xmin=xs[0],ymin=ys[0],width=xs[xs.length-1]-xmin,height=ylast-ymin;
    plan.setAttribute("viewBox",(xmin-.55)+" -.55 "+(width+1.1)+" "+(height+1.1));
    plan.setAttribute("aria-label","3D shell FEM plan of floor "+f+", "+choice.mode+" / "+choice.case);
    const reverse=y=>ylast-y;
    for(const a of t.shell_cells.filter(p=>p.floor===f)){
      let rect=element("rect",{"class":"shell",x:xs[a.i],y:reverse(ys[a.j+1]),
        width:xs[a.i+1]-xs[a.i],height:ys[a.j+1]-ys[a.j]},plan);
      element("title",{},rect).textContent="Shell cell "+a.i+","+a.j;
      const select=()=>{choice.selected={type:"shell",
          id:"L"+f+":CELL:"+a.i+":"+a.j,area:a.area_m2};infoSelection(run);};
      rect.addEventListener("click",select);
      rect.setAttribute("tabindex","0");
      rect.setAttribute("role","button");
      rect.setAttribute("aria-label","Inspect shell cell "+a.i+","+a.j);
      rect.addEventListener("keydown",e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();select();}});
    }
    for(const [i,j] of t.removed_opening_cells[choice.floor]||[]){
      element("rect",{"class":"opening",x:xs[i],y:reverse(ys[j+1]),
        width:xs[i+1]-xs[i],height:ys[j+1]-ys[j]},plan);
      element("text",{"class":"txt","text-anchor":"middle",
        x:(xs[i]+xs[i+1])/2,y:reverse((ys[j]+ys[j+1])/2)},plan).textContent="VOID";
    }
    for(const b of t.beams.filter(p=>p.floor===f)){
      const a=b.a,c=b.b;
      const selected=choice.selected&&choice.selected.id===b.key;
      const line=element("line",{"class":"beam"+(selected?" selected":""),
        x1:xs[a[1]],y1:reverse(ys[a[2]]),x2:xs[c[1]],y2:reverse(ys[c[2]]),
        tabindex:"0",role:"button","aria-label":"Inspect beam "+b.key},plan);
      element("title",{},line).textContent=b.key;
      const select=()=>{choice.selected={type:"beam",id:b.key};show();};
      line.addEventListener("click",select);
      line.addEventListener("keydown",e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();select();}});
    }
    for(const a of t.columns.filter(p=>p.floor===f)){
      const k=a.b;
      element("circle",{"class":"column",cx:xs[k[1]],cy:reverse(ys[k[2]]),r:.08},plan);
    }
    put("floor-area",fmt(t.floor_areas_m2[choice.floor],2)+" m²");
    put("gravity",fmt(run.gravity_resultants.Fz_kN,3)+" kN");
    put("six-residual",fmt(run.max_equilibrium_residual,10));
    put("vertical-deflection",fmt(1000*(run.floor_max_vertical_displacement_m[choice.floor]||0),5)+" mm");
    put("xbeam",fmt(run.shell_to_beam_directional_vz_abs_sum.X,4)+" kN");
    put("ybeam",fmt(run.shell_to_beam_directional_vz_abs_sum.Y,4)+" kN");
    $("support-body").replaceChildren(...Object.entries(run.support_reactions).map(([node,r])=>{
      let tr=d.createElement("tr");
      [node,fmt(r.Fz,4),fmt(r.Mx,4),fmt(r.My,4)].forEach(v=>{
        let td=d.createElement("td");td.textContent=v;tr.append(td);
      });return tr;
    }));
    infoSelection(run);
  }
  function setup(result){
    if(result.schema!=="jp.structural.r6p24.pages_independent_shell_preview.v0.1"||
       result.classification!=="SYNTHETIC_REFERENCE"||
       result.engineering_approval!==false||result.mesh_screen.engineering_approval!==false||
       result.historical_F3_unsafe_retained!==true)
      throw Error("Unapproved or unknown FE source data not admitted");
    data=result;
    Object.keys(data.topology.floor_areas_m2).forEach(v=>
      $("floor").add(new Option("Floor "+v,v)));
    Object.keys(data.solutions).forEach(v=>
      $("mode").add(new Option(v==="FLEXIBLE_SHELL"?"Flexible shell":"Rigid in-plane diaphragm",v)));
    data.cases.forEach(v=>$("case").add(new Option(v,v)));
    put("source-hash",data.source_SHA256);
    put("shell-count",data.topology.shell_count);
    put("dead-load",fmt(data.source_ledger.gravity_totals_kN.DL,2)+" kN");
    put("live-load",fmt(data.source_ledger.gravity_totals_kN.LL,2)+" kN");
    put("opening-count",Object.values(data.topology.removed_opening_cells).reduce((a,b)=>a+b.length,0));
    $("convergence-body").replaceChildren(...data.mesh_screen.comparisons.map(x=>{
      let tr=d.createElement("tr");
      const pass=x.relative_displacement_five_percent_screen_passed&&x.base_reaction_five_percent_screen_passed;
      [x.mode==="FLEXIBLE_SHELL"?"Flexible":"Rigid",x.case,
        fmt(100*x.max_response_difference_over_response_peak,2)+"%",
        fmt(100*x.max_base_Fz_difference_over_total_vertical_action,2)+"%",
        pass?"5% screen met":"Finer study required"].forEach(v=>{
        let td=d.createElement("td");td.textContent=v;tr.append(td);
      });return tr;
    }));
    for(const [field,key] of [["floor","floor"],["mode","mode"],["case","case"]]){
      $(field).addEventListener("change",()=>{
        choice[key]=$(field).value;choice.selected=null;show();
      });
    }
    put("load-status","Synthetic OpenSees calculations verified");
    show();
  }
  fetch("data/r6p23-preview.json",{cache:"no-store"}).then(r=>{
    if(!r.ok)throw Error("HTTP "+r.status);
    return r.json();
  }).then(setup).catch(err=>put("load-status","Numerical data unavailable: "+err.message));
})();
