import logging

from fastapi import APIRouter, Request
from fastapi.responses import Response

router = APIRouter(
    prefix="/ghl-contract-wh",
    tags=["webhooks", "ghl"],
)

logger = logging.getLogger(__name__)


@router.post("")
async def ghl_contract_webhook(request: Request):
    """Webhook with flexible payload. Logs payload and returns 200 OK."""
    payload = await request.json()
    print(payload)
    logger.info("GHL contract webhook payload: %s", payload)
    return Response(status_code=200)
