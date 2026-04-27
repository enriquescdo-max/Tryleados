import httpx
import asyncio
import os
from typing import List, Dict

APIFY_BASE = "https://api.apify.com/v2"
APIFY_TOKEN = os.getenv("APIFY_API_TOKEN", "")

FB_MARKETPLACE_CONFIG = {
    "searchQuery": "car",
    "location": "Austin, TX",
    "maxItems": 30,
    "priceMax": 25000
}

CRAIGSLIST_CONFIG = {
    "startUrls": [{"url": "https://austin.craigslist.org/search/apa"}],
    "maxItems": 40,
    "includeContactInfo": True
}

REDDIT_CONFIG = {
    "startUrls": [
        {"url": "https://www.reddit.com/r/Austin/search/?q=moving+to+austin&sort=new"},
        {"url": "https://www.reddit.com/r/Austin/search/?q=just+moved&sort=new"}
    ],
    "maxItems": 20
}


async def run_actor(actor_id: str, run_input: dict) -> List[Dict]:
    async with httpx.AsyncClient(timeout=120) as client:
        run_resp = await client.post(
            f"{APIFY_BASE}/acts/{actor_id}/runs",
            params={"token": APIFY_TOKEN},
            json={"runInput": run_input}
        )
        run_resp.raise_for_status()
        run_id = run_resp.json()["data"]["id"]

        status_resp = None
        for _ in range(18):
            await asyncio.sleep(5)
            status_resp = await client.get(
                f"{APIFY_BASE}/acts/{actor_id}/runs/{run_id}",
                params={"token": APIFY_TOKEN}
            )
            status = status_resp.json()["data"]["status"]
            if status == "SUCCEEDED":
                break
            if status in ["FAILED", "ABORTED", "TIMED-OUT"]:
                return []

        if not status_resp:
            return []

        dataset_id = status_resp.json()["data"]["defaultDatasetId"]
        items_resp = await client.get(
            f"{APIFY_BASE}/datasets/{dataset_id}/items",
            params={"token": APIFY_TOKEN, "limit": 50}
        )
        return items_resp.json()


async def scrape_all_sources() -> List[Dict]:
    results = await asyncio.gather(
        run_actor("apify/facebook-marketplace-scraper", FB_MARKETPLACE_CONFIG),
        run_actor("apify/craigslist-scraper", CRAIGSLIST_CONFIG),
        run_actor("apify/reddit-scraper", REDDIT_CONFIG),
        return_exceptions=True
    )

    normalized = []

    if isinstance(results[0], list):
        for item in results[0]:
            normalized.append({
                "source": "facebook_marketplace",
                "raw_name": item.get("sellerName", "Unknown"),
                "raw_contact": item.get("sellerProfileUrl", ""),
                "raw_text": f"{item.get('title','')} — {item.get('description','')} — ${item.get('price','')}",
                "location": "Austin, TX"
            })

    if isinstance(results[1], list):
        for item in results[1]:
            normalized.append({
                "source": "apartment_listing",
                "raw_name": item.get("posterName", "Unknown"),
                "raw_contact": item.get("email", item.get("phone", "")),
                "raw_text": f"{item.get('title','')} — {item.get('body','')}",
                "location": item.get("neighborhood", "Austin, TX")
            })

    if isinstance(results[2], list):
        for item in results[2]:
            normalized.append({
                "source": "social_post",
                "raw_name": item.get("author", "Unknown"),
                "raw_contact": f"reddit.com/u/{item.get('author','')}",
                "raw_text": f"{item.get('title','')} — {item.get('body','')}",
                "location": "Austin, TX"
            })

    return normalized
