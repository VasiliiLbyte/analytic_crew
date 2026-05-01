from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException
from fastapi.encoders import jsonable_encoder

from app.core.database import SessionLocal
from app.models.base import Signal

router = APIRouter()


@router.get("/signals/{signal_id}")
async def get_signal(signal_id: UUID) -> dict:
    async with SessionLocal() as session:
        signal = await session.get(Signal, signal_id)
        if signal is None:
            raise HTTPException(status_code=404, detail="Signal not found")
        return jsonable_encoder(signal)
