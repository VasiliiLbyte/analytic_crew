from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.base import Idea

router = APIRouter()


@router.get("/ideas")
async def list_ideas(
    status: str | None = Query(default=None, description="Фильтр по Idea.status"),
    min_score: float | None = Query(default=None, ge=0.0, le=100.0, description="Минимум critic_score"),
    cycle_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[dict]:
    async with SessionLocal() as session:
        stmt = select(Idea).order_by(Idea.created_at.desc())
        if status is not None and status.strip():
            stmt = stmt.where(Idea.status == status.strip())
        if min_score is not None:
            stmt = stmt.where(Idea.critic_score.is_not(None), Idea.critic_score >= min_score)
        if cycle_id is not None:
            stmt = stmt.where(Idea.cycle_id == cycle_id)

        stmt = stmt.offset(offset).limit(limit)
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
