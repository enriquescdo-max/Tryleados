import os, httpx, json
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from supabase import create_client

supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
ANTHROPIC_KEY = os.environ["ANTHROPIC_API_KEY"]

content_engine_router = APIRouter(prefix="/agents/content-engine", tags=["Content Engine"])

class RemixRequest(BaseModel):
    hook_id: str
    format_type: str = "wall_of_text"

class ScriptAction(BaseModel):
    script_id: str
    action: str

def get_brand():
    r = supabase.table("brand_context").select("*").eq("product_name","LeadOS").single().execute()
    return r.data or {}

async def call_claude(prompt, system):
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post("https://api.anthropic.com/v1/messages",
            headers={"x-api-key":ANTHROPIC_KEY,"anthropic-version":"2023-06-01","content-type":"application/json"},
            json={"model":"claude-sonnet-4-20250514","max_tokens":800,"system":system,"messages":[{"role":"user","content":prompt}]})
        r.raise_for_status()
        return r.json()["content"][0]["text"]

@content_engine_router.post("/scrape")
async def scrape(niche: str = "insurance"):
    if os.environ.get("MOCK_MODE","false").lower() == "true":
        hooks = [
            {"platform":"tiktok","niche":niche,"format":"wall_of_text","hook_text":"The insurance company does not want you to know this...","view_count":2400000,"like_count":180000,"share_count":22300,"status":"raw"},
            {"platform":"tiktok","niche":niche,"format":"slideshow","hook_text":"5 signs you are overpaying for car insurance right now","view_count":1800000,"like_count":142000,"share_count":19800,"status":"raw"},
            {"platform":"tiktok","niche":niche,"format":"hook_demo","hook_text":"I compared 6 insurance quotes in 47 seconds","view_count":3100000,"like_count":267000,"share_count":41200,"status":"raw"},
            {"platform":"instagram","niche":niche,"format":"green_screen","hook_text":"POV: your agent just saved you 400 dollars","view_count":980000,"like_count":95000,"share_count":12400,"status":"raw"},
        ]
        supabase.table("viral_hooks").insert(hooks).execute()
        return {"status":"seeded","count":len(hooks)}
    return {"status":"set MOCK_MODE=true for demo"}

@content_engine_router.post("/remix")
async def remix(req: RemixRequest):
    hook = supabase.table("viral_hooks").select("*").eq("id",req.hook_id).single().execute().data
    if not hook: raise HTTPException(404,"Hook not found")
    brand = get_brand()
    system = ("You are a viral copywriter for LeadOS. "
             "Return ONLY raw JSON: {\"script_body\":\"...\",\"cta\":\"...\",\"brand_angle\":\"...\",\"tone\":\"...\"}\n")
    raw = await call_claude(f'Remix for LeadOS ({req.format_type}): "{hook["hook_text"]}"', system)
    try: parsed = json.loads(raw.strip())
    except: parsed = {"script_body":raw,"cta":"Try LeadOS free at tryleados.com","brand_angle":"general","tone":"confident"}
    payload = {"hook_id":req.hook_id,"brand_angle":parsed.get("brand_angle","general"),"script_body":parsed.get("script_body",""),"cta":parsed.get("cta",""),"format_type":req.format_type,"tone":parsed.get("tone","confident"),"status":"pending"}
    result = supabase.table("content_scripts").insert(payload).execute()
    supabase.table("viral_hooks").update({"status":"remixed"}).eq("id",req.hook_id).execute()
    return {"status":"remixed","script":result.data[0] if result.data else payload}

@content_engine_router.post("/bulk-remix")
async def bulk_remix(niche: str = "insurance", limit: int = 5):
    raw_hooks = supabase.table("viral_hooks").select("id,hook_text,format").eq("niche",niche).eq("status","raw").limit(limit).execute()
    if not raw_hooks.data: return {"status":"no_raw_hooks","message":"Run /scrape first"}
    results = []
    for h in raw_hooks.data:
        try:
            await remix(RemixRequest(hook_id=h["id"],format_type=h.get("format","wall_of_text")))
            results.append({"hook_id":h["id"],"status":"remixed"})
        except Exception as e:
            results.append({"hook_id":h["id"],"status":"error","error":str(e)})
    return {"status":"complete","results":results}

@content_engine_router.get("/queue")
async def get_queue(status: str = "pending", limit: int = 20):
    r = supabase.table("content_scripts").select("*,viral_hooks(*)").eq("status",status).order("created_at",desc=True).limit(limit).execute()
    return {"queue":r.data,"count":len(r.data)}

@content_engine_router.post("/action")
async def action(req: ScriptAction):
    if req.action not in {"approve","reject"}: raise HTTPException(400,"must be approve or reject")
    update = {"status":"approved" if req.action=="approve" else "rejected","reviewed_at":datetime.utcnow().isoformat()}
    r = supabase.table("content_scripts").update(update).eq("id",req.script_id).execute()
    if not r.data: raise HTTPException(404,"Not found")
    return {"status":update["status"]}

@content_engine_router.get("/stats")
async def stats():
    r = supabase.table("content_queue_stats").select("*").execute()
    return r.data[0] if r.data else {}
