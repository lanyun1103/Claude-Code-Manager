from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.global_settings import GlobalSettings
from backend.schemas.global_settings import GlobalSettingsUpdate, GlobalSettingsResponse

router = APIRouter(prefix="/api/settings", tags=["settings"])


async def _get_or_create(db: AsyncSession) -> GlobalSettings:
    row = await db.get(GlobalSettings, 1)
    if not row:
        row = GlobalSettings(id=1)
        db.add(row)
        await db.commit()
        await db.refresh(row)
    return row


@router.get("/git", response_model=GlobalSettingsResponse)
async def get_git_settings(db: AsyncSession = Depends(get_db)):
    return await _get_or_create(db)


@router.put("/git", response_model=GlobalSettingsResponse)
async def update_git_settings(body: GlobalSettingsUpdate, db: AsyncSession = Depends(get_db)):
    row = await _get_or_create(db)
    for key, value in body.model_dump().items():
        setattr(row, key, value or None)
    await db.commit()
    await db.refresh(row)
    return row
