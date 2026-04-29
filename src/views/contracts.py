from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    UploadFile,
    File,
    Query,
)
from datetime import datetime, timedelta
from typing import Literal, Optional
from urllib.parse import urlencode
from pydantic import AliasChoices, BaseModel, Field

from database.connection import get_db
from database.queries.contract import (
    create_contract,
    update_contract,
    get_contract_by_id,
    get_auditor_schedule_for_date,
    list_contracts as list_contracts_query,
    update_contract_status,
    get_contract_statistics,
    delete_contract,
)
from sqlalchemy.ext.asyncio import AsyncSession

from services.s3_service import S3Service
from services.ses_service import SESService


router = APIRouter(
    prefix="/contracts",
    tags=["contracts"],
)


def format_datetime(date_obj, time_obj) -> Optional[str]:
    """Format date and time objects into a single readable string (e.g., 'January 21, 2026 at 2:30 PM')."""
    if not date_obj:
        return None

    date_str = date_obj.strftime("%B %d, %Y")

    if time_obj:
        time_str = time_obj.strftime("%I:%M %p").lstrip("0")
        return f"{date_str} at {time_str}"

    return date_str


def format_datetime_range(
    date_obj, start_time_obj, end_time_obj
) -> Optional[str]:
    """Format date with start and end time as a single string (e.g., 'February 19, 2026 at 9:00 AM – 10:00 AM')."""
    if not date_obj:
        return None
    date_str = date_obj.strftime("%B %d, %Y")
    if start_time_obj and end_time_obj:
        start_str = start_time_obj.strftime("%I:%M %p").lstrip("0")
        end_str = end_time_obj.strftime("%I:%M %p").lstrip("0")
        return f"{date_str} at {start_str} – {end_str}"
    if start_time_obj:
        start_str = start_time_obj.strftime("%I:%M %p").lstrip("0")
        return f"{date_str} at {start_str}"
    return date_str


def build_google_calendar_event_url(
    *,
    title: str,
    start_dt: datetime,
    end_dt: datetime,
    details: str = "",
    location: str = "",
) -> str:
    def _fmt(dt: datetime) -> str:
        # Use a "floating" time (no timezone suffix) so Google Calendar treats it as local time.
        return dt.strftime("%Y%m%dT%H%M%S")

    params = {
        "action": "TEMPLATE",
        "text": title,
        "dates": f"{_fmt(start_dt)}/{_fmt(end_dt)}",
    }
    if details:
        params["details"] = details
    if location:
        params["location"] = location
    return "https://calendar.google.com/calendar/render?" + urlencode(params)


class ContractRequest(BaseModel):
    user_id: str
    contract_id: Optional[str] = None
    zip: Optional[str] = None
    city: Optional[str] = None
    street_address: Optional[str] = None
    notes: Optional[str] = None
    fuel_type: Optional[str] = None
    client_name: Optional[str] = None
    client_email: Optional[str] = None
    phone_number: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("phone_number", "client_phone"),
    )
    hancock_project_id: Optional[str] = None
    auditor_id: Optional[str] = None
    multifamily_values: Optional[list[str]] = None
    date: Optional[str] = None  # ISO format date string
    start_at_time: Optional[str] = None  # ISO format time string
    end_at_time: Optional[str] = None  # ISO format time string
    google_meet_url: Optional[str] = None
    inspection_doc: Optional[str] = None
    invoice_doc: Optional[str] = None
    form_stage: Optional[str] = None
    r2: Optional[bool] = None


class ContractResponse(BaseModel):
    id: str
    user_id: str
    zip: Optional[str] = None
    city: Optional[str] = None
    street_address: Optional[str] = None
    notes: Optional[str] = None
    fuel_type: Optional[str] = None
    sponsored_by: Optional[str] = None
    hancock_project_id: Optional[str] = None
    auditor_id: Optional[str] = None
    client_name: Optional[str] = None
    client_email: Optional[str] = None
    phone_number: Optional[str] = None
    multifamily_values: Optional[list[str]] = None
    date: Optional[str] = None
    start_at_time: Optional[str] = None
    end_at_time: Optional[str] = None
    formatted_datetime: Optional[str] = None
    google_meet_url: Optional[str] = None
    meeting_url: Optional[str] = None
    inspection_doc: Optional[str] = None
    invoice_doc: Optional[str] = None
    form_stage: str
    r2: bool
    status: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class ContractListItem(BaseModel):
    id: str
    zip: Optional[str] = None
    city: Optional[str] = None
    street_address: Optional[str] = None
    notes: Optional[str] = None
    fuel_type: Optional[str] = None
    sponsored_by: Optional[str] = None
    hancock_project_id: Optional[str] = None
    auditor_id: Optional[str] = None
    client_name: Optional[str] = None
    phone_number: Optional[str] = None
    client_email: Optional[str] = None
    formatted_datetime: Optional[str] = None
    meeting_url: Optional[str] = None
    inspection_doc: Optional[str] = None
    invoice_doc: Optional[str] = None
    form_stage: str
    r2: bool
    status: str

    class Config:
        from_attributes = True


class PatchContractStatusRequest(BaseModel):
    status: Literal["cancelled", "completed"]


class PaginatedContractListResponse(BaseModel):
    items: list[ContractListItem]
    total: int
    page: int
    limit: int
    total_pages: int

    class Config:
        from_attributes = True


class SponsoredByStats(BaseModel):
    total: int
    fuel: dict[str, int]


class ProceedReasonStats(BaseModel):
    count: int
    by_sponsored_by: dict[str, SponsoredByStats]


class ContractStatisticsResponse(BaseModel):
    total: int
    by_form_stage: dict[str, int]
    by_status: dict[str, int]
    by_zip_code: dict[str, int]
    by_city: dict[str, int]
    by_sponsored_by: dict[str, SponsoredByStats]
    by_proceed_reason: dict[str, ProceedReasonStats]


@router.get("/statistics", response_model=ContractStatisticsResponse)
async def get_statistics(
    db: AsyncSession = Depends(get_db),
):
    """Return contract statistics: total count, counts per form stage, status, zip code, city, sponsored_by, and proceed_reason."""
    stats = await get_contract_statistics(db)
    return ContractStatisticsResponse(
        total=stats["total"],
        by_form_stage=stats["by_form_stage"],
        by_status=stats["by_status"],
        by_zip_code=stats["by_zip_code"],
        by_city=stats["by_city"],
        by_sponsored_by=stats["by_sponsored_by"],
        by_proceed_reason=stats["by_proceed_reason"],
    )


class AuditorScheduleSlot(BaseModel):
    """A single contract slot in an auditor's schedule."""
    contract_id: str
    formatted_time_range: Optional[str] = None  # e.g. "February 19, 2026 at 9:00 AM – 10:00 AM"
    zip: Optional[str] = None
    city: Optional[str] = None


class AuditorScheduleEntry(BaseModel):
    """One auditor's schedule for the day: auditor id/name and ordered list of slots."""
    auditor_id: Optional[str] = None
    auditor_name: Optional[str] = None
    contracts: list[str] = []


class AuditorScheduleResponse(BaseModel):
    items: list[AuditorScheduleEntry]


@router.get("/auditor-schedule", response_model=AuditorScheduleResponse)
async def get_auditor_schedule(
    date: str = Query(..., description="Date in ISO format (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
):
    """Get auditor schedule for a given date: list of auditors with their ordered contract slots for that day."""
    schedule = await get_auditor_schedule_for_date(db, date)
    return {"items": schedule}


@router.get("/list", response_model=PaginatedContractListResponse)
async def list_contracts(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    limit: int = Query(9, ge=1, le=100, description="Number of items per page"),
    date_from: Optional[str] = Query(None, description="Filter contracts by date (ISO format, e.g., 2024-01-01). Only returns contracts with date >= date_from"),
    no_dates: Optional[bool] = Query(None, description="If True, only return contracts without dates. If False, only return contracts with dates. If None (default), return all contracts."),
    status: Optional[Literal["open", "cancelled", "completed"]] = Query(
        "open",
        description="Filter contracts by status. Defaults to 'open'.",
    ),
    search: Optional[str] = Query(None, description="Optional search term (case-insensitive). Searches hancock_project_id, client_name, zip, and city."),
    db: AsyncSession = Depends(get_db),
):
    """
    List contracts with pagination.
    Ordering: items without date first, then ascending date and ascending time.
    Returns 9 items per page by default.
    By default, shows all contracts (with and without dates).
    """
    contracts, total_count = await list_contracts_query(
        db,
        page=page,
        limit=limit,
        date_from=date_from,
        no_dates=no_dates,
        status=status,
        search=search,
    )
    
    # Calculate total pages
    total_pages = (total_count + limit - 1) // limit if total_count > 0 else 0
    
    return PaginatedContractListResponse(
        items=[
            ContractListItem(
                id=contract.id,
                zip=contract.zip,
                city=contract.city,
                street_address=contract.street_address,
                notes=contract.notes,
                fuel_type=contract.fuel_type,
                sponsored_by=contract.sponsored_by or "other",
                hancock_project_id=contract.hancock_project_id,
                auditor_id=contract.auditor_id,
                client_name=contract.client_name,
                phone_number=contract.phone_number,
                client_email=contract.client_email,
                formatted_datetime=format_datetime(contract.date, contract.start_at_time),
                meeting_url=contract.google_meet_url,
                inspection_doc=contract.inspection_doc,
                invoice_doc=contract.invoice_doc,
                form_stage=contract.form_stage,
                r2=contract.r2 if contract.r2 is not None else False,
                status=contract.status or "open",
            )
            for contract in contracts
        ],
        total=total_count,
        page=page,
        limit=limit,
        total_pages=total_pages,
    )


@router.get("/", response_model=list[ContractResponse])
async def get_all_contracts(
    db: AsyncSession = Depends(get_db),
):
    """Get all contracts with full data ordered by date and start_at_time descending."""
    # Get all contracts (using a large limit to get all)
    contracts, _ = await list_contracts_query(db, page=1, limit=10000)
    return [
        ContractResponse(
            id=contract.id,
            user_id=contract.user_id,
            zip=contract.zip,
            city=contract.city,
            street_address=contract.street_address,
            notes=contract.notes,
            fuel_type=contract.fuel_type,
            sponsored_by=contract.sponsored_by or "other",
            hancock_project_id=contract.hancock_project_id,
            auditor_id=contract.auditor_id,
            client_name=contract.client_name,
            client_email=contract.client_email,
            phone_number=contract.phone_number,
            multifamily_values=contract.multifamily_values,
            date=contract.date.isoformat() if contract.date else None,
            start_at_time=contract.start_at_time.isoformat() if contract.start_at_time else None,
            end_at_time=contract.end_at_time.isoformat() if contract.end_at_time else None,
            formatted_datetime=format_datetime(contract.date, contract.start_at_time),
            google_meet_url=contract.google_meet_url,
            meeting_url=contract.google_meet_url,
            inspection_doc=contract.inspection_doc,
            invoice_doc=contract.invoice_doc,
            form_stage=contract.form_stage,
            r2=contract.r2 if contract.r2 is not None else False,
            status=contract.status or "open",
            created_at=contract.created_at.isoformat() if contract.created_at else "",
            updated_at=contract.updated_at.isoformat() if contract.updated_at else "",
        )
        for contract in contracts
    ]


@router.get("/{contract_id}", response_model=ContractResponse)
async def get_contract(
    contract_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a single contract by ID with full data including inspection_doc and invoice_doc URLs."""
    contract = await get_contract_by_id(db, contract_id)
    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contract with id {contract_id} not found",
        )
    
    return ContractResponse(
        id=contract.id,
        user_id=contract.user_id,
        zip=contract.zip,
        city=contract.city,
        street_address=contract.street_address,
        notes=contract.notes,
        fuel_type=contract.fuel_type,
        sponsored_by=contract.sponsored_by or "other",
        hancock_project_id=contract.hancock_project_id,
        auditor_id=contract.auditor_id,
        client_name=contract.client_name,
        client_email=contract.client_email,
        phone_number=contract.phone_number,
        multifamily_values=contract.multifamily_values,
        date=contract.date.isoformat() if contract.date else None,
        start_at_time=contract.start_at_time.isoformat() if contract.start_at_time else None,
        end_at_time=contract.end_at_time.isoformat() if contract.end_at_time else None,
        formatted_datetime=format_datetime(contract.date, contract.start_at_time),
        google_meet_url=contract.google_meet_url,
        meeting_url=contract.google_meet_url,
        inspection_doc=contract.inspection_doc,
        invoice_doc=contract.invoice_doc,
        form_stage=contract.form_stage,
        r2=contract.r2 if contract.r2 is not None else False,
        status=contract.status or "open",
        created_at=contract.created_at.isoformat() if contract.created_at else "",
        updated_at=contract.updated_at.isoformat() if contract.updated_at else "",
    )


@router.patch("/{contract_id}/status", response_model=ContractResponse)
async def patch_contract_status(
    contract_id: str,
    body: PatchContractStatusRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update contract status to 'cancelled' or 'completed'."""
    contract = await update_contract_status(db, contract_id, body.status)
    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contract with id {contract_id} not found or invalid status",
        )
    return ContractResponse(
        id=contract.id,
        user_id=contract.user_id,
        zip=contract.zip,
        city=contract.city,
        street_address=contract.street_address,
        notes=contract.notes,
        fuel_type=contract.fuel_type,
        sponsored_by=contract.sponsored_by or "other",
        hancock_project_id=contract.hancock_project_id,
        auditor_id=contract.auditor_id,
        client_name=contract.client_name,
        client_email=contract.client_email,
        phone_number=contract.phone_number,
        multifamily_values=contract.multifamily_values,
        date=contract.date.isoformat() if contract.date else None,
        start_at_time=contract.start_at_time.isoformat() if contract.start_at_time else None,
        end_at_time=contract.end_at_time.isoformat() if contract.end_at_time else None,
        formatted_datetime=format_datetime(contract.date, contract.start_at_time),
        google_meet_url=contract.google_meet_url,
        meeting_url=contract.google_meet_url,
        inspection_doc=contract.inspection_doc,
        invoice_doc=contract.invoice_doc,
        form_stage=contract.form_stage,
        r2=contract.r2 if contract.r2 is not None else False,
        status=contract.status or "open",
        created_at=contract.created_at.isoformat() if contract.created_at else "",
        updated_at=contract.updated_at.isoformat() if contract.updated_at else "",
    )


@router.delete("/{contract_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contract_endpoint(
    contract_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a contract by ID.
    Returns 204 if deleted, 404 if not found.
    """
    deleted = await delete_contract(db, contract_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contract with id {contract_id} not found",
        )


@router.post("/", response_model=ContractResponse)
async def submit_contract(
    contract_data: ContractRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Submit a contract.
    - If contract_id is provided, update the existing contract with provided fields.
    - If contract_id is not provided, create a new contract.
    """
    def _format_date(d) -> str:
        if not d:
            return ""
        return d.strftime("%B %d, %Y")

    def _format_time(t) -> str:
        if not t:
            return ""
        return t.strftime("%I:%M %p").lstrip("0")

    async def _send_auditor_assignment_email(*, auditor_id: str, contract) -> None:
        from pathlib import Path
        from sqlalchemy import select
        from database.models import User

        if not auditor_id:
            return
        result = await db.execute(select(User).where(User.id == auditor_id))
        auditor = result.scalar_one_or_none()
        if not auditor or not (auditor.email or "").strip():
            return

        src_root = Path(__file__).resolve().parents[1]
        template_path = src_root / "services" / "email_templates" / "auditor_notification.html"

        google_calendar_url = ""
        if contract.date and contract.start_at_time:
            start_dt = datetime.combine(contract.date, contract.start_at_time)
            end_dt = None
            if contract.end_at_time:
                end_dt = datetime.combine(contract.date, contract.end_at_time)
            else:
                end_dt = start_dt + timedelta(hours=1)

            details_lines: list[str] = []
            if (contract.google_meet_url or "").strip():
                details_lines.append(f"Meeting link: {contract.google_meet_url.strip()}")
            details_lines.append("Assigned via Souzet.")
            details = "\n".join(details_lines)

            location = " ".join([p for p in [(contract.city or "").strip(), (contract.zip or "").strip()] if p])
            title_city_zip = " ".join([p for p in [(contract.city or "").strip(), (contract.zip or "").strip()] if p])
            title = f"Audit - {title_city_zip}".strip() if title_city_zip else "Audit"

            google_calendar_url = build_google_calendar_event_url(
                title=title,
                start_dt=start_dt,
                end_dt=end_dt,
                details=details,
                location=location,
            )

        ses = SESService()
        ses.send_email_from_html_template(
            to_addresses=[auditor.email],
            subject="Souzet: New audit location assigned",
            template_path=template_path,
            context={
                "auditor_name_or_email": (auditor.full_name or "").strip() or auditor.email,
                "city": (contract.city or "").strip(),
                "zip": (contract.zip or "").strip(),
                "date": _format_date(contract.date),
                "time": _format_time(contract.start_at_time),
                "google_calendar_url": google_calendar_url,
            },
        )

    if contract_data.contract_id:
        # First, get the existing contract to verify ownership
        existing_contract = await get_contract_by_id(db, contract_data.contract_id)
        if not existing_contract:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Contract with id {contract_data.contract_id} not found",
            )

        # Update existing contract (pass auditor_id only when present in body so null can clear it)
        auditor_changed_to_assigned = (
            "auditor_id" in contract_data.model_dump(exclude_unset=True)
            and (existing_contract.auditor_id or "") != (contract_data.auditor_id or "")
            and (contract_data.auditor_id or "").strip() != ""
        )
        update_kwargs = dict(
            db=db,
            contract_id=contract_data.contract_id,
            user_id=contract_data.user_id,
            zip=contract_data.zip,
            city=contract_data.city,
            street_address=contract_data.street_address,
            notes=contract_data.notes,
            fuel_type=contract_data.fuel_type,
            client_name=contract_data.client_name,
            client_email=contract_data.client_email,
            phone_number=contract_data.phone_number,
            hancock_project_id=contract_data.hancock_project_id,
            date=contract_data.date,
            start_at_time=contract_data.start_at_time,
            end_at_time=contract_data.end_at_time,
            google_meet_url=contract_data.google_meet_url,
            inspection_doc=contract_data.inspection_doc,
            invoice_doc=contract_data.invoice_doc,
            form_stage=contract_data.form_stage,
            r2=contract_data.r2,
            multifamily_values=contract_data.multifamily_values,
        )
        if "auditor_id" in contract_data.model_dump(exclude_unset=True):
            update_kwargs["auditor_id"] = contract_data.auditor_id
        contract = await update_contract(**update_kwargs)
        if auditor_changed_to_assigned and contract and contract.auditor_id:
            try:
                await _send_auditor_assignment_email(auditor_id=contract.auditor_id, contract=contract)
            except Exception:
                pass
    else:
        # Create new contract
        contract = await create_contract(
            db=db,
            user_id=contract_data.user_id,
            zip=contract_data.zip,
            city=contract_data.city,
            street_address=contract_data.street_address,
            notes=contract_data.notes,
            fuel_type=contract_data.fuel_type,
            hancock_project_id=contract_data.hancock_project_id,
            auditor_id=contract_data.auditor_id,
            multifamily_values=contract_data.multifamily_values,
            date=contract_data.date,
            start_at_time=contract_data.start_at_time,
            end_at_time=contract_data.end_at_time,
            google_meet_url=contract_data.google_meet_url,
            inspection_doc=contract_data.inspection_doc,
            invoice_doc=contract_data.invoice_doc,
            form_stage=contract_data.form_stage,
            r2=contract_data.r2,
            client_name=contract_data.client_name,
            client_email=contract_data.client_email,
            phone_number=contract_data.phone_number,
        )
        if contract and (contract.auditor_id or "").strip() != "":
            try:
                await _send_auditor_assignment_email(auditor_id=contract.auditor_id, contract=contract)
            except Exception:
                pass
    
    # Convert to response model
    return ContractResponse(
        id=contract.id,
        user_id=contract.user_id,
        zip=contract.zip,
        city=contract.city,
        street_address=contract.street_address,
        notes=contract.notes,
        fuel_type=contract.fuel_type,
        sponsored_by=contract.sponsored_by or "other",
        hancock_project_id=contract.hancock_project_id,
        auditor_id=contract.auditor_id,
        client_name=contract.client_name,
        client_email=contract.client_email,
        phone_number=contract.phone_number,
        multifamily_values=contract.multifamily_values,
        date=contract.date.isoformat() if contract.date else None,
        start_at_time=contract.start_at_time.isoformat() if contract.start_at_time else None,
        end_at_time=contract.end_at_time.isoformat() if contract.end_at_time else None,
        formatted_datetime=format_datetime(contract.date, contract.start_at_time),
        google_meet_url=contract.google_meet_url,
        meeting_url=contract.google_meet_url,
        inspection_doc=contract.inspection_doc,
        invoice_doc=contract.invoice_doc,
        form_stage=contract.form_stage,
        r2=contract.r2 if contract.r2 is not None else False,
        status=contract.status or "open",
        created_at=contract.created_at.isoformat() if contract.created_at else "",
        updated_at=contract.updated_at.isoformat() if contract.updated_at else "",
    )


@router.post("/{contract_id}/inspection-doc", response_model=ContractResponse)
async def upload_inspection_doc(
    contract_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload inspection document for a contract. Stores the S3 URL in the contract's inspection_doc field."""
    contract = await get_contract_by_id(db, contract_id)
    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contract with id {contract_id} not found",
        )

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing file name",
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file",
        )

    try:
        s3 = S3Service()
        # Upload file to S3 with MIME type validation
        file_url = s3.upload_file(
            file_content=file_bytes,
            file_name=file.filename,
            folder=f"contracts/{contract_id}/inspection",
            content_type=file.content_type,
            validate_mime=True,
        )

        # Update contract with the file URL
        updated_contract = await update_contract(
            db=db,
            contract_id=contract_id,
            inspection_doc=file_url,
        )

        if not updated_contract:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update contract with inspection document URL",
            )

        return ContractResponse(
            id=updated_contract.id,
            user_id=updated_contract.user_id,
            zip=updated_contract.zip,
            city=updated_contract.city,
            street_address=updated_contract.street_address,
            notes=updated_contract.notes,
            fuel_type=updated_contract.fuel_type,
            sponsored_by=updated_contract.sponsored_by or "other",
            hancock_project_id=updated_contract.hancock_project_id,
            auditor_id=updated_contract.auditor_id,
            client_name=updated_contract.client_name,
            client_email=updated_contract.client_email,
            phone_number=updated_contract.phone_number,
            multifamily_values=updated_contract.multifamily_values,
            date=updated_contract.date.isoformat() if updated_contract.date else None,
            start_at_time=updated_contract.start_at_time.isoformat() if updated_contract.start_at_time else None,
            end_at_time=updated_contract.end_at_time.isoformat() if updated_contract.end_at_time else None,
            formatted_datetime=format_datetime(updated_contract.date, updated_contract.start_at_time),
            google_meet_url=updated_contract.google_meet_url,
            meeting_url=updated_contract.google_meet_url,
            inspection_doc=updated_contract.inspection_doc,
            invoice_doc=updated_contract.invoice_doc,
            form_stage=updated_contract.form_stage,
            r2=updated_contract.r2 if updated_contract.r2 is not None else False,
            status=updated_contract.status or "open",
            created_at=updated_contract.created_at.isoformat() if updated_contract.created_at else "",
            updated_at=updated_contract.updated_at.isoformat() if updated_contract.updated_at else "",
        )
    except ValueError as e:
        # MIME type validation failed
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File '{file.filename}': {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload inspection document: {str(e)}",
        )


@router.post("/{contract_id}/invoice-doc", response_model=ContractResponse)
async def upload_invoice_doc(
    contract_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload invoice document for a contract. Stores the S3 URL in the contract's invoice_doc field."""
    contract = await get_contract_by_id(db, contract_id)
    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contract with id {contract_id} not found",
        )

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing file name",
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file",
        )

    try:
        s3 = S3Service()
        # Upload file to S3 with MIME type validation
        file_url = s3.upload_file(
            file_content=file_bytes,
            file_name=file.filename,
            folder=f"contracts/{contract_id}/invoice",
            content_type=file.content_type,
            validate_mime=True,
        )

        # Update contract with the file URL
        updated_contract = await update_contract(
            db=db,
            contract_id=contract_id,
            invoice_doc=file_url,
        )

        if not updated_contract:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update contract with invoice document URL",
            )

        return ContractResponse(
            id=updated_contract.id,
            user_id=updated_contract.user_id,
            zip=updated_contract.zip,
            city=updated_contract.city,
            street_address=updated_contract.street_address,
            notes=updated_contract.notes,
            fuel_type=updated_contract.fuel_type,
            sponsored_by=updated_contract.sponsored_by or "other",
            hancock_project_id=updated_contract.hancock_project_id,
            auditor_id=updated_contract.auditor_id,
            client_name=updated_contract.client_name,
            client_email=updated_contract.client_email,
            phone_number=updated_contract.phone_number,
            multifamily_values=updated_contract.multifamily_values,
            date=updated_contract.date.isoformat() if updated_contract.date else None,
            start_at_time=updated_contract.start_at_time.isoformat() if updated_contract.start_at_time else None,
            end_at_time=updated_contract.end_at_time.isoformat() if updated_contract.end_at_time else None,
            formatted_datetime=format_datetime(updated_contract.date, updated_contract.start_at_time),
            google_meet_url=updated_contract.google_meet_url,
            meeting_url=updated_contract.google_meet_url,
            inspection_doc=updated_contract.inspection_doc,
            invoice_doc=updated_contract.invoice_doc,
            form_stage=updated_contract.form_stage,
            r2=updated_contract.r2 if updated_contract.r2 is not None else False,
            status=updated_contract.status or "open",
            created_at=updated_contract.created_at.isoformat() if updated_contract.created_at else "",
            updated_at=updated_contract.updated_at.isoformat() if updated_contract.updated_at else "",
        )
    except ValueError as e:
        # MIME type validation failed
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File '{file.filename}': {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload invoice document: {str(e)}",
        )
