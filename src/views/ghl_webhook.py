import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from database.queries.contract import (
    create_contract,
    update_contract,
    get_contract_by_ghl_contract_id,
)
from database.queries.user import get_or_create_user

router = APIRouter(
    prefix="/ghl-contract-wh",
    tags=["webhooks", "ghl"],
)

logger = logging.getLogger(__name__)

# Single default user for all contracts created/updated by the GHL webhook.
GHL_WEBHOOK_USER_EMAIL = "gohilevel@nonexist.com"


@router.post("/")
async def ghl_contract_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Webhook payload: id (GHL contract id), name, email, phone, zipCode, sourceOfHeat.
    If id is present and matches ghl_contract_id, update that contract; else create new.
    """
    payload = await request.json()
    print(payload)
    logger.info("GHL contract webhook payload: %s", payload)

    ghl_id = payload.get("id")
    email = (payload.get("email") or "").strip() or None
    zip_code = payload.get("zipCode")
    source_of_heat = payload.get("sourceOfHeat")
    if zip_code is not None and str(zip_code).strip() == "":
        zip_code = None
    if source_of_heat is not None and str(source_of_heat).strip() == "":
        source_of_heat = None

    # Use single default user as creator for all webhook-created contracts.
    ghl_user = await get_or_create_user(
        db=db,
        email=GHL_WEBHOOK_USER_EMAIL,
        username="GHL Webhook",
    )

    ghl_id_str = str(ghl_id).strip() if ghl_id is not None else None

    if ghl_id_str:
        existing = await get_contract_by_ghl_contract_id(db, ghl_id_str)
        if existing:
            await update_contract(
                db=db,
                contract_id=existing.id,
                user_id=ghl_user.id,
                zip=zip_code,
                fuel_type=source_of_heat,
                ghl_contract_id=ghl_id_str,
                client_email=email,
            )
            logger.info("Updated contract %s from GHL id %s", existing.id, ghl_id_str)
        else:
            await create_contract(
                db=db,
                user_id=ghl_user.id,
                zip=zip_code,
                fuel_type=source_of_heat,
                ghl_contract_id=ghl_id_str,
                client_email=email,
            )
            logger.info("Created new contract for GHL id %s", ghl_id_str)
    else:
        await create_contract(
            db=db,
            user_id=ghl_user.id,
            zip=zip_code,
            fuel_type=source_of_heat,
            client_email=email,
        )
        logger.info("Created new contract (no GHL id)")

    return Response(status_code=200)
