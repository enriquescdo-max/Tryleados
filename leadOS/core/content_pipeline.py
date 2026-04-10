"""
LeadOS Content Pipeline (P19)
ElevenLabs voice synthesis + HeyGen video rendering
Heartbeat-triggered 2-3x per week.
"""
import logging
import os
from typing import Optional, Dict

log = logging.getLogger("LeadOS.ContentPipeline")

ELEVENLABS_API = "https://api.elevenlabs.io/v1"
HEYGEN_API     = "https://api.heygen.com/v2"

CONTENT_TEMPLATES = {
    "lone_wolf_story": {
        "hook": "I built a tool that finds insurance leads while I sleep.",
        "template": """Hook: "I built a tool that finds insurance leads while I sleep."
Problem: Cold calls, bought lists, wasted money on unqualified leads.
Solution: LeadOS finds, qualifies, calls, and transfers leads — you just close.
CTA: "Link in bio — first week free"
Length: 60 seconds""",
        "duration": 60,
    },
    "lead_tip": {
        "hook": "The #1 mistake insurance agents make with online leads.",
        "template": """Hook: "The #1 mistake insurance agents make with online leads"
Tip: Waiting more than 5 minutes to call a new lead drops your conversion rate by 80%.
LeadOS tie-in: LeadOS calls new leads within 60 seconds automatically.
CTA: "Try it free at tryleados.com"
Length: 45 seconds""",
        "duration": 45,
    },
    "transfer_proof": {
        "hook": "An AI just transferred a live qualified lead to my phone.",
        "template": """Hook: "An AI just transferred a live qualified lead to my phone"
Walkthrough: AI calls the lead → qualifies with 5 questions → scores 0-100 → transfers at 75+
Result: You only pick up the phone when the lead is already sold.
CTA: "This is now available for any insurance agent at tryleados.com"
Length: 90 seconds""",
        "duration": 90,
    },
}


async def generate_script_with_claude(template_key: str, lead_stats: Dict, api_key: str) -> str:
    """Use Claude to generate a personalized script from a template."""
    try:
        import anthropic, asyncio

        template = CONTENT_TEMPLATES.get(template_key, CONTENT_TEMPLATES["lone_wolf_story"])
        leads_generated = lead_stats.get("total", 0)
        transfers       = lead_stats.get("transfers", 0)

        prompt = f"""You are writing a short-form video script for a licensed P&C insurance agent
who uses LeadOS to automate their lead generation.

Template: {template['template']}

Real stats to incorporate:
- Leads generated this week: {leads_generated}
- Qualified transfers this week: {transfers}

Write a natural, conversational script (no robotic language).
Keep it under {template['duration']} seconds when spoken at normal pace (~140 words/min).
Start with the hook. End with the CTA.
Return only the script text, no stage directions."""

        client = anthropic.Anthropic(api_key=api_key)
        response = await asyncio.to_thread(
            client.messages.create,
            model="claude-sonnet-4-20250514",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        script = response.content[0].text.strip()
        log.info(f"Script generated for {template_key}: {len(script)} chars")
        return script
    except Exception as e:
        log.warning(f"Script generation failed: {e}")
        return CONTENT_TEMPLATES.get(template_key, {}).get("hook", "LeadOS — find leads while you sleep.")


async def synthesize_voice(script: str, voice_id: str, elevenlabs_key: str) -> Optional[bytes]:
    """Convert script to audio bytes via ElevenLabs TTS."""
    if not elevenlabs_key:
        log.warning("ELEVENLABS_API_KEY not configured — skipping voice synthesis")
        return None
    try:
        import httpx, asyncio
        resp = await asyncio.to_thread(
            lambda: httpx.post(
                f"{ELEVENLABS_API}/text-to-speech/{voice_id}",
                headers={
                    "xi-api-key": elevenlabs_key,
                    "Content-Type": "application/json",
                    "Accept": "audio/mpeg",
                },
                json={
                    "text": script,
                    "model_id": "eleven_turbo_v2",
                    "voice_settings": {"stability": 0.75, "similarity_boost": 0.85},
                },
                timeout=30,
            )
        )
        if resp.status_code == 200:
            log.info(f"Voice synthesized: {len(resp.content)} bytes")
            return resp.content
        else:
            log.warning(f"ElevenLabs error {resp.status_code}: {resp.text[:100]}")
            return None
    except Exception as e:
        log.error(f"Voice synthesis error: {e}")
        return None


async def submit_heygen_video(
    script: str,
    avatar_id: str,
    voice_id: str,
    heygen_key: str,
) -> Optional[str]:
    """Submit video generation job to HeyGen. Returns video_id."""
    if not heygen_key:
        log.warning("HEYGEN_API_KEY not configured — skipping video generation")
        return None
    try:
        import httpx, asyncio
        payload = {
            "video_inputs": [{
                "character": {
                    "type": "avatar",
                    "avatar_id": avatar_id or "default_avatar",
                    "avatar_style": "normal",
                },
                "voice": {
                    "type": "elevenlabs",
                    "elevenlabs_voice_id": voice_id,
                    "input_text": script,
                },
                "background": {"type": "from_image", "image_type": "office_blur"},
            }],
            "aspect_ratio": "9:16",
            "test": False,
        }
        resp = await asyncio.to_thread(
            lambda: httpx.post(
                f"{HEYGEN_API}/video/generate",
                headers={"x-api-key": heygen_key, "Content-Type": "application/json"},
                json=payload,
                timeout=30,
            )
        )
        if resp.status_code in (200, 201):
            video_id = resp.json().get("data", {}).get("video_id")
            log.info(f"HeyGen video submitted: {video_id}")
            return video_id
        else:
            log.warning(f"HeyGen error {resp.status_code}: {resp.text[:100]}")
            return None
    except Exception as e:
        log.error(f"HeyGen submission error: {e}")
        return None


async def run_content_pipeline(
    template_key: str = "lone_wolf_story",
    lead_stats: Optional[Dict] = None,
    anthropic_key: str = "",
    elevenlabs_key: str = "",
    elevenlabs_voice_id: str = "",
    heygen_key: str = "",
    heygen_avatar_id: str = "",
) -> Dict:
    """
    Full pipeline: Claude script → ElevenLabs audio → HeyGen video
    Returns status dict with script, audio_bytes, and video_id.
    """
    result = {"template": template_key, "script": None, "audio": None, "video_id": None}

    # Step 1: Generate script
    script = await generate_script_with_claude(
        template_key, lead_stats or {}, anthropic_key
    )
    result["script"] = script

    # Step 2: Synthesize voice
    if elevenlabs_key and elevenlabs_voice_id:
        audio = await synthesize_voice(script, elevenlabs_voice_id, elevenlabs_key)
        result["audio"] = f"{len(audio)} bytes" if audio else None

    # Step 3: Submit HeyGen video
    if heygen_key and elevenlabs_voice_id:
        video_id = await submit_heygen_video(
            script, heygen_avatar_id, elevenlabs_voice_id, heygen_key
        )
        result["video_id"] = video_id

    log.info(f"Content pipeline complete: {result}")
    return result
