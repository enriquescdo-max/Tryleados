import { useState, useRef, useCallback, useEffect } from "react";

const API = "https://tryleados-production.up.railway.app";

const FORMAT_META = {
  wall_of_text: { label: "WALL OF TEXT", color: "#E05A1A", emoji: "📄" },
  slideshow:    { label: "SLIDESHOW",    color: "#3B82F6", emoji: "🖼️" },
  green_screen: { label: "GREEN SCREEN", color: "#10B981", emoji: "🟩" },
  hook_demo:    { label: "HOOK + DEMO",  color: "#8B5CF6", emoji: "🎬" },
};
const PLATFORM_META = {
  tiktok:    { label: "TikTok",    color: "#ff0050" },
  instagram: { label: "Instagram", color: "#C13584" },
  youtube:   { label: "YouTube",   color: "#FF0000" },
};

function fmtV(n) { return n>=1e6?`${(n/1e6).toFixed(1)}M`:n>=1e3?`${(n/1e3).toFixed(0)}K`:String(n||0); }
function sratio(s,l) { return l?`${((s/l)*100).toFixed(1)}%`:"0%"; }

function parseScript(raw) {
  if (!raw) return { body: "", cta: "" };
  const clean = raw.replace(/```json/g,"").replace(/```/g,"").trim();
  try {
    const p = JSON.parse(clean);
    return { body: p.script_body || raw, cta: p.cta || "" };
  } catch { return { body: raw, cta: "" }; }
}

function SwipeCard({ script, onApprove, onReject, isTop }) {
  const startX=useRef(0), isDragging=useRef(false);
  const [offset, setOffset] = useState({x:0,y:0});
  const [drag, setDrag] = useState(false);
  const fmt = FORMAT_META[script.format_type]||FORMAT_META.wall_of_text;
  const plt = PLATFORM_META[script.viral_hooks?.platform]||PLATFORM_META.tiktok;
  const h = script.viral_hooks||{};
  const { body, cta } = parseScript(script.script_body);
  const aOp = Math.min(Math.max(offset.x/80,0),1);
  const rOp = Math.min(Math.max(-offset.x/80,0),1);

  const onMD = e => { if(!isTop) return; isDragging.current=true; startX.current=e.clientX; setDrag(true); };
  const onMM = useCallback(e => { if(!isDragging.current) return; setOffset({x:e.clientX-startX.current,y:0}); },[]);
  const onMU = useCallback(() => {
    if(!isDragging.current) return; isDragging.current=false; setDrag(false);
    if(offset.x>80) onApprove(); else if(offset.x<-80) onReject(); else setOffset({x:0,y:0});
  },[offset.x,onApprove,onReject]);

  useEffect(()=>{ window.addEventListener("mousemove",onMM); window.addEventListener("mouseup",onMU);
    return()=>{ window.removeEventListener("mousemove",onMM); window.removeEventListener("mouseup",onMU); }; },[onMM,onMU]);

  return (
    <div onMouseDown={onMD} style={{
      position:"absolute",width:"100%",maxWidth:420,
      background:"linear-gradient(145deg,#111214,#0d0f11)",
      border:"1px solid #1e2126",borderRadius:18,overflow:"hidden",
      cursor:isTop?(drag?"grabbing":"grab"):"default",
      transform:`translate(${offset.x}px,${offset.y}px) rotate(${(offset.x/300)*12}deg)`,
      transition:drag?"none":"transform 0.35s cubic-bezier(0.25,0.46,0.45,0.94)",
      userSelect:"none",boxShadow:isTop?"0 24px 64px rgba(0,0,0,0.6)":"0 8px 24px rgba(0,0,0,0.4)",
    }}>
      <div style={{position:"absolute",inset:0,borderRadius:18,zIndex:10,pointerEvents:"none",
        background:`rgba(16,185,129,${aOp*0.15})`,border:`2px solid rgba(16,185,129,${aOp})`,
        display:"flex",alignItems:"center",paddingLeft:24}}>
        <span style={{fontSize:32,opacity:aOp,fontWeight:900,color:"#10B981"}}>✓ APPROVE</span>
      </div>
      <div style={{position:"absolute",inset:0,borderRadius:18,zIndex:10,pointerEvents:"none",
        background:`rgba(239,68,68,${rOp*0.15})`,border:`2px solid rgba(239,68,68,${rOp})`,
        display:"flex",alignItems:"center",justifyContent:"flex-end",paddingRight:24}}>
        <span style={{fontSize:32,opacity:rOp,fontWeight:900,color:"#EF4444"}}>✕ SKIP</span>
      </div>
      <div style={{padding:"18px 20px 14px",borderBottom:"1px solid #1a1d22"}}>
        <div style={{display:"flex",justifyContent:"space-between",alignItems:"flex-start"}}>
          <div style={{display:"flex",gap:6,flexWrap:"wrap"}}>
            <span style={{background:fmt.color+"22",color:fmt.color,fontSize:9,fontWeight:700,letterSpacing:"0.12em",padding:"3px 8px",borderRadius:5,border:`1px solid ${fmt.color}44`}}>{fmt.emoji} {fmt.label}</span>
            <span style={{background:plt.color+"22",color:plt.color,fontSize:9,fontWeight:700,letterSpacing:"0.12em",padding:"3px 8px",borderRadius:5,border:`1px solid ${plt.color}44`}}>{plt.label.toUpperCase()}</span>
          </div>
          <div style={{textAlign:"right"}}>
            <div style={{fontSize:18,fontWeight:800,color:"#fff"}}>{fmtV(h.view_count)}</div>
            <div style={{fontSize:9,color:"#4a5568"}}>VIEWS</div>
          </div>
        </div>
        <div style={{marginTop:10,padding:"8px 12px",background:"#0a0c0f",borderRadius:7,border:"1px solid #1a1d22"}}>
          <div style={{fontSize:9,color:"#4a5568",marginBottom:3}}>VIRAL SOURCE HOOK</div>
          <div style={{fontSize:11,color:"#6b7280",fontStyle:"italic",lineHeight:1.5}}>"{h.hook_text}"</div>
        </div>
        <div style={{display:"flex",gap:14,marginTop:8}}>
          <div><span style={{fontSize:9,color:"#4a5568"}}>SHARES </span><span style={{fontSize:9,color:"#9ca3af",fontWeight:600}}>{fmtV(h.share_count)}</span></div>
          <div><span style={{fontSize:9,color:"#4a5568"}}>RATIO </span><span style={{fontSize:9,color:"#10B981",fontWeight:700}}>{sratio(h.share_count,h.like_count)}</span></div>
        </div>
      </div>
      <div style={{padding:"16px 20px"}}>
        <div style={{fontSize:9,color:"#4a5568",letterSpacing:"0.12em",marginBottom:10}}>AI-REMIXED SCRIPT</div>
        <div style={{fontSize:12,color:"#d1d5db",lineHeight:1.8,whiteSpace:"pre-line",maxHeight:180,overflowY:"auto"}}>{body}</div>
        {cta && <div style={{marginTop:14,padding:"10px 12px",background:"#E05A1A11",borderRadius:7,border:"1px solid #E05A1A33"}}>
          <div style={{fontSize:9,color:"#E05A1A",marginBottom:3}}>CALL TO ACTION</div>
          <div style={{fontSize:11,color:"#e5e7eb",fontWeight:500}}>{cta}</div>
        </div>}
      </div>
    </div>
  );
}

export default function ContentEngine() {
  const [queue, setQueue] = useState([]);
  const [approved, setApproved] = useState([]);
  const [rejected, setRejected] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [activeTab, setActiveTab] = useState("queue");
  const [exitDir, setExitDir] = useState(null);
  const [toast, setToast] = useState(null);

  const showToast = (msg,color) => { setToast({msg,color}); setTimeout(()=>setToast(null),2000); };

  const loadQueue = async () => {
    try {
      const r = await fetch(`${API}/agents/content-engine/queue`);
      const d = await r.json();
      setQueue(d.queue||[]);
    } catch(e) { console.error(e); }
    setLoading(false);
  };

  useEffect(()=>{ loadQueue(); },[]);

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      await fetch(`${API}/agents/content-engine/scrape`,{method:"POST"});
      await fetch(`${API}/agents/content-engine/bulk-remix`,{method:"POST"});
      await loadQueue();
      showToast("⚡ New batch generated","#E05A1A");
    } catch(e) { showToast("Error generating","#EF4444"); }
    setGenerating(false);
  };

  const act = async (scriptId, action) => {
    try {
      await fetch(`${API}/agents/content-engine/action`,{
        method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({script_id:scriptId,action})
      });
    } catch(e) {}
  };

  const handleApprove = useCallback(() => {
    if(!queue[0]) return;
    setExitDir("right");
    setTimeout(async()=>{
      await act(queue[0].id,"approve");
      setApproved(a=>[queue[0],...a]);
      setQueue(q=>q.slice(1));
      setExitDir(null);
      showToast("✓ Approved","#10B981");
    },300);
  },[queue]);

  const handleReject = useCallback(() => {
    if(!queue[0]) return;
    setExitDir("left");
    setTimeout(async()=>{
      await act(queue[0].id,"reject");
      setRejected(r=>[queue[0],...r]);
      setQueue(q=>q.slice(1));
      setExitDir(null);
      showToast("Skipped","#4b5563");
    },300);
  },[queue]);

  return (
    <div style={{background:"#08090b",minHeight:"100vh",fontFamily:"'DM Sans','Inter',sans-serif",color:"#fff",position:"relative"}}>
      {toast&&<div style={{position:"fixed",top:20,left:"50%",transform:"translateX(-50%)",background:"#111418",border:`1px solid ${toast.color}44`,borderRadius:10,padding:"10px 20px",fontSize:12,fontWeight:600,color:toast.color,zIndex:1000}}>{toast.msg}</div>}
      <div style={{borderBottom:"1px solid #111418",padding:"18px 24px 0",background:"linear-gradient(180deg,#0d0f12,#08090b)"}}>
        <div style={{display:"flex",justifyContent:"space-between",alignItems:"flex-start"}}>
          <div>
            <div style={{display:"flex",alignItems:"center",gap:8,marginBottom:3}}>
              <div style={{width:7,height:7,borderRadius:"50%",background:"#10B981",boxShadow:"0 0 8px #10B981"}}/>
              <span style={{fontSize:9,color:"#10B981",letterSpacing:"0.15em",fontWeight:700}}>CONTENT ENGINE · LIVE</span>
            </div>
            <h1 style={{fontSize:20,fontWeight:800,letterSpacing:-0.8,margin:0}}>Vibe-UGC Queue</h1>
            <p style={{fontSize:11,color:"#4b5563",margin:"3px 0 0"}}>AI-remixed viral hooks · Swipe to approve</p>
          </div>
          <div style={{display:"flex",gap:18}}>
            {[{l:"QUEUE",v:queue.length,c:"#9ca3af"},{l:"APPROVED",v:approved.length,c:"#10B981"},{l:"REJECTED",v:rejected.length,c:"#EF4444"}].map(s=>(
              <div key={s.l} style={{textAlign:"right"}}>
                <div style={{fontSize:18,fontWeight:800,color:s.c}}>{s.v}</div>
                <div style={{fontSize:9,color:"#374151"}}>{s.l}</div>
              </div>
            ))}
          </div>
        </div>
        <div style={{display:"flex",marginTop:18}}>
          {[{id:"queue",label:"Swipe Queue"},{id:"approved",label:`Approved (${approved.length})`},{id:"rejected",label:`Rejected (${rejected.length})`}].map(t=>(
            <button key={t.id} onClick={()=>setActiveTab(t.id)} style={{background:"none",border:"none",cursor:"pointer",padding:"9px 18px",fontSize:11,fontWeight:600,color:activeTab===t.id?"#fff":"#4b5563",borderBottom:activeTab===t.id?"2px solid #E05A1A":"2px solid transparent",transition:"all 0.2s"}}>{t.label}</button>
          ))}
        </div>
      </div>
      <div style={{padding:"24px"}}>
        {activeTab==="queue"&&(
          <div style={{display:"flex",gap:24,alignItems:"flex-start"}}>
            <div style={{flex:1}}>
              {loading?<div style={{textAlign:"center",padding:"60px",color:"#4b5563"}}>Loading queue...</div>
              :queue.length>0?(
                <>
                  <div style={{display:"flex",justifyContent:"space-between",marginBottom:16}}>
                    <div style={{fontSize:10,color:"#374151"}}>← DRAG TO REJECT · DRAG TO APPROVE →</div>
                    <div style={{fontSize:10,color:"#374151"}}>{queue.length} remaining</div>
                  </div>
                  <div style={{position:"relative",height:560,display:"flex",justifyContent:"center"}}>
                    {queue.slice(1,3).reverse().map((s,i)=>(
                      <div key={s.id} style={{position:"absolute",width:"100%",maxWidth:420,transform:`scale(${0.94-i*0.04}) translateY(${(i+1)*12}px)`,opacity:0.45-i*0.15,pointerEvents:"none",zIndex:i}}>
                        <SwipeCard script={s} onApprove={()=>{}} onReject={()=>{}} isTop={false}/>
                      </div>
                    ))}
                    <div style={{position:"absolute",width:"100%",maxWidth:420,zIndex:10,transform:exitDir==="right"?"translate(120%,-20px) rotate(20deg)":exitDir==="left"?"translate(-120%,-20px) rotate(-20deg)":"none",opacity:exitDir?0:1,transition:exitDir?"transform 0.3s ease-in,opacity 0.3s":"none"}}>
                      <SwipeCard key={queue[0].id} script={queue[0]} onApprove={handleApprove} onReject={handleReject} isTop={true}/>
                    </div>
                  </div>
                  <div style={{display:"flex",gap:12,justifyContent:"center",marginTop:20}}>
                    <button onClick={handleReject} style={{width:52,height:52,borderRadius:"50%",background:"#EF444411",border:"2px solid #EF444433",color:"#EF4444",fontSize:20,cursor:"pointer"}}>✕</button>
                    <button onClick={handleApprove} style={{padding:"0 28px",height:52,borderRadius:26,background:"linear-gradient(135deg,#10B981,#059669)",border:"none",color:"#fff",fontSize:12,fontWeight:700,cursor:"pointer"}}>✓ APPROVE</button>
                    <button onClick={handleReject} style={{width:52,height:52,borderRadius:"50%",background:"#E05A1A11",border:"2px solid #E05A1A33",color:"#E05A1A",fontSize:16,cursor:"pointer"}}>✏</button>
                  </div>
                </>
              ):(
                <div style={{textAlign:"center",padding:"60px 20px"}}>
                  <div style={{fontSize:44,marginBottom:14}}>🎬</div>
                  <div style={{fontSize:15,fontWeight:700,color:"#9ca3af",marginBottom:8}}>Queue empty</div>
                  <button onClick={handleGenerate} disabled={generating} style={{padding:"12px 28px",borderRadius:12,background:generating?"#1a1d22":"linear-gradient(135deg,#E05A1A,#c04a14)",border:"none",color:"#fff",fontSize:12,fontWeight:700,cursor:generating?"not-allowed":"pointer"}}>
                    {generating?"⟳ Generating...":"⚡ Generate New Batch"}
                  </button>
                </div>
              )}
            </div>
            <div style={{width:220,flexShrink:0}}>
              <button onClick={handleGenerate} disabled={generating} style={{width:"100%",padding:"13px",borderRadius:11,marginBottom:16,background:generating?"#1a1d22":"linear-gradient(135deg,#E05A1A,#c04a14)",border:"none",color:"#fff",fontSize:11,fontWeight:700,cursor:generating?"not-allowed":"pointer"}}>
                {generating?"⟳ GENERATING...":"⚡ GENERATE BATCH"}
              </button>
              <div style={{background:"#0d0f12",border:"1px solid #1a1d22",borderRadius:11,padding:"14px 16px"}}>
                <div style={{fontSize:9,color:"#4b5563",marginBottom:10}}>FORMAT BREAKDOWN</div>
                {Object.entries(FORMAT_META).map(([k,m])=>{
                  const count=queue.filter(s=>s.format_type===k).length;
                  return <div key={k} style={{display:"flex",justifyContent:"space-between",marginBottom:7}}>
                    <span style={{fontSize:9,color:"#6b7280"}}>{m.emoji} {m.label}</span>
                    <span style={{fontSize:12,fontWeight:700,color:m.color}}>{count}</span>
                  </div>;
                })}
              </div>
            </div>
          </div>
        )}
        {activeTab==="approved"&&(
          approved.length===0?<div style={{textAlign:"center",padding:"60px",color:"#4b5563"}}>No approved scripts yet.</div>:
          <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fill,minmax(320px,1fr))",gap:14}}>
            {approved.map(s=>{ const {body,cta}=parseScript(s.script_body); return (
              <div key={s.id} style={{background:"#0d0f12",border:"1px solid #10B98133",borderRadius:13,padding:"16px 18px"}}>
                <div style={{fontSize:9,color:"#10B981",fontWeight:700,marginBottom:8}}>✓ APPROVED · {FORMAT_META[s.format_type]?.emoji} {FORMAT_META[s.format_type]?.label}</div>
                <div style={{fontSize:11,color:"#9ca3af",lineHeight:1.7,marginBottom:12}}>{body.slice(0,200)}...</div>
                <div style={{display:"flex",gap:8}}>
                  <button style={{flex:1,padding:"7px",borderRadius:7,background:"#3B82F611",border:"1px solid #3B82F633",color:"#3B82F6",fontSize:10,fontWeight:600,cursor:"pointer"}}>📅 Schedule</button>
                  <button onClick={()=>{navigator.clipboard.writeText(body+"\n\n"+cta);}} style={{flex:1,padding:"7px",borderRadius:7,background:"#8B5CF611",border:"1px solid #8B5CF633",color:"#8B5CF6",fontSize:10,fontWeight:600,cursor:"pointer"}}>📋 Copy</button>
                </div>
              </div>
            );})}
          </div>
        )}
        {activeTab==="rejected"&&(
          rejected.length===0?<div style={{textAlign:"center",padding:"60px",color:"#4b5563"}}>No skipped scripts yet.</div>:
          <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fill,minmax(320px,1fr))",gap:14}}>
            {rejected.map(s=>{ const {body}=parseScript(s.script_body); return (
              <div key={s.id} style={{background:"#0d0f12",border:"1px solid #EF444422",borderRadius:13,padding:"16px 18px",opacity:0.6}}>
                <div style={{fontSize:9,color:"#EF4444",fontWeight:700,marginBottom:8}}>✕ SKIPPED</div>
                <div style={{fontSize:11,color:"#6b7280",lineHeight:1.7}}>{body.slice(0,160)}...</div>
              </div>
            );})}
          </div>
        )}
      </div>
    </div>
  );
}
