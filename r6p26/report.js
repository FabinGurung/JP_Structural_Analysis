"use strict";
(()=>{
  const $=id=>document.getElementById(id), ns="http://www.w3.org/2000/svg";
  let data=null, selectedCase="DL", floor="ALL", focused=null;
  function f(x,p=3){return typeof x==="number"&&Number.isFinite(x)?
      x.toLocaleString(undefined,{maximumFractionDigits:p}):"—";}
  function node(tag,attrs,parent){
    const n=document.createElementNS(ns,tag);
    Object.entries(attrs||{}).forEach(([k,v])=>n.setAttribute(k,String(v)));
    (parent||$("frame-visual")).appendChild(n);return n;
  }
  function trow(target,values,click){
    let tr=document.createElement("tr");
    for(const value of values){let c=document.createElement("td");c.textContent=String(value);tr.appendChild(c);}
    if(click){tr.addEventListener("click",click);tr.setAttribute("tabindex","0");
      tr.setAttribute("role","button");tr.addEventListener("keydown",e=>{
        if(e.key==="Enter"||e.key===" "){e.preventDefault();click();}
      });}
    target.appendChild(tr);
  }
  function current(){return data.cases[selectedCase];}
  function pick(member){
    focused=member.id;
    document.querySelectorAll(".frame-column,.frame-beam").forEach(el=>{
      el.classList.toggle("frame-highlight",el.dataset.id===focused);
    });
    const forces=current().signed_local_member_forces.find(x=>x.id===focused);
    $("selected-element").textContent=member.id+" · "+member.floor;
    const lines=[
      "Element: "+member.type.toUpperCase()+" · source/candidate ID "+member.id,
      "I: "+member.ni+"     J: "+member.nj,
      "Geometry: "+member.geometry_status,
      "Original DXF handles: "+(member.source_DXF_handles||[]).join(", "),
      "Nearest-column source gaps: "+(member.assumed_joint_gaps_m||[]).map(x=>f(x,4)+"m").join(" / "),
      "CURRENT CASE "+selectedCase+" · signed LOCAL I/J member end actions",
      forces?
        "End I: "+Object.entries(forces.local_I_J.I).map(([k,v])=>k+"="+f(v,5)).join("  "):
        "No independent member action",
      forces?
        "End J: "+Object.entries(forces.local_I_J.J).map(([k,v])=>k+"="+f(v,5)).join("  "):
        "",
      "N / V in kN. M / T in kNm. Not member strength or reinforcement approval."
    ];
    $("member-detail").textContent=lines.join("\n");
  }
  function draw(){
    if(!data)return;
    const view=$("frame-visual"),nmap=new Map(data.source_nodes.map(n=>[n.id,n]));
    view.replaceChildren();
    const members=data.source_members.filter(m=>floor==="ALL"||m.floor===floor);
    const corners=data.source_nodes.filter(n=>floor==="ALL"||n.floor===floor||
        (floor==="GF"&&n.floor==="B"));
    const project=n=>[(n.x_m-n.y_m)*.88, (n.x_m+n.y_m)*.36 - n.z_m*1.65];
    const corners2=corners.map(project);
    let xmin=Math.min(...corners2.map(a=>a[0])),xmax=Math.max(...corners2.map(a=>a[0]));
    let ymin=Math.min(...corners2.map(a=>a[1])),ymax=Math.max(...corners2.map(a=>a[1]));
    if(!Number.isFinite(xmin)){xmin=0;xmax=1;ymin=0;ymax=1;}
    const scale=Math.min(650/Math.max(1,xmax-xmin),340/Math.max(1,ymax-ymin));
    const xy=n=>{const [x,y]=project(n);return [35+(x-xmin)*scale,35+(y-ymin)*scale];};
    view.setAttribute("viewBox","0 0 720 430");
    view.setAttribute("aria-label","Narayani assumed 3D OpenSees frame model, "+floor+" level");
    members.sort((a,b)=>nmap.get(a.ni).z_m - nmap.get(b.ni).z_m);
    for(const member of members){
      const a=xy(nmap.get(member.ni)),b=xy(nmap.get(member.nj));
      const isCol=member.type==="column";
      const line=node("line",{
        x1:a[0],y1:a[1],x2:b[0],y2:b[1],
        class:(isCol?"frame-column":"frame-beam")+
              (member.provisional_level?" risky":"")+
              (focused===member.id?" frame-highlight":""),
        "data-id":member.id,"aria-hidden":"true"
      },view);
      node("title",{},line).textContent=member.id+" assumed structural member";
      const hit=node("line",{x1:a[0],y1:a[1],x2:b[0],y2:b[1],
        class:"member-hit",tabindex:"0",role:"button",
        "aria-label":"Inspect independently modeled "+member.id},view);
      hit.addEventListener("click",()=>pick(member));
      hit.addEventListener("keydown",e=>{if(e.key==="Enter"||e.key===" "){
        e.preventDefault();pick(member);
      }});
      hit.addEventListener("mouseenter",()=>line.classList.add("frame-highlight"));
      hit.addEventListener("mouseleave",()=>{if(focused!==member.id)line.classList.remove("frame-highlight");});
    }
    if($("show-labels").checked){
      for(const n of corners.filter(n=>n.floor==="GF")){
        const [x,y]=xy(n);
        let label=node("text",{x:x+4,y:y-3,class:"axis-mark"},view);
        label.textContent=n.column_axis;
      }
    }
  }
  function setCase(next){
    selectedCase=next;
    const c=current();
    $("current-case").textContent=next+" · "+(next.startsWith("P")?"non-code lateral probe":"gravity load");
    $("case-load").textContent=f(c.applied_6axis.Fz,3)+" kN";
    $("case-reaction").textContent=f(c.base_6axis.Fz,3)+" kN";
    $("case-equilibrium").textContent=c.max_6axis_equilibrium_residual.toExponential(2);
    let list=c.signed_local_member_forces.slice().sort(
      (a,b)=>b.max_abs_bending_kNm-a.max_abs_bending_kNm);
    $("case-moment").textContent=f(list[0]?.max_abs_bending_kNm)+" kNm";
    $("member-results").replaceChildren();
    list.slice(0,17).forEach((m,i)=>{
      trow($("member-results"),[i+1,m.id,m.type+" · "+m.floor,
        f(m.max_abs_axial_kN),f(m.max_abs_shear_kN),f(m.max_abs_bending_kNm)],
        ()=>{const source=data.source_members.find(x=>x.id===m.id);if(source)pick(source);});
    });
    $("displacement-results").replaceChildren();
    for(const v of c.floor_displacements)trow($("displacement-results"),
      [v.floor,f(v.max_abs_Ux_mm,5),f(v.max_abs_Uy_mm,5),f(v.max_abs_Uz_mm,5)]);
    $("base-results").replaceChildren();
    for(const v of c.base_support_reactions)trow($("base-results"),
      [v.axis,f(v.Fx_kN),f(v.Fy_kN),f(v.Fz_kN),f(v.Mx_kNm),f(v.My_kNm)]);
    if(focused){const x=data.source_members.find(m=>m.id===focused);if(x)pick(x);}
  }
  function setup(d){
    if(d.schema!=="jp.structural.r6p26.narayani_independent_frame_results.v0.1"||
       d.classification!=="UNVERIFIED_NARAYANI_FRAME_WITH_REAL_DXF_GF_COORDINATES_AND_ASSUMED_JOINTS"||
       d.professional_engineering_approval!==false || d.construction_release!==false ||
       d.original_F3_unsafe_status_retained!==true||
       d.model_counts.source_GF_columns!==23||
       d.model_counts.independent_3D_elastic_frame_scenarios!==4||
       d.gravity_conditions.wall_load_included!==false||
       d.member_design_checked!==false || d.seismic_code_design_performed!==false)
       throw Error("Unverified or unauthorized calculation data");
    data=d;
    document.querySelector('[data-field="columns"]').textContent=d.model_counts.source_GF_columns;
    document.querySelector('[data-field="cases"]').textContent=d.model_counts.independent_3D_elastic_frame_scenarios;
    document.querySelector('[data-field="members"]').textContent=d.source_members.length;
    const mx=Math.max(...Object.values(d.cases).map(c=>c.max_6axis_equilibrium_residual));
    document.querySelector('[data-field="eq"]').textContent=mx<1e-4?"PASS":"FAIL";
    $("source-strip-total").textContent=d.model_counts.source_candidate_beam_edges;
    $("modeled-beams").textContent=d.model_counts.model_accepted_beam_link_hypotheses;
    $("omitted-beams").textContent=d.model_counts.discarded_or_duplicate_beam_candidate_edges;
    $("source-digest").textContent=d.model_source_digest;
    $("floor-summary").replaceChildren();
    for(const q of d.floors)trow($("floor-summary"),[
      q.id,f(q.area_m2,2)+" m²",f(q.z_m,3)+" m · assumed"]);
    $("load-ledger").replaceChildren();
    const names={
      column_concrete_kN:["Column concrete self-weight","Geometry-derived + 20kN/m³"],
      beam_downstand_concrete_kN:["Beam concrete downstand","Provisional assumed 0.23×0.40m"],
      floor_slab_concrete_kN:["Slab concrete area proxy","Architectural area × 0.13m ×20"],
      floor_finish_kN:["Finishes area proxy","1.5kPa provisional"],
      room_imposed_kN:["Uniform room imposed proxy","2kPa from source report"],
      DL_total_kN:["Total DL applied (no walls)","Source + labelled assumptions"],
      LL_total_kN:["Total LL proxy","NOT occupancy-zone complete"],
      probe_lateral_x_kN:["Lateral probe PX10","NOT NBC seismic"],
      probe_lateral_y_kN:["Lateral probe PY10","NOT NBC seismic"]
    };
    for(const [k,label] of Object.entries(names)){
      const value=d.source_area_and_load_ledger[k];
      if(typeof value!=="number")continue;
      trow($("load-ledger"),[label[0],f(value,4),label[1]]);
    }
    $("open-holds").replaceChildren();
    for(const note of d.holds){
      const li=document.createElement("li");li.textContent=note;$("open-holds").append(li);
    }
    $("floor-select").addEventListener("change",()=>{floor=$("floor-select").value;draw();});
    $("case-select").addEventListener("change",()=>setCase($("case-select").value));
    $("show-labels").addEventListener("change",draw);
    draw();setCase("DL");
  }
  fetch("reports/r6p26/narayani-independent-frame-results.json",{cache:"no-store"}).then(r=>{
    if(!r.ok)throw Error("HTTP "+r.status);
    return r.json();
  }).then(setup).catch(e=>{
    const h=$("main");const n=document.createElement("div");n.className="warning";
    n.textContent="Numerical report unavailable: "+e.message;h.prepend(n);
  });
})();
