"""Gates for anything that would contact a person.

Automatic outreach, AI outbound calls, and bulk send are off unless the owner
sets an explicit flag. Flags do not replace consent. TCPA and Texas rules
require prior express written consent for AI or autodialed calls and for
marketing texts. A scraped post is not consent.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

_ON = {"1", "true", "yes", "on"}


def _flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in _ON


def auto_outreach_enabled() -> bool:
    return _flag("AUTO_OUTREACH_ENABLED") or _flag("ENABLE_AUTO_OUTREACH")


def ai_outbound_enabled() -> bool:
    return _flag("AI_OUTBOUND_CALLS_ENABLED")


def outbound_send_enabled() -> bool:
    return _flag("OUTBOUND_SEND_ENABLED")


@dataclass(frozen=True)
class ContactDecision:
    allowed: bool
    reason: str


def _active(consents: list[dict] | None) -> list[dict]:
    return [c for c in (consents or []) if not c.get("revoked_at")]


def _has_written(consents: list[dict] | None, channels: set[str]) -> bool:
    for row in _active(consents):
        if not row.get("written"):
            continue
        if row.get("channel") in channels or row.get("scope") in channels:
            return True
    return False


def _has_callback_consent(consents: list[dict] | None) -> bool:
    for row in _active(consents):
        if row.get("scope") == "owner_callback":
            return True
        if row.get("channel") == "call" and row.get("source") in {"call", "web_form", "dm", "owner_recorded"}:
            return True
    return False


def contact_decision(*, channel: str, consents: list[dict] | None = None) -> ContactDecision:
    """Decide whether this process may contact someone. Default is no."""
    if channel == "ai_call":
        if not ai_outbound_enabled():
            return ContactDecision(
                False,
                "AI outbound calls are off. The owner places callbacks. This path does not dial.",
            )
        if not _has_written(consents, {"call", "ai_call"}):
            return ContactDecision(
                False,
                "Prior express written consent is required for an AI or autodialed call.",
            )
        return ContactDecision(True, "Written call consent is on file and AI outbound is explicitly enabled.")

    if channel == "sms":
        if not outbound_send_enabled():
            return ContactDecision(False, "Outbound texting is off.")
        if not _has_written(consents, {"sms", "marketing_sms"}):
            return ContactDecision(
                False,
                "Prior express written consent is required for a marketing text.",
            )
        return ContactDecision(True, "Written SMS consent is on file and outbound texting is explicitly enabled.")

    if channel == "email":
        if not auto_outreach_enabled():
            return ContactDecision(False, "Automatic email outreach is off.")
        if not any(c.get("channel") == "email" for c in _active(consents)):
            return ContactDecision(False, "Email consent is not on file.")
        return ContactDecision(True, "Email consent is on file and automatic outreach is explicitly enabled.")

    if channel == "bulk":
        if not auto_outreach_enabled():
            return ContactDecision(False, "Bulk send is disabled.")
        return ContactDecision(
            False,
            "Bulk send stays off. Contact one consented person at a time, and only after you approve the message.",
        )

    if channel == "owner_callback":
        if _has_callback_consent(consents):
            return ContactDecision(True, "Callback consent is on file. The owner places this call. AI does not dial.")
        return ContactDecision(False, "No consent on file for a callback.")

    return ContactDecision(False, f"Refusing unknown contact channel: {channel}")
