"""Call, lead, response-time, and consent figures. Read only."""

import csv
import io

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from services.agency_store import get_store

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


def _snapshot():
    return get_store().metrics()


@router.get("")
@router.get("/")
async def metrics_json():
    return _snapshot()


@router.get(".csv")
@router.get("/export.csv")
async def metrics_csv():
    snapshot = _snapshot()
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["calls", "leads", "median_response_seconds", "consent_rate"])
    writer.writerow([
        snapshot["calls"],
        snapshot["leads"],
        "" if snapshot["median_response_seconds"] is None else snapshot["median_response_seconds"],
        snapshot["consent_rate"],
    ])
    return PlainTextResponse(buffer.getvalue(), media_type="text/csv")
