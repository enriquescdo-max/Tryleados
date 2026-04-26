"""
LeadOS Carrier Appetite Scorer
FastAPI routes — drop into your existing Railway FastAPI app

POST /api/v1/carrier-score
Returns ranked carrier recommendations with appetite scores,
underwriting notes, and binding probability.

Carriers supported:
  Auto:  Progressive, GEICO, Root, National General, Bristol West
  Home:  Orion180, Swyfft, Sagesure, Lemonade
  Bundle: Auto + Home carrier pairing logic
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Literal
from enum import Enum
import json

router = APIRouter(prefix="/api/v1", tags=["carrier-score"])


# ─── Enums & Models ────────────────────────────────────────────────────────────

class PolicyType(str, Enum):
    AUTO    = "auto"
    HOME    = "home"
    RENTERS = "renters"
    BUNDLE  = "bundle"

class CreditTier(str, Enum):
    EXCELLENT = "excellent"   # 750+
    GOOD      = "good"        # 680-749
    FAIR      = "fair"        # 600-679
    POOR      = "poor"        # below 600
    UNKNOWN   = "unknown"

class LifeEvent(str, Enum):
    NEW_MOVE       = "new_move"
    CAR_PURCHASE   = "car_purchase"
    DEED_TRANSFER  = "deed_transfer"
    APT_LISTING    = "apt_listing"
    RENEWAL        = "renewal"
    NEW_HOMEOWNER  = "new_homeowner"

class CarrierScoreRequest(BaseModel):
    zip_code:        str                      = Field(..., description="5-digit ZIP code")
    policy_type:     PolicyType               = Field(..., description="Type of policy needed")
    credit_tier:     CreditTier               = Field(CreditTier.UNKNOWN, description="Applicant credit tier")
    life_event:      Optional[LifeEvent]      = Field(None, description="Triggering life event")
    vehicle_year:    Optional[int]            = Field(None, ge=1990, le=2026, description="Vehicle model year")
    vehicle_make:    Optional[str]            = Field(None, description="Vehicle make (e.g. Toyota)")
    prior_claims:    Optional[int]            = Field(0, ge=0, le=10, description="# of prior claims in 3 years")
    property_age:    Optional[int]            = Field(None, ge=0, le=150, description="Property age in years")
    roof_age:        Optional[int]            = Field(None, ge=0, le=50, description="Roof age in years")
    prior_lapses:    bool                     = Field(False, description="Any prior coverage lapses?")
    is_new_driver:   bool                     = Field(False, description="Newly licensed driver on policy?")
    dwelling_type:   Optional[str]            = Field("single_family", description="single_family|condo|mobile|apartment")

class CarrierResult(BaseModel):
    carrier:         str
    score:           int           # 0–100 appetite score
    rank:            int           # 1 = best fit
    market_type:     str           # "standard" | "non-standard" | "specialty"
    binding_prob:    float         # 0.0–1.0 estimated binding probability
    notes:           list[str]     # agent-facing underwriting notes
    flag:            Optional[str] # "recommended" | "caution" | "decline"

class CarrierScoreResponse(BaseModel):
    lead_profile:    dict
    results:         list[CarrierResult]
    compliance_note: str
    top_pick:        str
    strategy_note:   str


# ─── ZIP Intelligence ──────────────────────────────────────────────────────────

# Catastrophe zone classifications by ZIP prefix
# TX Gulf Coast / hail corridor / flood zones
CAT_ZONES = {
    # TX Gulf Coast / Harris County high-risk
    "770": "cat_high",   "771": "cat_high",  "772": "cat_high",
    "773": "cat_high",   "774": "cat_high",  "775": "cat_high",
    "776": "cat_high",   "777": "cat_high",
    # TX inland / Austin — moderate hail
    "786": "cat_med",    "787": "cat_med",   "788": "cat_med",
    # Standard
    "785": "standard",   "784": "standard",
}

# Known hard-market home insurance ZIPs in TX (coastal, flood-prone)
HARD_MARKET_ZIPS = {"77551","77550","77553","77554","77590","77591","77592","77650"}

# High-growth apartment corridors (Austin) — renters insurance sweet spot
RENTER_HOT_ZIPS = {"78701","78702","78703","78704","78705","78741","78745","78748"}

def get_cat_zone(zip_code: str) -> str:
    prefix3 = zip_code[:3]
    return CAT_ZONES.get(prefix3, "standard")

def get_state_from_zip(zip_code: str) -> str:
    prefix = int(zip_code[:3])
    if 750 <= prefix <= 799: return "TX"
    if 320 <= prefix <= 339: return "FL"
    if 300 <= prefix <= 319: return "GA"
    if 700 <= prefix <= 714: return "LA"
    if 870 <= prefix <= 884: return "AZ"
    if 890 <= prefix <= 898: return "NV"
    return "OTHER"


# ─── Scoring Logic ─────────────────────────────────────────────────────────────

# Base appetite per carrier × credit tier (0–100)
AUTO_CREDIT_APPETITE = {
    "Progressive":      {"excellent": 88, "good": 85, "fair": 80, "poor": 72, "unknown": 78},
    "GEICO":            {"excellent": 95, "good": 88, "fair": 68, "poor": 35, "unknown": 70},
    "Root":             {"excellent": 82, "good": 80, "fair": 78, "poor": 65, "unknown": 75},
    "National General": {"excellent": 72, "good": 74, "fair": 80, "poor": 85, "unknown": 78},
    "Bristol West":     {"excellent": 55, "good": 62, "fair": 78, "poor": 90, "unknown": 72},
}

HOME_BASE_APPETITE = {
    "Orion180": {"standard": 85, "cat_med": 75, "cat_high": 45},
    "Swyfft":   {"standard": 80, "cat_med": 72, "cat_high": 50},
    "Sagesure": {"standard": 78, "cat_med": 80, "cat_high": 72},
    "Lemonade": {"standard": 88, "cat_med": 60, "cat_high": 20},
}

AUTO_MARKET_TYPE = {
    "Progressive":      "standard",
    "GEICO":            "standard",
    "Root":             "standard",
    "National General": "non-standard",
    "Bristol West":     "non-standard",
}

HOME_MARKET_TYPE = {
    "Orion180": "specialty",
    "Swyfft":   "specialty",
    "Sagesure": "specialty",
    "Lemonade": "standard",
}


def score_auto_carrier(carrier: str, req: CarrierScoreRequest, cat_zone: str, state: str) -> CarrierResult:
    credit = req.credit_tier.value
    base = AUTO_CREDIT_APPETITE[carrier][credit]
    notes = []
    flag = None

    # Vehicle age adjustment
    if req.vehicle_year:
        age = 2025 - req.vehicle_year
        if age > 15:
            if carrier in ("GEICO", "Progressive"):
                base -= 8
                notes.append(f"Vehicle is {age} yrs old — preferred carriers prefer <15 yrs")
            else:
                base += 5
                notes.append(f"Older vehicle ({age} yrs) — non-std carriers more competitive")
        elif age <= 3:
            if carrier == "GEICO":
                base += 6
            notes.append(f"Late-model vehicle ({req.vehicle_year}) — full coverage expected")

    # Claims history
    if req.prior_claims and req.prior_claims > 0:
        penalty = req.prior_claims * (12 if carrier == "GEICO" else 6)
        base -= penalty
        notes.append(f"{req.prior_claims} prior claim(s) — {'significant penalty' if carrier == 'GEICO' else 'moderate penalty'} applied")
        if req.prior_claims >= 3:
            flag = "caution"

    # Prior lapse
    if req.prior_lapses:
        if carrier in ("GEICO",):
            base -= 20
            notes.append("Prior lapse — GEICO is strict on continuous coverage")
        else:
            base -= 8
            notes.append("Prior lapse noted — verify continuous coverage gap length")

    # New driver
    if req.is_new_driver:
        if carrier in ("Bristol West", "National General"):
            base += 8
            notes.append("New driver — non-standard market is more accepting")
        else:
            base -= 10
            notes.append("New driver on policy — expect higher premium")

    # Life event boost
    if req.life_event in (LifeEvent.CAR_PURCHASE, LifeEvent.NEW_MOVE):
        base += 5
        notes.append("Life event trigger — motivated buyer, higher close probability")

    # State-specific
    if state == "TX":
        notes.append("TX market — verify SR-22 requirements if applicable")

    base = max(0, min(100, base))
    binding_prob = round(base / 100 * 0.92, 2)

    if base >= 80 and not flag:
        flag = "recommended"
    elif base < 50:
        flag = "decline"
    else:
        flag = flag or None

    return CarrierResult(
        carrier=carrier,
        score=base,
        rank=0,  # set after sorting
        market_type=AUTO_MARKET_TYPE[carrier],
        binding_prob=binding_prob,
        notes=notes if notes else ["No flags — standard appetite"],
        flag=flag,
    )


def score_home_carrier(carrier: str, req: CarrierScoreRequest, cat_zone: str, state: str) -> CarrierResult:
    base = HOME_BASE_APPETITE[carrier][cat_zone]
    notes = []
    flag = None

    # Hard market ZIP
    if req.zip_code in HARD_MARKET_ZIPS:
        base -= 20
        notes.append("High-risk coastal ZIP — limited carrier options, expect E&S market")
        flag = "caution"

    # Property age
    if req.property_age is not None:
        if req.property_age > 40:
            if carrier == "Lemonade":
                base -= 25
                notes.append("Lemonade prefers newer construction (<20 yrs)")
            else:
                base -= 10
                notes.append(f"Property age {req.property_age} yrs — may require inspection or renovation notes")
        elif req.property_age > 25:
            base -= 5
            notes.append(f"Property age {req.property_age} yrs — standard underwriting applies")

    # Roof age
    if req.roof_age is not None:
        if req.roof_age > 20:
            base -= 18
            notes.append(f"Roof age {req.roof_age} yrs — most carriers require <20 yrs or ACV settlement")
            flag = "caution"
        elif req.roof_age > 15:
            base -= 8
            notes.append(f"Roof age {req.roof_age} yrs — verify material and condition")

    # Dwelling type
    if req.dwelling_type == "mobile":
        if carrier in ("Orion180", "Swyfft"):
            base -= 30
            notes.append("Mobile/manufactured home — not eligible for this carrier")
            flag = "decline"
        else:
            base -= 10
            notes.append("Mobile home — confirm specialty coverage available")

    # Life event
    if req.life_event in (LifeEvent.DEED_TRANSFER, LifeEvent.NEW_HOMEOWNER, LifeEvent.NEW_MOVE):
        base += 8
        notes.append("New purchase/transfer — motivated buyer, binding deadline urgency")

    # Claims
    if req.prior_claims and req.prior_claims > 1:
        base -= req.prior_claims * 8
        notes.append(f"{req.prior_claims} prior claims — home carriers scrutinize loss history")
        if req.prior_claims >= 3:
            flag = "caution"

    # Sagesure advantage in cat zones
    if carrier == "Sagesure" and cat_zone in ("cat_med", "cat_high"):
        notes.append("Sagesure specializes in non-coastal TX — competitive in cat zones")

    base = max(0, min(100, base))
    binding_prob = round(base / 100 * 0.88, 2)

    if base >= 75 and not flag:
        flag = "recommended"
    elif base < 40:
        flag = "decline"
    else:
        flag = flag or None

    return CarrierResult(
        carrier=carrier,
        score=base,
        rank=0,
        market_type=HOME_MARKET_TYPE[carrier],
        binding_prob=binding_prob,
        notes=notes if notes else ["No flags — standard appetite"],
        flag=flag,
    )


def score_renters_carrier(carrier: str, req: CarrierScoreRequest, cat_zone: str, state: str) -> CarrierResult:
    """Renters insurance — Lemonade and Sagesure are primary. Simplified scoring."""
    base_map = {"Lemonade": 88, "Sagesure": 75}
    base = base_map.get(carrier, 60)
    notes = []

    if req.zip_code in RENTER_HOT_ZIPS:
        base += 8
        notes.append("Austin high-density renter corridor — strong conversion expected")

    if req.life_event == LifeEvent.APT_LISTING:
        base += 10
        notes.append("Apartment listing trigger — lease signing urgency, ideal timing for renters pitch")

    if carrier == "Lemonade":
        notes.append("Lemonade: instant bind, $5/mo entry — use for price-sensitive leads")
    else:
        notes.append("Sagesure: broader coverage options, better for personal property riders")

    base = min(100, base)
    return CarrierResult(
        carrier=carrier,
        score=base,
        rank=0,
        market_type="standard" if carrier == "Lemonade" else "specialty",
        binding_prob=round(base / 100 * 0.94, 2),
        notes=notes,
        flag="recommended" if base >= 80 else None,
    )


# ─── Route ────────────────────────────────────────────────────────────────────

@router.post("/carrier-score", response_model=CarrierScoreResponse)
async def score_carriers(req: CarrierScoreRequest):
    """
    Score all applicable carriers for a given lead profile.
    Returns ranked recommendations with underwriting notes.
    """
    if len(req.zip_code) != 5 or not req.zip_code.isdigit():
        raise HTTPException(status_code=422, detail="ZIP code must be 5 digits")

    cat_zone = get_cat_zone(req.zip_code)
    state    = get_state_from_zip(req.zip_code)

    results: list[CarrierResult] = []

    if req.policy_type in (PolicyType.AUTO, PolicyType.BUNDLE):
        for carrier in AUTO_CREDIT_APPETITE:
            results.append(score_auto_carrier(carrier, req, cat_zone, state))

    if req.policy_type in (PolicyType.HOME, PolicyType.BUNDLE):
        for carrier in HOME_BASE_APPETITE:
            results.append(score_home_carrier(carrier, req, cat_zone, state))

    if req.policy_type == PolicyType.RENTERS:
        for carrier in ("Lemonade", "Sagesure"):
            results.append(score_renters_carrier(carrier, req, cat_zone, state))

    # Sort by score, assign ranks
    results.sort(key=lambda r: r.score, reverse=True)
    for i, r in enumerate(results):
        r.rank = i + 1

    top = results[0].carrier if results else "Unknown"

    # Strategy note based on profile
    strategy_note = _build_strategy_note(req, results, cat_zone, state)

    compliance_note = (
        "TX: Insurance solicitation governed by TDI. Verify TCPA consent before dialing. "
        "No prior written consent required for property/casualty inquiries under TX Ins. Code §541."
    ) if state == "TX" else (
        "Verify state-specific solicitation rules before outreach. Check DNC registry."
    )

    return CarrierScoreResponse(
        lead_profile={
            "zip": req.zip_code,
            "state": state,
            "cat_zone": cat_zone,
            "policy_type": req.policy_type,
            "credit_tier": req.credit_tier,
            "life_event": req.life_event,
        },
        results=results,
        top_pick=top,
        compliance_note=compliance_note,
        strategy_note=strategy_note,
    )


def _build_strategy_note(req: CarrierScoreRequest, results: list[CarrierResult], cat_zone: str, state: str) -> str:
    if not results:
        return "No carriers scored — check policy type and ZIP."

    top = results[0]
    second = results[1] if len(results) > 1 else None

    notes = []

    # Life event urgency
    if req.life_event == LifeEvent.NEW_MOVE:
        notes.append("Lead just moved — coverage gap window is open. Contact within 24hrs.")
    elif req.life_event == LifeEvent.CAR_PURCHASE:
        notes.append("Dealership purchase likely requires same-day bind. Lead is hot.")
    elif req.life_event == LifeEvent.DEED_TRANSFER:
        notes.append("New homeowner — 30-day closing window. Bundle opportunity with auto.")
    elif req.life_event == LifeEvent.APT_LISTING:
        notes.append("Apartment listing — renters insurance concierge play. Partner referral opportunity.")

    # Carrier strategy
    if top.market_type == "non-standard":
        notes.append(f"Lead skews non-standard — lead with {top.carrier}, have {second.carrier if second else 'backup'} ready.")
    else:
        notes.append(f"Start quote with {top.carrier} (score: {top.score}). Competitive market — present 2 options.")

    # Cat zone warning
    if cat_zone == "cat_high":
        notes.append("High-cat ZIP — home carriers are restricted. Set E&S expectations upfront.")

    # Bundle opportunity
    if req.policy_type == PolicyType.BUNDLE:
        notes.append("Bundle discount potential — quote auto + home together for 12-18% discount.")

    return " ".join(notes)


# ─── Health check ─────────────────────────────────────────────────────────────

@router.get("/carrier-score/health")
async def health():
    return {"status": "ok", "carriers_loaded": len(AUTO_CREDIT_APPETITE) + len(HOME_BASE_APPETITE)}
