from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Contract


async def list_contracts(
    db: AsyncSession,
    page: int = 1,
    limit: int = 20,
    date_from: str | None = None,
    no_dates: bool | None = None
) -> tuple[list[Contract], int]:
    """
    List contracts with pagination, ordered by date and start_at_time.
    Ordering: items without date first, then ascending date and ascending time.
    
    Args:
        db: Database session
        page: Page number (1-indexed)
        limit: Number of items per page
        date_from: Optional date filter (ISO format) - only contracts with date >= date_from
        no_dates: If True, only return contracts without dates (date is NULL).
                  If False, only return contracts with dates (date IS NOT NULL).
                  If None (default), return all contracts (with and without dates).
        
    Returns:
        Tuple of (list of contracts, total count)
    """
    import datetime
    
    # Calculate offset
    offset = (page - 1) * limit
    
    # Build query with optional filters
    query = select(Contract)
    count_query = select(func.count(Contract.id))
    
    # Apply no_dates filter
    if no_dates is True:
        # Only contracts without dates
        query = query.where(Contract.date.is_(None))
        count_query = count_query.where(Contract.date.is_(None))
    elif no_dates is False:
        # Only contracts with dates
        query = query.where(Contract.date.isnot(None))
        count_query = count_query.where(Contract.date.isnot(None))
    
    # Apply date_from filter (only if no_dates is not True)
    if no_dates is not True and date_from:
        # Parse date filter if provided
        filter_date = None
        try:
            if isinstance(date_from, str):
                try:
                    filter_date = datetime.date.fromisoformat(date_from)
                except ValueError:
                    # Try parsing as datetime and extract date
                    filter_date = datetime.datetime.fromisoformat(date_from).date()
            else:
                filter_date = date_from
        except (ValueError, AttributeError):
            # If date parsing fails, ignore the filter
            filter_date = None
        
        if filter_date:
            query = query.where(Contract.date >= filter_date)
            count_query = count_query.where(Contract.date >= filter_date)
    
    count_result = await db.execute(count_query)
    total_count = count_result.scalar_one()
    
    # Order by: items without date first (nulls_first), then ascending date and ascending time
    result = await db.execute(
        query.order_by(
            Contract.date.asc().nulls_first(),
            Contract.start_at_time.asc().nulls_last()
        )
        .limit(limit)
        .offset(offset)
    )
    
    contracts = list(result.scalars().all())
    return contracts, total_count


async def get_contract_by_id(db: AsyncSession, contract_id: str) -> Contract | None:
    """Get contract by id."""
    result = await db.execute(
        select(Contract).where(Contract.id == contract_id)
    )
    return result.scalar_one_or_none()


async def create_contract(
    db: AsyncSession,
    user_id: str,
    zip: str | None = None,
    city: str | None = None,
    fuel_type: str | None = None,
    hancock_project_id: str | None = None,
    date: str | None = None,
    start_at_time: str | None = None,
    end_at_time: str | None = None,
    google_meet_url: str | None = None,
    inspection_doc: str | None = None,
    invoice_doc: str | None = None,
    form_stage: str | None = None,
) -> Contract:
    """Create a new contract."""
    import datetime
    
    # Parse date and time strings if provided
    parsed_date = None
    parsed_start_time = None
    parsed_end_time = None
    
    if date:
        if isinstance(date, str):
            # Handle both date strings and datetime strings
            try:
                parsed_date = datetime.date.fromisoformat(date)
            except ValueError:
                # Try parsing as datetime and extract date
                parsed_date = datetime.datetime.fromisoformat(date).date()
        else:
            parsed_date = date
    if start_at_time:
        if isinstance(start_at_time, str):
            # Handle both time strings and datetime strings
            try:
                parsed_start_time = datetime.time.fromisoformat(start_at_time)
            except ValueError:
                # Try parsing as datetime and extract time
                parsed_start_time = datetime.datetime.fromisoformat(start_at_time).time()
        else:
            parsed_start_time = start_at_time
    if end_at_time:
        if isinstance(end_at_time, str):
            # Handle both time strings and datetime strings
            try:
                parsed_end_time = datetime.time.fromisoformat(end_at_time)
            except ValueError:
                # Try parsing as datetime and extract time
                parsed_end_time = datetime.datetime.fromisoformat(end_at_time).time()
        else:
            parsed_end_time = end_at_time
    
    contract = Contract(
        user_id=user_id,
        zip=zip,
        city=city,
        fuel_type=fuel_type,
        hancock_project_id=hancock_project_id,
        date=parsed_date,
        start_at_time=parsed_start_time,
        end_at_time=parsed_end_time,
        google_meet_url=google_meet_url,
        inspection_doc=inspection_doc,
        invoice_doc=invoice_doc,
        form_stage=form_stage or "project_id",
    )
    db.add(contract)
    await db.commit()
    await db.refresh(contract)
    return contract


async def update_contract(
    db: AsyncSession,
    contract_id: str,
    zip: str | None = None,
    city: str | None = None,
    fuel_type: str | None = None,
    hancock_project_id: str | None = None,
    date: str | None = None,
    start_at_time: str | None = None,
    end_at_time: str | None = None,
    google_meet_url: str | None = None,
    inspection_doc: str | None = None,
    invoice_doc: str | None = None,
    form_stage: str | None = None,
) -> Contract | None:
    """Update an existing contract with only provided fields."""
    import datetime
    
    # Get the existing contract
    contract = await get_contract_by_id(db, contract_id)
    if not contract:
        return None
    
    # Build update dictionary with only provided fields
    update_data = {}
    if zip is not None:
        update_data["zip"] = zip
    if city is not None:
        update_data["city"] = city
    if fuel_type is not None:
        update_data["fuel_type"] = fuel_type
    if hancock_project_id is not None:
        update_data["hancock_project_id"] = hancock_project_id
    if date is not None:
        if isinstance(date, str):
            # Handle both date strings and datetime strings
            try:
                parsed_date = datetime.date.fromisoformat(date)
            except ValueError:
                # Try parsing as datetime and extract date
                parsed_date = datetime.datetime.fromisoformat(date).date()
        else:
            parsed_date = date
        update_data["date"] = parsed_date
    if start_at_time is not None:
        if isinstance(start_at_time, str):
            # Handle both time strings and datetime strings
            try:
                parsed_start_time = datetime.time.fromisoformat(start_at_time)
            except ValueError:
                # Try parsing as datetime and extract time
                parsed_start_time = datetime.datetime.fromisoformat(start_at_time).time()
        else:
            parsed_start_time = start_at_time
        update_data["start_at_time"] = parsed_start_time
    if end_at_time is not None:
        if isinstance(end_at_time, str):
            # Handle both time strings and datetime strings
            try:
                parsed_end_time = datetime.time.fromisoformat(end_at_time)
            except ValueError:
                # Try parsing as datetime and extract time
                parsed_end_time = datetime.datetime.fromisoformat(end_at_time).time()
        else:
            parsed_end_time = end_at_time
        update_data["end_at_time"] = parsed_end_time
    if google_meet_url is not None:
        update_data["google_meet_url"] = google_meet_url
    if inspection_doc is not None:
        update_data["inspection_doc"] = inspection_doc
    if invoice_doc is not None:
        update_data["invoice_doc"] = invoice_doc
    if form_stage is not None:
        update_data["form_stage"] = form_stage
    
    if not update_data:
        return contract
    
    # Update the contract
    await db.execute(
        update(Contract)
        .where(Contract.id == contract_id)
        .values(**update_data)
    )
    await db.commit()
    # Get the updated contract
    return await get_contract_by_id(db, contract_id)
