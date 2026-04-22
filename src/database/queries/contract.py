import datetime as dt

from sqlalchemy import distinct, select, update, delete, func, literal
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Contract, ContractFormUpdate, User, ZipProfiles


def icontains(column, needle: str):
    """
    Case-insensitive substring match.
    Implemented as: lower(column) LIKE %lower(needle)%.
    """
    return func.lower(column).like(f"%{needle.lower()}%")


async def list_contracts(
    db: AsyncSession,
    page: int = 1,
    limit: int = 20,
    date_from: str | None = None,
    no_dates: bool | None = None,
    search: str | None = None,
    status: str | None = "open",
) -> tuple[list[Contract], int]:
    """
    List contracts with pagination, ordered by date and start_at_time.
    Ordering: newest created first (created_at desc).
    
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

    # Apply status filter (defaults to "open")
    if status is not None:
        status_value = str(status).strip().lower()
        if status_value in ("open", "cancelled", "completed"):
            query = query.where(func.coalesce(Contract.status, literal("open")) == status_value)
            count_query = count_query.where(func.coalesce(Contract.status, literal("open")) == status_value)
    
    # Apply search filter (case-insensitive partial match)
    if search is not None and str(search).strip() != "":
        search_term = str(search).strip()
        search_filter = (
            icontains(Contract.hancock_project_id, search_term)
            | icontains(Contract.client_name, search_term)
            | icontains(Contract.client_email, search_term)
            | icontains(Contract.zip, search_term)
            | icontains(Contract.city, search_term)
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

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
    
    # Order by: newest created first
    result = await db.execute(
        query.order_by(
            Contract.created_at.desc()
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


async def get_contract_by_ghl_contract_id(db: AsyncSession, ghl_contract_id: str) -> Contract | None:
    """Get contract by GHL contract id."""
    result = await db.execute(
        select(Contract).where(Contract.ghl_contract_id == ghl_contract_id)
    )
    return result.scalar_one_or_none()


async def get_auditor_schedule_for_date(
    db: AsyncSession,
    date: str,
) -> list[dict]:
    """
    Get schedule of auditors for a given date.
    Returns list of { "auditor_id": str | None, "auditor_name": str | None, "slots": list[Contract] }
    with slots ordered by start_at_time. Contracts with no auditor_id are grouped under auditor_id None.
    """
    # Fetch users with type Auditors
    auditors_result = await db.execute(select(User).where(User.cognito_group == "Auditors"))
    auditors = list(auditors_result.scalars().all())

    # Fetch contracts by auditor_id and date, group by auditor_id
    if isinstance(date, str):
        date = dt.date.fromisoformat(date)
    contracts_result = await db.execute(
        select(Contract)
        .where(Contract.date == date)
        .order_by(Contract.start_at_time.asc().nulls_last())
    )
    contracts = list(contracts_result.scalars().all())

    auditors_schedule = []
    for auditor in auditors:
        auditor_contracts = [
            f"{date.strftime('%B %d, %Y')} at {contract.start_at_time.strftime('%I:%M %p')} - {contract.end_at_time.strftime('%I:%M %p')}"
            for contract in contracts if contract.auditor_id == auditor.id
        ]

        auditors_schedule.append({
            "auditor_id": auditor.id,
            "auditor_name": auditor.full_name,
            "auditor_email": auditor.email,
            "contracts": auditor_contracts,
        })

    return auditors_schedule


async def create_contract(
    db: AsyncSession,
    user_id: str,
    zip: str | None = None,
    city: str | None = None,
    fuel_type: str | None = None,
    hancock_project_id: str | None = None,
    auditor_id: str | None = None,
    multifamily_values: list[str] | None = None,
    date: str | None = None,
    start_at_time: str | None = None,
    end_at_time: str | None = None,
    google_meet_url: str | None = None,
    inspection_doc: str | None = None,
    invoice_doc: str | None = None,
    form_stage: str | None = None,
    r2: bool | None = None,
    ghl_contract_id: str | None = None,
    client_email: str | None = None,
    client_name: str | None = None,
    phone_number: str | None = None,
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
    
    # Resolve sponsored_by from zip_profiles when zip is provided
    sponsored_by = None
    if zip:
        profile_result = await db.execute(
            select(ZipProfiles.sponsored).where(ZipProfiles.zip_code == zip).limit(1)
        )
        row = profile_result.one_or_none()
        if row is not None:
            sponsored_by = row[0]

    contract_kwargs = {
        "user_id": user_id,
        "zip": zip,
        "city": city,
        "fuel_type": fuel_type,
        "sponsored_by": sponsored_by,
        "hancock_project_id": hancock_project_id,
        "auditor_id": auditor_id,
        "multifamily_values": multifamily_values,
        "date": parsed_date,
        "start_at_time": parsed_start_time,
        "end_at_time": parsed_end_time,
        "google_meet_url": google_meet_url,
        "inspection_doc": inspection_doc,
        "invoice_doc": invoice_doc,
        "form_stage": form_stage or "project_id",
        "ghl_contract_id": ghl_contract_id,
        "client_email": client_email,
        "client_name": client_name,
        "phone_number": phone_number,
    }
    # Only set r2 if explicitly provided, otherwise use model default (False)
    if r2 is not None:
        contract_kwargs["r2"] = r2

    contract = Contract(**contract_kwargs)
    db.add(contract)
    await db.flush()
    form_part = form_stage or "project_id"
    db.add(
        ContractFormUpdate(
            contract_id=contract.id,
            form_part=form_part,
            user_id=user_id,
        )
    )
    await db.commit()
    await db.refresh(contract)
    return contract


class _Unset:
    pass


_UNSET = _Unset()


async def update_contract(
    db: AsyncSession,
    contract_id: str,
    user_id: str | None = None,
    zip: str | None = None,
    city: str | None = None,
    fuel_type: str | None = None,
    hancock_project_id: str | None = None,
    auditor_id: str | None | type[_Unset] = _UNSET,
    multifamily_values: list[str] | None = None,
    date: str | None = None,
    start_at_time: str | None = None,
    end_at_time: str | None = None,
    google_meet_url: str | None = None,
    inspection_doc: str | None = None,
    invoice_doc: str | None = None,
    form_stage: str | None = None,
    r2: bool | None = None,
    ghl_contract_id: str | None = None,
    client_email: str | None = None,
    client_name: str | None = None,
    phone_number: str | None = None,
) -> Contract | None:
    """Update an existing contract with only provided fields."""
    import datetime
    
    # Get the existing contract
    contract = await get_contract_by_id(db, contract_id)
    if not contract:
        return None
    
    # Build update dictionary with only provided fields
    update_data = {}
    if user_id is not None:
        update_data["user_id"] = user_id
    if zip is not None:
        update_data["zip"] = zip
    if city is not None:
        update_data["city"] = city
    if fuel_type is not None:
        update_data["fuel_type"] = fuel_type
    if hancock_project_id is not None:
        update_data["hancock_project_id"] = hancock_project_id
    if auditor_id is not _UNSET:
        update_data["auditor_id"] = auditor_id
    if multifamily_values is not None:
        update_data["multifamily_values"] = multifamily_values
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
    if r2 is not None:
        update_data["r2"] = r2
    if ghl_contract_id is not None:
        update_data["ghl_contract_id"] = ghl_contract_id
    if client_email is not None:
        update_data["client_email"] = client_email
    if client_name is not None:
        update_data["client_name"] = client_name
    if phone_number is not None:
        update_data["phone_number"] = phone_number
    if not update_data:
        return contract
    
    # Update the contract
    await db.execute(
        update(Contract)
        .where(Contract.id == contract_id)
        .values(**update_data)
    )
    await db.commit()
    updated_contract = await get_contract_by_id(db, contract_id)
    # Record who last updated this form part (last update wins)
    if user_id is not None and updated_contract and updated_contract.form_stage:
        stmt = insert(ContractFormUpdate).values(
            contract_id=contract_id,
            form_part=updated_contract.form_stage,
            user_id=user_id,
        ).on_conflict_do_update(
            index_elements=["contract_id", "form_part"],
            set_={"user_id": user_id},
        )
        await db.execute(stmt)
        await db.commit()
    return updated_contract


async def update_contract_status(
    db: AsyncSession,
    contract_id: str,
    status: str,
) -> Contract | None:
    """Update contract status to 'cancelled' or 'completed'. Returns None if contract not found or status invalid."""
    if status not in ("cancelled", "completed"):
        return None
    contract = await get_contract_by_id(db, contract_id)
    if not contract:
        return None
    await db.execute(
        update(Contract).where(Contract.id == contract_id).values(status=status)
    )
    await db.commit()
    return await get_contract_by_id(db, contract_id)


async def get_contract_statistics(
    db: AsyncSession,
) -> dict:
    """
    Return contract statistics: total count, counts per form_stage, per status,
    per zip_code, per city, per sponsored_by, and per proceed_reason (via zip_profiles join).
    Returns:
        {
            "total": int,
            "by_form_stage": { "<stage>": int, ... },
            "by_status": { "open": int, "cancelled": int, "completed": int },
            "by_zip_code": { "<zip>": int, ... },
            "by_city": { "<city>": int, ... },
        "by_sponsored_by": { "<sponsor>": { "total": int, "fuel": { "<fuel_type>": int } }, ... },
        "by_proceed_reason": { "<reason>": { "count": int, "by_sponsored_by": { "<sponsor>": { "total": int, "fuel": { "<fuel_type>": int } } } }, ... }
        }
    """
    total_result = await db.execute(select(func.count(Contract.id)))
    total = total_result.scalar_one() or 0

    form_stage_result = await db.execute(
        select(Contract.form_stage, func.count(Contract.id)).group_by(Contract.form_stage)
    )
    by_form_stage = {row[0] or "": row[1] for row in form_stage_result.all()}

    status_result = await db.execute(
        select(Contract.status, func.count(Contract.id)).group_by(Contract.status)
    )
    status_rows = {row[0] or "open": row[1] for row in status_result.all()}
    by_status = {
        "open": status_rows.get("open", 0),
        "cancelled": status_rows.get("cancelled", 0),
        "completed": status_rows.get("completed", 0),
    }

    zip_result = await db.execute(
        select(Contract.zip, func.count(Contract.id)).group_by(Contract.zip)
    )
    by_zip_code = {
        (row[0] or ""): row[1]
        for row in zip_result.all()
        if (row[0] or "").strip() != ""
    }
    if len(by_zip_code) > 5:
        by_zip_code = dict(
            sorted(by_zip_code.items(), key=lambda kv: kv[1], reverse=True)[:5]
        )

    city_result = await db.execute(
        select(Contract.city, func.count(Contract.id)).group_by(Contract.city)
    )
    by_city = {
        (row[0] or ""): row[1]
        for row in city_result.all()
        if (row[0] or "").strip() != ""
    }
    if len(by_city) > 5:
        by_city = dict(sorted(by_city.items(), key=lambda kv: kv[1], reverse=True)[:5])

    sponsored_by_fuel_result = await db.execute(
        select(
            Contract.sponsored_by,
            Contract.fuel_type,
            func.count(Contract.id),
        )
        .group_by(Contract.sponsored_by, Contract.fuel_type)
    )
    by_sponsored_by = {}
    for row in sponsored_by_fuel_result.all():
        sponsor_key = row[0] or "other"
        fuel_key = row[1] or ""
        count = row[2]
        if sponsor_key not in by_sponsored_by:
            by_sponsored_by[sponsor_key] = {"total": 0, "fuel": {}}
        by_sponsored_by[sponsor_key]["total"] += count
        by_sponsored_by[sponsor_key]["fuel"][fuel_key] = (
            by_sponsored_by[sponsor_key]["fuel"].get(fuel_key, 0) + count
        )

    proceed_reason_key = func.coalesce(ZipProfiles.proceed_reason, literal("Out of Scope"))
    proceed_reason_result = await db.execute(
        select(proceed_reason_key, func.count(distinct(Contract.id)))
        .select_from(Contract)
        .outerjoin(ZipProfiles, Contract.zip == ZipProfiles.zip_code)
        .group_by(proceed_reason_key)
    )
    proceed_reason_counts = {str(row[0] or "").strip(): int(row[1] or 0) for row in proceed_reason_result.all()}
    proceed_reason_sponsored_by_fuel_result = await db.execute(
        select(
            proceed_reason_key,
            Contract.sponsored_by,
            Contract.fuel_type,
            func.count(Contract.id),
        )
        .select_from(Contract)
        .outerjoin(ZipProfiles, Contract.zip == ZipProfiles.zip_code)
        .group_by(proceed_reason_key, Contract.sponsored_by, Contract.fuel_type)
    )

    by_proceed_reason: dict[str, dict] = {}
    for reason, count in proceed_reason_counts.items():
        if reason == "" or count <= 0:
            continue
        by_proceed_reason[reason] = {"count": count, "by_sponsored_by": {}}

    for row in proceed_reason_sponsored_by_fuel_result.all():
        reason_key = str(row[0] or "").strip()
        if reason_key == "" or proceed_reason_counts.get(reason_key, 0) <= 0:
            continue
        sponsor_key = row[1] or "other"
        fuel_key = row[2] or ""
        count = int(row[3] or 0)
        if count <= 0:
            continue

        sponsor_bucket = by_proceed_reason[reason_key]["by_sponsored_by"].setdefault(
            sponsor_key, {"total": 0, "fuel": {}}
        )
        sponsor_bucket["total"] += count
        sponsor_bucket["fuel"][fuel_key] = sponsor_bucket["fuel"].get(fuel_key, 0) + count

    return {
        "total": total,
        "by_form_stage": by_form_stage,
        "by_status": by_status,
        "by_zip_code": by_zip_code,
        "by_city": by_city,
        "by_sponsored_by": {},
        "by_proceed_reason": by_proceed_reason,
    }


async def delete_contract(
    db: AsyncSession,
    contract_id: str,
) -> bool:
    """
    Permanently delete a contract by ID.
    Returns True if a row was deleted, False otherwise.
    """
    result = await db.execute(
        delete(Contract).where(Contract.id == contract_id)
    )
    await db.commit()
    return result.rowcount > 0
