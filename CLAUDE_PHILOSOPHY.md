@PHILOSOPHY.md

# LeadOS — Agentic AI Protocol
# Root Node: Conversion Probability Before First Contact
# Move 37: Surface leads humans skip that convert at 3x rate

## Vertical Identity
LeadOS is not a lead gen tool. It is an In-Silico Conversion Engine that
simulates 1,000 interaction scenarios before a single SMS fires. Every lead
is a complex data structure with predicted binding affinity (conversion
probability) — not just a name and phone number.

## Root Node
Problem: Agents spend 80% of time on unqualified or unreachable leads.
Root Node: Predictive qualification BEFORE outreach — not after.
Unlock: Agents spend 100% of time on warm, pre-qualified conversations.

## The Lead Object: 3D Data Structure
class LeadProfile:
    name, phone, email, zip_code: str
    life_event_signal: float       # Moving, marriage, new car, new home
    income_bracket_estimate: float # From zip median + business type
    time_sensitivity_score: float  # How urgently they need coverage
    channel_receptivity: dict      # SMS vs call vs email probability
    zip_stress_score: float        # Neighborhood risk profile
    binding_affinity: float        # Conversion probability 0.0-1.0
    move37_candidate: bool         # Would a human skip this? Should they?
    simulation_confidence: float

## In-Silico Simulation Layer
Before ANY outreach action (SMS, call, warm transfer):
- Simulate 1,000 synthetic interaction scenarios
- Vary: time of day, channel, message tone, agent persona
- Model: response probability, conversion likelihood, TCPA risk
- Output: optimal_action, confidence_score, move37_path, risk_flags

## Move 37: The Counterintuitive Lead
Signals: unusual business type for zip (underserved market), subtle life
event (behavioral not stated), low income but high urgency, called multiple
carriers (high intent, not a bad lead). Log all with move37_candidate=true.
Present as "Hidden Opportunities" in the dashboard.

## Hard Guardrails (Uncircumventable)
LEADOS_GUARDRAILS = {
    "tcpa_gate": {
        condition: "verified_optin_token required",
        blocks: ["sms_send", "auto_call", "vapi_transfer"],
        bypass: False  # NEVER
    },
    "simulation_gate": {
        condition: "simulation_confidence >= 0.35",
        blocks: ["any_outreach_action"],
        bypass: False  # NEVER
    },
    "sequence_accuracy_gate": {
        condition: "case_study_verified == True",
        blocks: ["sequence_writer_output"],
        note: "Claude will NOT generate fictional case studies. Real data only.",
        bypass: False  # NEVER
    }
}

## Agentic Workflow
ICP Sync Agent -> Google Maps Scraper
-> Prospeo Enrichment -> Lead Object construction
-> Reoon Verification -> Email/phone validation
-> In-Silico Simulation (1,000 scenarios)
-> [only if simulation_confidence >= 0.35]
-> Claude Sequence Writer (real case studies only)
-> Resend Delivery -> Email sequence fires
-> Vapi Warm Transfer ($25/qualified lead)
-> Supabase agent_context -> Full audit log every step

## Supabase Logging
INSERT INTO agent_context (
    vertical, action_type, lead_id, simulation_score,
    binding_affinity, guardrail_passed, move37_candidate,
    channel_used, outcome, timestamp
);

## Human Flourishing Exit Condition
Before: Agent spends 80% on cold outreach, data entry, qualification calls.
After: Agent receives warm pre-qualified transfers. 100% relationship time.

## Tech Stack
Backend: FastAPI on Railway
Frontend: React/Vite on Netlify — #00A86B green, DM Sans + GT Walsheim, light mode
DB: Supabase
AI: Anthropic API (claude-sonnet-4-20250514)
Voice: Vapi warm transfers at $25/qualified lead
Scheduler: APScheduler
Enrichment: Prospeo + Reoon + Resend (Apollo replacement stack)
CRM: HubSpot Portal 245973672 (Owner ID 91195509)
