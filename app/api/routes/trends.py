from __future__ import annotations

from fastapi import APIRouter
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.base import Trend

router = APIRouter()


@router.get("/trends")
async def get_trends() -> list[dict]:
    async with SessionLocal() as session:
        stmt = select(Trend).order_by(Trend.created_at.desc())
        result = await session.execute(stmt)
        trends = result.scalars().all()
        return [jsonable_encoder(row) for row in trends]
