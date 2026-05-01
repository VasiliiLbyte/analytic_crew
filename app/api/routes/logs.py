from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.base import AgentLog

router = APIRouter()


@router.get("/agent_logs/{cycle_id}")
async def get_agent_logs(cycle_id: UUID) -> list[dict]:
    async with SessionLocal() as session:
        stmt = (
            select(AgentLog)
            .where(AgentLog.cycle_id == cycle_id)
            .order_by(AgentLog.timestamp.desc())
        )
        result = await session.execute(stmt)
        logs = result.scalars().all()
        return [jsonable_encoder(row) for row in logs]
