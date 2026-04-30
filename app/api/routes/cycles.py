from __future__ import annotations

from fastapi import APIRouter
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.base import Cycle

router = APIRouter()


@router.get("/cycle/current")
async def get_current_cycle() -> dict | None:
    async with SessionLocal() as session:
        stmt = select(Cycle).order_by(Cycle.created_at.desc()).limit(1)
        result = await session.execute(stmt)
        cycle = result.scalar_one_or_none()
        if cycle is None:
            return None
        return jsonable_encoder(cycle)
