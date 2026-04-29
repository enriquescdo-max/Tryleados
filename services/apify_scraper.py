"""
LeadOS Apify Scraper
Uses Google Search Scraper (free, reliable) to find insurance leads.
Searches for: Austin/Houston movers, car buyers, new homeowners on Reddit/Craigslist.
"""

import httpx
import asyncio
import os
import logging
from typing import List, Dict

log = logging.getLogger("LeadOS.Apify")

APIFY_BASE  = "https://api.apify.com/v2"
APIFY_TOKEN = os.getenv("APIFY_API_TOKEN", "")

# Using Google Search Scraper — reliable, no special permissions needed
GOOGLE_SCRAPER_ID = "apify/google-search-scraper"

# Insurance lead search queries targeting Austin/Houston
LEAD_SEARCHES = [
    # Renters / movers
    'site:reddit.com "moving to Austin" OR "just moved to Austin" insurance renters',
    'site:craigslist.org "austin" "apartment" "available"',
    # Car buyers
    'site:reddit.com "Austin" "just bought a car" OR "buying a car" insurance',
    # New homeowners
    'site:reddit.com "Austin" "just closed" OR "new home" OR "just bought a house" insurance',
    # Houston
    'site:reddit.com "moving to Houston" OR "just moved to Houston" insurance renters',
]


async def run_google_search(query: str, max_results: int = 20) -> List[Dict]:
    """Run Apify Google Search Scraper for a single query."""
    if not APIFY_TOKEN:
        log.warning("APIFY_API_TOKEN not set")
        return []

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            # Start the actor run
            run_resp = await client.post(
                f"{APIFY_BASE}/acts/{GOOGLE_SCRAPER_ID}/runs",
                params={"token": APIFY_TOKEN},
                json={
                    "queries": query,
                    "maxPagesPerQuery": 1,
                    "resultsPerPage": max_results,
                    "mobileResults": False,
                    "languageCode": "en",
                    "countryCode": "us",
                }
            )

            if run_resp.status_code not in (200, 201):
                log.error(f"Apify start failed: {run_resp.status_code} {run_resp.text[:100]}")
                return []

            run_id = run_resp.json()["data"]["id"]
            log.info(f"Apify run started: {run_id} for query: {query[:50]}")

            # Poll for completion
            for _ in range(24):  # up to 2 minutes
                await asyncio.sleep(5)
                status_resp = await client.get(
                    f"{APIFY_BASE}/actor-runs/{run_id}",
                    params={"token": APIFY_TOKEN}
                )
                status = status_resp.json()["data"]["status"]
                if status == "SUCCEEDED":
                    break
                if status in ("FAILED", "ABORTED", "TIMED-OUT"):
                    log.warning(f"Apify run {run_id} ended with status: {status}")
                    return []

            # Get results
            dataset_id = status_resp.json()["data"]["defaultDatasetId"]
            items_resp = await client.get(
                f"{APIFY_BASE}/datasets/{dataset_id}/items",
                params={"token": APIFY_TOKEN, "limit": max_results}
            )

            items = items_resp.json()
            log.info(f"Apify returned {len(items)} results for: {query[:50]}")
            return items if isinstance(items, list) else []

    except Exception as e:
        log.error(f"Apify run_google_search error: {e}")
        return []


def normalize_google_result(item: dict, query: str) -> dict:
    """Convert Google Search result into LeadOS lead format."""
    url = item.get("url") or item.get("link") or ""
    title = item.get("title") or ""
    description = item.get("description") or item.get("snippet") or ""
    text = f"{title} — {description}"

    # Determine source and life event
    if "reddit.com" in url:
        source = "Reddit"
        if "moving" in text.lower() or "moved" in text.lower():
            life_event = "new_move"
            insurance_type = "renters"
        elif "car" in text.lower() or "vehicle" in text.lower():
            life_event = "car_purchase"
            insurance_type = "auto"
        elif "home" in text.lower() or "house" in text.lower() or "closed" in text.lower():
            life_event = "new_homeowner"
            insurance_type = "home"
        else:
            life_event = "new_move"
            insurance_type = "renters"
    elif "craigslist.org" in url:
        source = "Craigslist"
        life_event = "apt_listing"
        insurance_type = "renters"
    else:
        source = "Google Search"
        life_event = "new_move"
        insurance_type = "renters"

    # Determine location
    if "Houston" in text or "houston" in text:
        location = "Houston, TX"
    else:
        location = "Austin, TX"

    return {
        "source": source,
        "raw_name": "Lead from " + source,
        "raw_contact": url,
        "raw_text": text[:1000],
        "location": location,
        "life_event": life_event,
        "insurance_type": insurance_type,
        "source_url": url,
    }


async def scrape_all_sources() -> List[Dict]:
    """Run all search queries and return normalized leads."""
    if not APIFY_TOKEN:
        log.warning("APIFY_API_TOKEN not set — returning empty")
        return []

    log.info(f"Starting Apify scrape with {len(LEAD_SEARCHES)} queries")

    # Run searches in parallel (max 3 at a time to avoid rate limits)
    all_leads = []
    for i in range(0, len(LEAD_SEARCHES), 3):
        batch = LEAD_SEARCHES[i:i+3]
        results = await asyncio.gather(
            *[run_google_search(q, max_results=15) for q in batch],
            return_exceptions=True
        )
        for j, result in enumerate(results):
            if isinstance(result, list):
                for item in result:
                    lead = normalize_google_result(item, batch[j])
                    if lead.get("raw_text") and len(lead["raw_text"]) > 20:
                        all_leads.append(lead)

        await asyncio.sleep(2)  # Brief pause between batches

    log.info(f"Apify scrape complete: {len(all_leads)} raw leads")
    return all_leads
