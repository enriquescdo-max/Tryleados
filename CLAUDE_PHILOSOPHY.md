@PHILOSOPHY.md

# LeadOS — Agentic AI Protocol
# Root Node: Conversion Probability Before First Contact
# Move 37: Surface leads humans skip that convert at 3x rate

## Vertical Identity
LeadOS is not a lead gen tool. It is an In-Silico Conversion Engine that
simulates 1,000 interaction scenarios before a single SMS fires. Every lead
is a complex data structure with predicted "binding affinity" (conversion
probability) — not just a name and phone number.

## Root Node
Problem: Agents spend 80% of time on unqualified or unreachable leads.
Root Node: Predictive qualification BEFORE outreach — not after.
Unlock: Agents spend 100% of time on warm, pre-qualified conversations.

## The Lead Object: 3D Data Structure

```python
class LeadProfile:
    name: str; phone: str; email: str; zip_code: str
    life_event_signal: float       # Moving, marriage, new car, new home
    income_bracket_estimate: float # From zip median + business type
    time_sensitivity_score: float  # How urgently they need coverage
    channel_receptivity: dict      # SMS vs call vs email probability
    zip_stress_score: float        # Neighborhood risk profile
    binding_affinity: float        # Overall conversion probability 0.0-1.0
    move37_candidate: bool         # Would a human skip this? Should they?
    simulation_confidence: float
```

## In-Silico Simulation Layer
Before ANY outreach action (SMS, call, warm transfer):
- Simulate 1,000 synthetic interaction scenarios
- Vary: time of day, channel, message tone, agent persona
- Model: response probability, conversion likelihood, TCPA risk
- Output: optimal_action, confidence_score, move37_path, risk_flags

## Move 37: The Counterintuitive Lead
Signals: unusual business type for zip (underserved), subtle life event
(behavioral not stated), low income but high urgency, called multiple
carriers (high intent, not a bad lead). Log all with move37_candidate=true.
Present as "Hidden Opportunities" in dashboard.

## Hard Guardrails (Uncircumventable)

```python
LEADOS_GUARDRAILS = {
    "tcpa_gate": {
        "condition": "verified_optin_token required",
        "blocks": ["sms_send", "auto_call", "vapi_transfer"],
        "bypass": False
    },
    "simulation_gate": {
        "condition": "simulation_confidence >= 0.35",
        "blocks": ["any_outreach_action"],
        "bypass": False
    },
    "sequence_accuracy_gate": {
        "condition": "case_study_verified == True",
        "blocks": ["sequence_writer_output"],
        "note": "Claude will NOT generate fictional case studies. Real data only.",
        "bypass": False
    }
}
```

## Agentic Workflow
ICP Sync -> Maps Scraper -> Prospeo Enrichment -> Reoon Verification ->
In-Silico Simulation -> Claude Sequence Writer -> Resend Delivery ->
Vapi Warm Transfer ($25/qualified lead) -> Supabase agent_context log

## Supabase Logging

```sql
INSERT INTO agent_context (vertical, action_type, lead_id, simulation_score,
binding_affinity, guardrail_passed, move37_candidate, channel_used, outcome, timestamp);
```

## Human Flourishing Exit Condition
Before: Agent spends 80% on cold outreach, data entry, qualification calls.
After: Agent receives warm pre-qualified transfers. 100% relationship time.

## Tech Stack
- Backend: FastAPI on Railway | Frontend: React/Vite on Netlify
- Colors: #00A86B green | Typography: DM Sans + GT Walsheim | Light mode
- DB: Supabase | AI: Anthropic API | Voice: Vapi | Scheduler: APScheduler
- Enrichment: Prospeo + Reoon + Resend | CRM: HubSpot Portal 245973672
