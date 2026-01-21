from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import ContractFiles


async def create_contract_file(
    db: AsyncSession,
    contract_id: str,
    file_name: str,
    file_ext: str,
    file_url: str,
) -> ContractFiles:
    contract_file = ContractFiles(
        contract_id=contract_id,
        file_name=file_name,
        file_ext=file_ext,
        file_url=file_url,
    )
    db.add(contract_file)
    await db.commit()
    await db.refresh(contract_file)
    return contract_file


async def list_contract_files(db: AsyncSession, contract_id: str) -> list[ContractFiles]:
    result = await db.execute(
        select(ContractFiles).where(ContractFiles.contract_id == contract_id)
    )
    return list(result.scalars().all())

