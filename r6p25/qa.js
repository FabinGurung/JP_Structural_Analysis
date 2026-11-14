"use strict";
(function(){
  const ns="http://www.w3.org/2000/svg", d=document, $=id=>d.getElementById(id);
  let model=null, floor="GF", filter="all";
  let selection=null;
  const fmt=(n,places=2)=>typeof n==="number"&&Number.isFinite(n)?
      n.toLocaleString(undefined,{minimumFractionDigits:0,maximumFractionDigits:places}):"—";
  function svg(tag,attrs,parent){
    const el=d.createElementNS(ns,tag);
    Object.entries(attrs||{}).forEach(([k,v])=>el.setAttribute(k,String(v)));
    (parent||$("plan")).appendChild(el);return el;
  }
  function choose(item){
    selection=item;const name=item.source_axis||item.family||item.id;
    $("selection-heading").textContent=name+" · "+item.id;
    let detail;
    if(item.type==="column"){
      detail="SOURCE: original ground-floor DXF column marker.\n"+
      "Grid: "+item.source_axis+" · family "+item.family+"\n"+
      "CAD handle: "+item.original_DXF_handle+"\n"+
      "Footing handle: "+item.footing_DXF_handle+"\n"+
      "Relative GF position: ("+fmt(item.x,3)+", "+fmt(item.y,3)+") m.\n"+
      "UPPER GF→FF→SF→ROOF: 3-storey continuation is ASSUMED; no signed vertical support or reinforcement continuity.\n"+
      (item.i3_exception?"WARNING: original source I4 is different from owner working I3 in an unregistered coordinate frame. ":"")+
      "Rigid RC moment joint is a model hypothesis; no connection design verification.";
    }else if(item.type==="footing"){
      detail="SOURCE: original ground-floor DXF footing outline.\n"+
      "Type: "+item.family+" · drawing handle "+item.handle+"\n"+
      "Plan dimensions: "+fmt(item.width_m,3)+" × "+fmt(item.depth_m,3)+" m.\n"+
      "Original associated column marks: "+item.source_columns.join(", ")+".\n"+
      "160 kPa is a provisional scenario, NOT a checked soil bearing, overturning, shear, punching or foundation design.";
    }else{
      const joints=item.assumed_endpoint_joints;
      detail="SOURCE: "+item.source_type+"\n"+
      "Original DXF line handles: "+item.original_DXF_handles.join(" / ")+"\n"+
      (item.nearest_annotation_HANDLE_proximity_only?"Nearest text handle (proximity only): "+item.nearest_annotation_HANDLE_proximity_only+"\n":"")+
      "End I candidate → "+joints[0].column_axis+
      " ("+fmt(joints[0].distance_m,3)+" m; "+(joints[0].plan_near_750mm?"near":"HIGH GAP")+")\n"+
      "End J candidate → "+joints[1].column_axis+
      " ("+fmt(joints[1].distance_m,3)+" m; "+(joints[1].plan_near_750mm?"near":"HIGH GAP")+")\n"+
      "STATUS: assumed endpoints for source drawing QA ONLY. These are NOT verified beam support constraints, span sections, bending connections or a solved OpenSees load path.";
    }
    $("selection").textContent=detail;
  }
  const colById=()=>new Map(model.columns.map(c=>[c.id,c]));
  function render(){
    if(!model)return;
    const svgRoot=$("plan");svgRoot.replaceChildren();selection=null;
    const members=model.beams.filter(b=>b.level===floor &&
      (filter==="all"|| (b.assumed_endpoint_joints.some(j=>!j.plan_near_750mm))===(filter==="gap")));
    const bounds=[...model.columns.map(x=>[x.x,x.y]),
      ...members.flatMap(b=>b.endpoints),...model.footings.map(f=>[f.x,f.y])];
    const xmin=Math.min(...bounds.map(x=>x[0]))-1.7;
    const xmax=Math.max(...bounds.map(x=>x[0]))+1.7;
    const ymin=Math.min(...bounds.map(x=>x[1]))-1.7;
    const ymax=Math.max(...bounds.map(x=>x[1]))+1.7;
    const width=xmax-xmin,height=ymax-ymin;
    svgRoot.setAttribute("viewBox",xmin+" "+(-ymax)+" "+width+" "+height);
    svgRoot.setAttribute("aria-label",floor+" source drawing with 23 assumed vertical columns and "+members.length+" candidate strips");
    const yy=y=>-y;
    for(let n=Math.ceil(xmin);n<=xmax;n+=2){
      svg("line",{class:"grid-line",x1:n,y1:-ymax,x2:n,y2:-ymin});
    }
    for(let n=Math.ceil(ymin);n<=ymax;n+=2){
      svg("line",{class:"grid-line",x1:xmin,y1:yy(n),x2:xmax,y2:yy(n)});
    }
    if($("show-footings").checked&&floor==="GF"){
      for(const f of model.footings){
        const rect=svg("rect",{class:"found",x:f.x-f.width_m/2,
          y:yy(f.y+f.depth_m/2),width:f.width_m,height:f.depth_m,
          tabindex:0,role:"button","aria-label":"Inspect footing "+f.id});
        svg("title",{},rect).textContent=f.id+" "+f.family;
        rect.addEventListener("click",()=>choose({...f,type:"footing"}));
        rect.addEventListener("keydown",e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();choose({...f,type:"footing"});}});
      }
    }
    if($("show-ties").checked){
      const cols=colById();
      for(const b of members){
        b.endpoints.forEach(([x,y],i)=>{
          const j=b.assumed_endpoint_joints[i], c=cols.get(j.column_id);
          if(!c)return;
          svg("line",{class:"joint-tie"+(j.plan_near_750mm?"":" high"),x1:x,y1:yy(y),x2:c.x,y2:yy(c.y)});
        });
      }
    }
    for(const b of members){
      const risky=b.assumed_endpoint_joints.some(j=>!j.plan_near_750mm);
      const line=svg("line",{class:"beam"+(floor==="GF"?"":" upper")+(risky?" risky":""),
        x1:b.endpoints[0][0],y1:yy(b.endpoints[0][1]),
        x2:b.endpoints[1][0],y2:yy(b.endpoints[1][1]),
        tabindex:0,role:"button","aria-label":"Inspect source candidate "+b.id});
      svg("title",{},line).textContent=b.id+" · "+(risky?"high-gap":"near")+" source";
      line.addEventListener("click",()=>choose({...b,type:"beam"}));
      line.addEventListener("keydown",e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();choose({...b,type:"beam"});}});
    }
    for(const c of model.columns){
      const circle=svg("circle",{class:"column-mark",cx:c.x,cy:yy(c.y),r:.19,role:"button",tabindex:0,
        "aria-label":"Inspect source column "+c.source_axis});
      svg("title",{},circle).textContent="Original column "+c.source_axis+" · assumed vertical";
      circle.addEventListener("click",()=>choose({...c,type:"column"}));
      circle.addEventListener("keydown",e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();choose({...c,type:"column"});}});
      svg("text",{class:"mark-label",x:c.x+.23,y:yy(c.y)-.24},svgRoot).textContent=c.source_axis;
    }
    const info=model.floors.find(x=>x.id===floor);
    $("level-label").textContent=info.name+" (source candidate)";
    $("level-beams").textContent=fmt(members.length,0)+" / "+
      model.beams.filter(x=>x.level===floor).length;
    $("level-area").textContent=fmt(info.architectural_reported_area_m2)+" m² · architectural area only";
    $("selection-heading").textContent="Choose a source element";
    $("selection").textContent="Tap a beam, column or footing to inspect its original drawing handles, nearest-column gap distances and the specific assumption. No building FE forces are calculated here.";
    renderTable(members);
  }
  function renderTable(beams){
    const rows=beams.slice().sort((a,b)=>{
      const distance=x=>Math.max(...x.assumed_endpoint_joints.map(j=>j.distance_m));
      return distance(b)-distance(a);
    });
    $("gaps").replaceChildren(...rows.map(x=>{
      const row=d.createElement("tr");
      const joints=x.assumed_endpoint_joints;
      const risk=joints.some(j=>!j.plan_near_750mm);
      for(const val of [x.id,...joints.map(j=>j.column_axis+" · "+fmt(j.distance_m,2)+"m"),risk?"HIGH GAP — REVIEW":"Near-column hypothesis"]){
        const cell=d.createElement("td");cell.textContent=val;
        if(val==="HIGH GAP — REVIEW")cell.className="gap-high";
        if(val==="Near-column hypothesis")cell.className="gap-low";
        row.appendChild(cell);
      }
      row.addEventListener("click",()=>choose({...x,type:"beam"}));
      return row;
    }));
  }
  function setup(data){
    if(data.schema!=="jp.structural.r6p25.narayani_assumed_connections_public_qa.v0.1" ||
       data.classification!=="ORIGINAL_DXF_SOURCE_DERIVED_WITH_ASSUMED_UNVERIFIED_CONNECTIONS" ||
       data.engineering_approval!==false||data.actual_independent_FE_run!==false ||
       data.summary.source_GF_column_marks!==23||data.summary.source_footing_outlines!==21 ||
       data.summary.total_candidate_beam_segments!==66 ||
       data.basis.concrete_unit_weight_kN_m3!==20||data.basis.seismic_code!=="NBC 105:2025")
      throw Error("Unrecognized or unapproved source data / schema");
    model=data;
    $("source-sha").textContent=data.cad_source_sha;
    $("ncols").textContent=data.columns.length;
    $("nfoot").textContent=data.footings.length;
    $("nbeams").textContent="32 · 17 · 17";
    $("ngaps").textContent=data.summary.high_gap_endpoint_hypotheses;
    for(const id of ["floor","scope","show-ties","show-footings"])$(id).disabled=false;
    $("floor").addEventListener("change",()=>{floor=$("floor").value;render();});
    $("scope").addEventListener("change",()=>{filter=$("scope").value;render();});
    for(const id of ["show-ties","show-footings"])$(id).addEventListener("change",render);
    $("load-state").textContent="Pinned CAD source · assumed connections visible";
    render();
  }
  fetch("data/r6p25-narayani-qa.json",{cache:"no-store"}).then(r=>{
    if(!r.ok)throw Error("HTTP "+r.status);
    return r.json();
  }).then(setup).catch(err=>{$("load-state").textContent="Source data error: "+err.message;});
})();
