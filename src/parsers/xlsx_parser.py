import asyncio
import json
import os
import sys

import pandas as pd
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

# Add parent directory to path to import database modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database.connection import AsyncSessionLocal
from database.models.zip_profile import Agencies, ZipProfiles

CONTRACTORS_FILE_PATH = "zip_contractors.xlsx"
AGENCIES_FILE_PATH = "agencies.xlsx"


def yn_to_bool(value):
    if pd.isna(value):
        return False
    return str(value).strip().upper() == "YES"


def parse_agencies_xlsx(path: str):
    df = pd.read_excel(path)

    agencies = []

    for _, row in df.iterrows():
        agency = {
            "agency_code": str(row["agency_code"]).strip(),
            "name": row["agency_name"],
            "phone": row["phone"],
            "website": row["website"],
            "to_apply_url": row["to_apply"],
            "notes": row["notes"],
        }

        agencies.append(agency)

    return agencies


def parse_contractors_xlsx(path: str):
    df = pd.read_excel(path)

    records = []

    for _, row in df.iterrows():
        record = {
            "zip_code": str(row["zip_code"]).zfill(5),
            "city": str(row["city"]).title(),
            "fuel_type": row["fuel_type"],
            "sponsored": row["sponsored"],
            "utility_type": row["utility_type"],
            "has_utility": yn_to_bool(row["utility"]),
            "proceed_reason": row["proceed_reason"],
            "is_dec": yn_to_bool(row["is_dec"]),
            "electrification_candidate": yn_to_bool(row["electrification_candidate"]),
            "agency_code": row["R2_AgencyCodes"]
        }

        records.append(record)

    return records


async def delete_all_records(db: AsyncSession):
    """Delete all records from agencies and zip_profiles tables."""
    print("Deleting all existing records from agencies and zip_profiles tables...")
    
    # Delete all zip_profiles first (in case there are foreign key constraints)
    await db.execute(delete(ZipProfiles))
    
    # Delete all agencies
    await db.execute(delete(Agencies))
    
    await db.commit()
    print("All records deleted successfully!")


async def fill_agencies(agencies_data: list[dict], db: AsyncSession):
    """Fill Agencies table with parsed agencies data."""
    for agency_data in agencies_data:
        new_agency = Agencies(
            code=agency_data["agency_code"],
            name=agency_data["name"],
            phone=str(agency_data["phone"]) if pd.notna(agency_data["phone"]) else "",
            website=str(agency_data["website"]) if pd.notna(agency_data["website"]) else "",
            to_apply_url=str(agency_data["to_apply_url"]) if pd.notna(agency_data["to_apply_url"]) else "",
            notes=str(agency_data["notes"]) if pd.notna(agency_data["notes"]) else "",
        )
        db.add(new_agency)
    
    await db.commit()
    print(f"Processed {len(agencies_data)} agencies")


async def fill_zip_profiles(contractors_data: list[dict], db: AsyncSession):
    """Fill ZipProfiles table with parsed contractors data."""
    for contractor_data in contractors_data:
        new_profile = ZipProfiles(
            zip_code=contractor_data["zip_code"],
            city=contractor_data["city"],
            fuel_type=str(contractor_data["fuel_type"]) if pd.notna(contractor_data["fuel_type"]) else "",
            sponsored=str(contractor_data["sponsored"]) if pd.notna(contractor_data["sponsored"]) else "",
            utility_type=str(contractor_data["utility_type"]) if pd.notna(contractor_data["utility_type"]) else "",
            has_utility=contractor_data["has_utility"],
            proceed_reason=str(contractor_data["proceed_reason"]) if pd.notna(contractor_data["proceed_reason"]) else "",
            is_dec=contractor_data["is_dec"],
            electrification_candidate=contractor_data["electrification_candidate"],
            agency_code=str(contractor_data["agency_code"]) if pd.notna(contractor_data["agency_code"]) else None,
        )
        db.add(new_profile)
    
    await db.commit()
    print(f"Processed {len(contractors_data)} zip profiles")


async def fill_database(contractors_data: list[dict], agencies_data: list[dict]):
    """Main function to fill database with parsed data."""
    async with AsyncSessionLocal() as db:
        # Delete all existing records first
        await delete_all_records(db)
        
        print("Filling Agencies table...")
        await fill_agencies(agencies_data, db)
        
        print("Filling ZipProfiles table...")
        await fill_zip_profiles(contractors_data, db)
    
    print("Database population completed!")


if __name__ == "__main__":
    # Get the directory where the script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    contractors_path = os.path.join(script_dir, CONTRACTORS_FILE_PATH)
    agencies_path = os.path.join(script_dir, AGENCIES_FILE_PATH)
    
    # Parse Excel files
    contractors = parse_contractors_xlsx(contractors_path)
    agencies = parse_agencies_xlsx(agencies_path)

    # Optional: save to JSON
    json_path = os.path.join(script_dir, "zip_data.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(contractors, f, indent=4, ensure_ascii=False)
    
    # Fill database
    print("Parsing Excel files...")
    asyncio.run(fill_database(contractors, agencies))