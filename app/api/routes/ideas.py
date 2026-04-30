from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.base import Idea

router = APIRouter()


@router.get("/ideas")
async def list_ideas() -> list[dict]:
    async with SessionLocal() as session:
        stmt = select(Idea).order_by(Idea.created_at.desc())
        result = await session.execute(stmt)
        ideas = result.scalars().all()
        return [jsonable_encoder(row) for row in ideas]


@router.get("/ideas/{idea_id}")
async def get_idea(idea_id: UUID) -> dict:
    async with SessionLocal() as session:
        idea = await session.get(Idea, idea_id)
        if idea is None:
            raise HTTPException(status_code=404, detail="Idea not found")
        return jsonable_encoder(idea)
