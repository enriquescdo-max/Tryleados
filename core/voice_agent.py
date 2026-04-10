"""
LeadOS Voice Agent — Vapi.ai Integration (P11-P13)
Handles:
  - Vapi assistant creation + configuration
  - Outbound call initiation
  - Webhook processing (call started/ended/transfer-requested)
  - Twilio warm transfer bridge
  - Lead score calculation from call transcript
  - Supabase call logging (P15)
"""
import logging
import os
from typing import Optional, Dict, Any

log = logging.getLogger("LeadOS.VoiceAgent")

# ── System Prompt (from CLAUDE.md Section 6) ─────────────────────────────────
VOICE_SYSTEM_PROMPT = """You are Aria, a friendly and professional AI calling on behalf of a
licensed insurance agency. You are calling because the prospect recently
expressed interest in home or auto insurance.

Your goal: qualify this lead in under 3 minutes using these 5 questions.
Score each answer 0-20 points. Total score determines transfer.

QUESTION FLOW:
Q1: "Are you currently insured for home or auto?"
  Yes, shopping for better rate = 20pts | Yes, not looking = 5pts | No = 15pts

Q2: "When does your current policy renew, or when do you need coverage?"
  Within 30 days = 20pts | 30-90 days = 15pts | Just looking = 5pts

Q3: "Are you a homeowner or renter?"
  Homeowner (bundle opportunity) = 20pts | Renter = 10pts

Q4: "Roughly how many vehicles are in your household?"
  2+ = 20pts | 1 = 15pts | 0 = 5pts

Q5: "What state are you located in?"
  [Check if agent is licensed in that state] Licensed = 20pts | Not licensed = 0pts

SCORING:
75-100: Say "I'm going to connect you with one of our licensed specialists
        right now — please hold for just a moment." → TRIGGER TRANSFER
50-74:  Say "Great, I'll have someone follow up with you by end of day."
         → END CALL, ADD TO NURTURE
0-49:   Say "Thanks so much for your time. Have a great day!" → DISQUALIFY

RULES:
- Always disclose you are an AI at the start if asked directly
- Never quote specific premiums or coverage amounts
- Never make guarantees about rates
- Keep total call under 4 minutes
- Be warm, not robotic. Short sentences. Natural pauses.
- Begin with: "Hi, this is Aria calling about your recent insurance inquiry. Do you have 2 minutes?" """

# ── Vapi Assistant Config ─────────────────────────────────────────────────────
def build_vapi_assistant_config(
    elevenlabs_voice_id: str = "",
    transfer_phone: str = "",
) -> Dict:
    """Build the full Vapi assistant configuration dict."""
    voice_config = {
        "provider": "elevenlabs",
        "voiceId": elevenlabs_voice_id or "EXAVITQu4vr4xnSDxMaL",  # default ElevenLabs voice
        "stability": 0.75,
        "similarityBoost": 0.85,
    } if elevenlabs_voice_id else {
        "provider": "openai",
        "voiceId": "alloy",  # fallback if no ElevenLabs key
    }

    config = {
        "name": "Aria — LeadOS Voice Agent",
        "model": {
            "provider": "anthropic",
            "model": "claude-sonnet-4-20250514",
            "systemPrompt": VOICE_SYSTEM_PROMPT,
            "temperature": 0.3,
        },
        "voice": voice_config,
        "firstMessage": "Hi, this is Aria calling about your recent insurance inquiry. Do you have 2 minutes?",
        "endCallMessage": "Thanks so much for your time. Someone from our team will follow up shortly.",
        "maxDurationSeconds": 300,
        "recordingEnabled": True,
        "transcriptPlan": {"enabled": True},
        "endCallFunctionEnabled": True,
    }

    # Add warm transfer destination if phone number is configured
    if transfer_phone:
        config["forwardingPhoneNumber"] = transfer_phone

    return config


async def create_vapi_assistant(vapi_key: str, config: Dict) -> Optional[str]:
    """Create a Vapi assistant and return its ID."""
    try:
        import httpx
        resp = httpx.post(
            "https://api.vapi.ai/assistant",
            headers={"Authorization": f"Bearer {vapi_key}", "Content-Type": "application/json"},
            json=config,
            timeout=15,
        )
        if resp.status_code in (200, 201):
            assistant_id = resp.json().get("id")
            log.info(f"Vapi assistant created: {assistant_id}")
            return assistant_id
        else:
            log.error(f"Vapi assistant creation failed {resp.status_code}: {resp.text[:200]}")
            return None
    except Exception as e:
        log.error(f"Vapi assistant creation error: {e}")
        return None


async def initiate_outbound_call(
    vapi_key: str,
    assistant_id: str,
    lead_phone: str,
    twilio_phone: str,
    lead_name: str = "",
    metadata: Optional[Dict] = None,
) -> Optional[str]:
    """Initiate an outbound call via Vapi. Returns call_id on success."""
    try:
        import httpx
        payload = {
            "assistantId": assistant_id,
            "phoneNumber": {
                "twilioPhoneNumber": twilio_phone,
                "twilioAccountSid": os.getenv("TWILIO_ACCOUNT_SID", ""),
                "twilioAuthToken": os.getenv("TWILIO_AUTH_TOKEN", ""),
            },
            "customer": {
                "number": lead_phone,
                "name": lead_name,
            },
        }
        if metadata:
            payload["metadata"] = metadata

        resp = httpx.post(
            "https://api.vapi.ai/call/phone",
            headers={"Authorization": f"Bearer {vapi_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=15,
        )
        if resp.status_code in (200, 201):
            call_id = resp.json().get("id")
            log.info(f"Vapi call initiated: {call_id} → {lead_phone}")
            return call_id
        else:
            log.error(f"Vapi call initiation failed {resp.status_code}: {resp.text[:200]}")
            return None
    except Exception as e:
        log.error(f"Vapi call error: {e}")
        return None


def score_call_transcript(transcript: str) -> Dict:
    """
    Parse a Vapi call transcript and extract the qualification score.
    Returns {'score': int, 'outcome': str, 'answers': dict}
    """
    score = 0
    answers = {}
    transcript_lower = transcript.lower()

    # Q1: Currently insured?
    if "shopping" in transcript_lower or "better rate" in transcript_lower:
        answers["q1"] = "shopping"; score += 20
    elif "not looking" in transcript_lower:
        answers["q1"] = "not_looking"; score += 5
    elif "not insured" in transcript_lower or "no insurance" in transcript_lower:
        answers["q1"] = "uninsured"; score += 15

    # Q2: Policy renewal
    if "within 30" in transcript_lower or "this month" in transcript_lower or "next month" in transcript_lower:
        answers["q2"] = "within_30_days"; score += 20
    elif "few months" in transcript_lower or "three months" in transcript_lower:
        answers["q2"] = "30_90_days"; score += 15
    else:
        answers["q2"] = "just_looking"; score += 5

    # Q3: Homeowner vs renter
    if "homeowner" in transcript_lower or "own my home" in transcript_lower or "own a home" in transcript_lower:
        answers["q3"] = "homeowner"; score += 20
    elif "renter" in transcript_lower or "rent" in transcript_lower:
        answers["q3"] = "renter"; score += 10

    # Q4: Vehicles
    if any(n in transcript_lower for n in ["two vehicles", "2 vehicles", "three vehicles", "3 vehicles", "multiple vehicles"]):
        answers["q4"] = "2plus"; score += 20
    elif "one vehicle" in transcript_lower or "1 vehicle" in transcript_lower or "one car" in transcript_lower:
        answers["q4"] = "one"; score += 15

    # Q5: State licensing — score 20 if transfer was triggered
    if "connect you with" in transcript_lower or "licensed specialist" in transcript_lower:
        answers["q5"] = "licensed_state"; score += 20

    if score >= 75:
        outcome = "transfer"
    elif score >= 50:
        outcome = "nurture"
    else:
        outcome = "disqualified"

    return {"score": min(score, 100), "outcome": outcome, "answers": answers}


async def log_call_to_supabase(
    call_id: str,
    lead_id: str,
    duration: int,
    score_before: float,
    score_after: float,
    transferred: bool,
    recording_url: str,
    transcript: str,
    outcome: str,
) -> bool:
    """Log completed call to Supabase voice_call_logs table (P15)."""
    try:
        from db import supabase_client
        import asyncio
        if not supabase_client.is_ready():
            return False

        transfer_amount = 25.0 if transferred else 0.0
        await asyncio.to_thread(
            supabase_client.client.table("voice_call_logs").insert({
                "vapi_call_id": call_id,
                "lead_id": lead_id,
                "duration_seconds": duration,
                "score_before_call": score_before,
                "score_after_call": score_after,
                "transferred": transferred,
                "transfer_amount": transfer_amount,
                "recording_url": recording_url,
                "transcript": transcript[:10000],  # cap at 10k chars
                "call_outcome": outcome,
            }).execute
        )
        log.info(f"Call logged to Supabase: {call_id} — outcome={outcome}")
        return True
    except Exception as e:
        log.warning(f"Supabase call log failed: {e}")
        return False
