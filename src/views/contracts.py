from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    UploadFile,
    File,
)
from typing import Optional
from pydantic import BaseModel

from database.connection import get_db
from database.queries.contract import create_contract, update_contract, get_contract_by_id, list_contracts as list_contracts_query
from sqlalchemy.ext.asyncio import AsyncSession

from services.s3_service import S3Service


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


class ContractRequest(BaseModel):
    user_id: str
    contract_id: Optional[str] = None
    zip: Optional[str] = None
    city: Optional[str] = None
    fuel_type: Optional[str] = None
    hancock_project_id: Optional[str] = None
    date: Optional[str] = None  # ISO format date string
    start_at_time: Optional[str] = None  # ISO format time string
    end_at_time: Optional[str] = None  # ISO format time string
    google_meet_url: Optional[str] = None
    inspection_doc: Optional[str] = None
    invoice_doc: Optional[str] = None
    form_stage: Optional[str] = None


class ContractResponse(BaseModel):
    id: str
    user_id: str
    zip: Optional[str] = None
    city: Optional[str] = None
    fuel_type: Optional[str] = None
    hancock_project_id: Optional[str] = None
    date: Optional[str] = None
    start_at_time: Optional[str] = None
    end_at_time: Optional[str] = None
    formatted_datetime: Optional[str] = None
    google_meet_url: Optional[str] = None
    meeting_url: Optional[str] = None
    inspection_doc: Optional[str] = None
    invoice_doc: Optional[str] = None
    form_stage: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class ContractListItem(BaseModel):
    id: str
    zip: Optional[str] = None
    city: Optional[str] = None
    fuel_type: Optional[str] = None
    hancock_project_id: Optional[str] = None
    formatted_datetime: Optional[str] = None
    meeting_url: Optional[str] = None
    inspection_doc: Optional[str] = None
    invoice_doc: Optional[str] = None
    form_stage: str

    class Config:
        from_attributes = True


@router.get("/list", response_model=list[ContractListItem])
async def list_contracts(
    db: AsyncSession = Depends(get_db),
):
    """List all contracts ordered by updated_at descending."""
    contracts = await list_contracts_query(db)
    return [
        ContractListItem(
            id=contract.id,
            zip=contract.zip,
            city=contract.city,
            fuel_type=contract.fuel_type,
            hancock_project_id=contract.hancock_project_id,
            formatted_datetime=format_datetime(contract.date, contract.start_at_time),
            meeting_url=contract.google_meet_url,
            inspection_doc=contract.inspection_doc,
            invoice_doc=contract.invoice_doc,
            form_stage=contract.form_stage,
        )
        for contract in contracts
    ]


@router.get("/", response_model=list[ContractResponse])
async def get_all_contracts(
    db: AsyncSession = Depends(get_db),
):
    """Get all contracts with full data ordered by updated_at descending."""
    contracts = await list_contracts_query(db)
    return [
        ContractResponse(
            id=contract.id,
            user_id=contract.user_id,
            zip=contract.zip,
            city=contract.city,
            fuel_type=contract.fuel_type,
            hancock_project_id=contract.hancock_project_id,
            date=contract.date.isoformat() if contract.date else None,
            start_at_time=contract.start_at_time.isoformat() if contract.start_at_time else None,
            end_at_time=contract.end_at_time.isoformat() if contract.end_at_time else None,
            formatted_datetime=format_datetime(contract.date, contract.start_at_time),
            google_meet_url=contract.google_meet_url,
            meeting_url=contract.google_meet_url,
            inspection_doc=contract.inspection_doc,
            invoice_doc=contract.invoice_doc,
            form_stage=contract.form_stage,
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
        fuel_type=contract.fuel_type,
        hancock_project_id=contract.hancock_project_id,
        date=contract.date.isoformat() if contract.date else None,
        start_at_time=contract.start_at_time.isoformat() if contract.start_at_time else None,
        end_at_time=contract.end_at_time.isoformat() if contract.end_at_time else None,
        formatted_datetime=format_datetime(contract.date, contract.start_at_time),
        google_meet_url=contract.google_meet_url,
        meeting_url=contract.google_meet_url,
        inspection_doc=contract.inspection_doc,
        invoice_doc=contract.invoice_doc,
        form_stage=contract.form_stage,
        created_at=contract.created_at.isoformat() if contract.created_at else "",
        updated_at=contract.updated_at.isoformat() if contract.updated_at else "",
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
    if contract_data.contract_id:
        # Update existing contract
        contract = await update_contract(
            db=db,
            contract_id=contract_data.contract_id,
            zip=contract_data.zip,
            city=contract_data.city,
            fuel_type=contract_data.fuel_type,
            hancock_project_id=contract_data.hancock_project_id,
            date=contract_data.date,
            start_at_time=contract_data.start_at_time,
            end_at_time=contract_data.end_at_time,
            google_meet_url=contract_data.google_meet_url,
            inspection_doc=contract_data.inspection_doc,
            invoice_doc=contract_data.invoice_doc,
            form_stage=contract_data.form_stage,
        )
        if not contract:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Contract with id {contract_data.contract_id} not found",
            )
        # Verify that the contract belongs to the user_id
        if contract.user_id != contract_data.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Contract does not belong to the specified user",
            )
    else:
        # Create new contract
        contract = await create_contract(
            db=db,
            user_id=contract_data.user_id,
            zip=contract_data.zip,
            city=contract_data.city,
            fuel_type=contract_data.fuel_type,
            hancock_project_id=contract_data.hancock_project_id,
            date=contract_data.date,
            start_at_time=contract_data.start_at_time,
            end_at_time=contract_data.end_at_time,
            google_meet_url=contract_data.google_meet_url,
            inspection_doc=contract_data.inspection_doc,
            invoice_doc=contract_data.invoice_doc,
            form_stage=contract_data.form_stage,
        )
    
    # Convert to response model
    return ContractResponse(
        id=contract.id,
        user_id=contract.user_id,
        zip=contract.zip,
        city=contract.city,
        fuel_type=contract.fuel_type,
        hancock_project_id=contract.hancock_project_id,
        date=contract.date.isoformat() if contract.date else None,
        start_at_time=contract.start_at_time.isoformat() if contract.start_at_time else None,
        end_at_time=contract.end_at_time.isoformat() if contract.end_at_time else None,
        formatted_datetime=format_datetime(contract.date, contract.start_at_time),
        google_meet_url=contract.google_meet_url,
        meeting_url=contract.google_meet_url,
        inspection_doc=contract.inspection_doc,
        invoice_doc=contract.invoice_doc,
        form_stage=contract.form_stage,
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
            fuel_type=updated_contract.fuel_type,
            hancock_project_id=updated_contract.hancock_project_id,
            date=updated_contract.date.isoformat() if updated_contract.date else None,
            start_at_time=updated_contract.start_at_time.isoformat() if updated_contract.start_at_time else None,
            end_at_time=updated_contract.end_at_time.isoformat() if updated_contract.end_at_time else None,
            formatted_datetime=format_datetime(updated_contract.date, updated_contract.start_at_time),
            google_meet_url=updated_contract.google_meet_url,
            meeting_url=updated_contract.google_meet_url,
            inspection_doc=updated_contract.inspection_doc,
            invoice_doc=updated_contract.invoice_doc,
            form_stage=updated_contract.form_stage,
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
            fuel_type=updated_contract.fuel_type,
            hancock_project_id=updated_contract.hancock_project_id,
            date=updated_contract.date.isoformat() if updated_contract.date else None,
            start_at_time=updated_contract.start_at_time.isoformat() if updated_contract.start_at_time else None,
            end_at_time=updated_contract.end_at_time.isoformat() if updated_contract.end_at_time else None,
            formatted_datetime=format_datetime(updated_contract.date, updated_contract.start_at_time),
            google_meet_url=updated_contract.google_meet_url,
            meeting_url=updated_contract.google_meet_url,
            inspection_doc=updated_contract.inspection_doc,
            invoice_doc=updated_contract.invoice_doc,
            form_stage=updated_contract.form_stage,
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
