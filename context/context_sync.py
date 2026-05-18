"""AgentOS L6 stateful context layer — reads/writes Supabase agent_context."""
import os
import asyncio
from datetime import datetime
from typing import Any

try:
    from supabase import create_client, Client
    _SUPABASE_AVAILABLE = True
except ImportError:
    _SUPABASE_AVAILABLE = False

TABLE = "agent_context"
_local_cache: dict[str, Any] = {}  # fallback when Supabase unavailable


def _client() -> "Client | None":
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
    if not (url and key and _SUPABASE_AVAILABLE):
        return None
    return create_client(url, key)


class ContextSync:
    def __init__(self, vertical: str):
        self.vertical = vertical
        self._db = _client()

    async def set(self, key: str, value: Any, meta: dict | None = None) -> bool:
        record = {
            "vertical": self.vertical,
            "key": key,
            "value": str(value),
            "timestamp": datetime.utcnow().isoformat(),
            **(meta or {}),
        }
        _local_cache[f"{self.vertical}:{key}"] = record

        if not self._db:
            return True  # local cache only

        try:
            await asyncio.to_thread(
                lambda: self._db.table(TABLE).upsert(record).execute()
            )
            return True
        except Exception:
            return False

    async def get(self, key: str) -> Any | None:
        cached = _local_cache.get(f"{self.vertical}:{key}")
        if cached:
            return cached["value"]

        if not self._db:
            return None

        try:
            result = await asyncio.to_thread(
                lambda: self._db.table(TABLE)
                .select("value")
                .eq("vertical", self.vertical)
                .eq("key", key)
                .order("timestamp", desc=True)
                .limit(1)
                .execute()
            )
            rows = result.data
            return rows[0]["value"] if rows else None
        except Exception:
            return None

    async def recent(self, limit: int = 20) -> list[dict]:
        if not self._db:
            prefix = f"{self.vertical}:"
            return [v for k, v in _local_cache.items() if k.startswith(prefix)][-limit:]

        try:
            result = await asyncio.to_thread(
                lambda: self._db.table(TABLE)
                .select("*")
                .eq("vertical", self.vertical)
                .order("timestamp", desc=True)
                .limit(limit)
                .execute()
            )
            return result.data
        except Exception:
            return []

    async def move37_feed(self, limit: int = 10) -> list[dict]:
        if not self._db:
            return [
                v for k, v in _local_cache.items()
                if k.startswith(f"{self.vertical}:") and v.get("move37_candidate")
            ][-limit:]

        try:
            result = await asyncio.to_thread(
                lambda: self._db.table(TABLE)
                .select("*")
                .eq("vertical", self.vertical)
                .eq("move37_candidate", True)
                .order("timestamp", desc=True)
                .limit(limit)
                .execute()
            )
            return result.data
        except Exception:
            return []

    async def flywheel_check(self) -> dict:
        """Check if cross-vertical flywheel conditions are met."""
        if self.vertical != "juniper":
            return {"triggered": False, "reason": "flywheel only triggers from juniper lease close"}

        recent = await self.recent(limit=5)
        lease_closes = [r for r in recent if "lease_close" in str(r.get("key", ""))]

        if lease_closes:
            return {
                "triggered": True,
                "target_vertical": "leados",
                "action": "auto_create_renters_insurance_lead",
                "source_events": len(lease_closes),
            }
        return {"triggered": False, "reason": "no recent lease close events"}

    async def log_action(
        self,
        action_type: str,
        simulation_score: float,
        guardrail_passed: bool,
        move37_candidate: bool = False,
        channel_used: str | None = None,
        outcome: str | None = None,
    ) -> bool:
        return await self.set(
            key=f"action:{action_type}:{datetime.utcnow().isoformat()}",
            value=outcome or "executed",
            meta={
                "action_type": action_type,
                "simulation_score": simulation_score,
                "guardrail_passed": guardrail_passed,
                "move37_candidate": move37_candidate,
                "channel_used": channel_used,
            },
        )
