"""
LeadOS HeyGen Service
Generates personalized 30-second insurance outreach videos per lead.
"Hey Maria — saw you're moving to Austin. I can get your renters insurance proof emailed same day."
"""

import os
import asyncio
import logging
import httpx
from typing import Optional

log = logging.getLogger("LeadOS.HeyGen")

HEYGEN_API_KEY = os.getenv("HEYGEN_API_KEY", "")
HEYGEN_BASE = "https://api.heygen.com"

# Your avatar ID — get from HeyGen dashboard → Avatars
# Default to a professional male avatar if not set
AVATAR_ID = os.getenv("HEYGEN_AVATAR_ID", "josh_lite3_20230714")
VOICE_ID  = os.getenv("HEYGEN_VOICE_ID",  "2d5b0e6cf36f460aa7fc47e3eee4ba54")

# Insurance-specific video scripts per life event
VIDEO_SCRIPTS = {
    "new_move": "Hey {first_name} — heard you're making a move to {city}. Congrats! I'm Enrique, a licensed insurance agent in Texas. I can get your renters or auto insurance sorted same day so you're covered the moment you arrive. Takes about 10 minutes. Want me to shoot you a quick quote?",
    "car_purchase": "Hey {first_name} — looks like you're in the market for a new car. I'm Enrique, a licensed Texas insurance agent. I can have you fully insured in under 20 minutes so you can drive it off the lot today. No hassle, just fast coverage. Want a quick quote?",
    "deed_transfer": "Hey {first_name} — congratulations on the new home! I'm Enrique with We Insure. Your lender needs a homeowners insurance binder before closing. I specialize in the Texas market and can get that to you today. Let me help you close on time.",
    "apt_listing": "Hey {first_name} — your apartment locator sent me your way. I'm Enrique, a licensed insurance agent. I can get your renters insurance proof emailed to you and your landlord today — takes about 10 minutes. Lemonade starts at $5 a month. Want me to set it up?",
    "new_homeowner": "Hey {first_name} — congrats on closing on your new home! I'm Enrique with We Insure. I specialize in Texas home insurance, including older properties and tricky situations other agents won't touch. Let's make sure you're protected.",
    "default": "Hey {first_name} — I'm Enrique, a licensed P&C insurance agent in Texas. I saw you might be in the market for insurance. I work with all the major carriers and can get you the best rate fast. Takes about 10 minutes. Want a quick quote?",
}


async def generate_video(
    lead: dict,
    life_event: Optional[str] = None,
) -> dict:
    """
    Generate a personalized HeyGen video for a lead.
    Returns: { video_id, video_url, status, script }
    """
    if not HEYGEN_API_KEY:
        return {"error": "HEYGEN_API_KEY not set", "status": "skipped"}

    first_name = (lead.get("raw_name") or lead.get("name") or "there").split()[0].title()
    city = _extract_city(lead.get("location") or "Austin, TX")
    event = life_event or lead.get("life_event") or "default"

    script_template = VIDEO_SCRIPTS.get(event, VIDEO_SCRIPTS["default"])
    script = script_template.format(
        first_name=first_name,
        city=city,
        policy_type=lead.get("insurance_type") or "insurance",
    )

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            # Create video generation job
            res = await client.post(
                f"{HEYGEN_BASE}/v2/video/generate",
                headers={
                    "X-Api-Key": HEYGEN_API_KEY,
                    "Content-Type": "application/json",
                },
                json={
                    "video_inputs": [
                        {
                            "character": {
                                "type": "avatar",
                                "avatar_id": AVATAR_ID,
                                "avatar_style": "normal",
                            },
                            "voice": {
                                "type": "text",
                                "input_text": script,
                                "voice_id": VOICE_ID,
                                "speed": 1.0,
                            },
                            "background": {
                                "type": "color",
                                "value": "#f8f8f6",
                            },
                        }
                    ],
                    "dimension": {"width": 1280, "height": 720},
                    "aspect_ratio": "16:9",
                    "test": False,
                },
            )

            if res.status_code != 200:
                log.error(f"HeyGen API error {res.status_code}: {res.text[:200]}")
                return {"error": f"HeyGen returned {res.status_code}", "status": "failed", "script": script}

            data = res.json()
            video_id = data.get("data", {}).get("video_id")

            log.info(f"HeyGen video job created: {video_id} for {first_name}")
            return {
                "status": "processing",
                "video_id": video_id,
                "script": script,
                "lead_name": first_name,
                "check_url": f"{HEYGEN_BASE}/v1/video_status.get?video_id={video_id}",
            }

    except Exception as e:
        log.error(f"HeyGen generate_video error: {e}")
        return {"error": str(e), "status": "failed", "script": script}


async def get_video_status(video_id: str) -> dict:
    """Poll HeyGen for video status. Returns video_url when complete."""
    if not HEYGEN_API_KEY:
        return {"error": "HEYGEN_API_KEY not set"}

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            res = await client.get(
                f"{HEYGEN_BASE}/v1/video_status.get",
                headers={"X-Api-Key": HEYGEN_API_KEY},
                params={"video_id": video_id},
            )
            if res.status_code != 200:
                return {"error": f"Status check failed: {res.status_code}"}

            data = res.json().get("data", {})
            status = data.get("status")  # processing, completed, failed

            result = {"video_id": video_id, "status": status}
            if status == "completed":
                result["video_url"] = data.get("video_url")
                result["thumbnail_url"] = data.get("thumbnail_url")
                log.info(f"HeyGen video {video_id} complete: {result['video_url']}")

            return result

    except Exception as e:
        return {"error": str(e), "status": "failed"}


async def wait_for_video(video_id: str, max_wait: int = 300) -> dict:
    """Poll until video is complete or timeout (default 5 min)."""
    for _ in range(max_wait // 10):
        await asyncio.sleep(10)
        result = await get_video_status(video_id)
        if result.get("status") in ("completed", "failed"):
            return result
    return {"video_id": video_id, "status": "timeout"}


async def list_avatars() -> list:
    """List available HeyGen avatars."""
    if not HEYGEN_API_KEY:
        return []
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            res = await client.get(
                f"{HEYGEN_BASE}/v2/avatars",
                headers={"X-Api-Key": HEYGEN_API_KEY},
            )
            return res.json().get("data", {}).get("avatars", [])
    except Exception as e:
        log.error(f"HeyGen list_avatars: {e}")
        return []


def _extract_city(location: str) -> str:
    """Extract city from location string like '78704 · Austin TX'"""
    if "Austin" in location: return "Austin"
    if "Houston" in location: return "Houston"
    if "Dallas" in location: return "Dallas"
    if "San Antonio" in location: return "San Antonio"
    parts = location.split("·")
    if len(parts) > 1:
        city_state = parts[-1].strip()
        return city_state.split()[0] if city_state else "Texas"
    return "Texas"
