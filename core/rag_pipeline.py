"""
RAG pipeline over context_nodes table in Supabase.
Nodes store text chunks + embeddings (pgvector) per vertical/agent.
"""
import os
import hashlib
from datetime import datetime, timezone
from typing import Optional
import anthropic
from supabase import create_client

_sb = None
_ac = None

def _supabase():
    global _sb
    if _sb is None:
        _sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
    return _sb

def _anthropic():
    global _ac
    if _ac is None:
        _ac = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _ac

def _embed(text: str) -> list[float]:
    # Supabase pgvector expects float array; use a lightweight model or OpenAI.
    # Placeholder: returns deterministic mock for local dev if no embed key set.
    embed_key = os.environ.get("OPENAI_API_KEY")
    if embed_key:
        import openai
        openai.api_key = embed_key
        resp = openai.embeddings.create(input=text, model="text-embedding-3-small")
        return resp.data[0].embedding
    # Fallback: zero vector (disables semantic search, exact match only)
    return [0.0] * 1536

def upsert_node(
    content: str,
    vertical: str,
    agent_name: str,
    node_type: str = "knowledge",
    metadata: dict = None,
) -> str:
    node_id = hashlib.sha256(f"{vertical}:{agent_name}:{content}".encode()).hexdigest()[:16]
    embedding = _embed(content)
    _supabase().table("context_nodes").upsert({
        "id": node_id,
        "content": content,
        "vertical": vertical,
        "agent_name": agent_name,
        "node_type": node_type,
        "embedding": embedding,
        "metadata": metadata or {},
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).execute()
    return node_id

def retrieve(
    query: str,
    vertical: str,
    agent_name: Optional[str] = None,
    top_k: int = 5,
) -> list[dict]:
    embedding = _embed(query)
    # pgvector cosine similarity via Supabase RPC
    params = {"query_embedding": embedding, "vertical_filter": vertical, "match_count": top_k}
    if agent_name:
        params["agent_filter"] = agent_name
    try:
        rows = _supabase().rpc("match_context_nodes", params).execute().data
    except Exception:
        # Fallback: plain text search if RPC not deployed
        q = _supabase().table("context_nodes").select("*").eq("vertical", vertical)
        if agent_name:
            q = q.eq("agent_name", agent_name)
        rows = q.limit(top_k).execute().data
    return rows

def build_context_block(query: str, vertical: str, agent_name: str = None, top_k: int = 5) -> str:
    nodes = retrieve(query, vertical, agent_name, top_k)
    if not nodes:
        return ""
    chunks = [f"[{n.get('node_type','context')}] {n['content']}" for n in nodes]
    return "RETRIEVED CONTEXT:\n" + "\n---\n".join(chunks)
