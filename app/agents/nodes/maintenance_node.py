from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, select

from app.agents.state import AgentState
from app.core.database import SessionLocal
from app.models.base import Cycle, Idea, Signal, Trend

logger = logging.getLogger(__name__)

# Chroma: очистка эмбеддингов — следующий спринт (закомментировано по P1)
# from app.services.chroma_service import prune_old_embeddings


def _passed_ideas_count_from_state(state: AgentState) -> int:
    scored = state.get("scored_ideas") or []
    return sum(1 for x in scored if x.get("verdict") == "pass")


async def maintenance_node(state: AgentState) -> AgentState:
    cycle_id: UUID | None = state.get("cycle_id")
    passed_count = _passed_ideas_count_from_state(state)

    async with SessionLocal() as session:
        cycle: Cycle | None = await session.get(Cycle, cycle_id) if cycle_id else None
        signals_count = 0
        trends_count = 0
        ideas_count = 0

        if cycle_id is not None:
            signals_count = int(
                await session.scalar(
                    select(func.count()).select_from(Signal).where(Signal.cycle_id == cycle_id)
                )
                or 0
            )
            trends_count = int(
                await session.scalar(
                    select(func.count()).select_from(Trend).where(Trend.cycle_id == cycle_id)
                )
                or 0
            )
            ideas_count = int(
                await session.scalar(
                    select(func.count()).select_from(Idea).where(Idea.cycle_id == cycle_id)
                )
                or 0
            )

        # ТЗ P1: удалить сигналы старше 30 дней (в схеме нет created_at — используем timestamp)
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        del_result = await session.execute(delete(Signal).where(Signal.timestamp < cutoff))
        deleted_old = del_result.rowcount if del_result.rowcount is not None else 0

        if cycle is not None:
            cycle.status = "completed"
            cycle.end_date = datetime.now(timezone.utc)

        await session.commit()

        stats: dict[str, Any] = {
            "cycle_id": str(cycle_id) if cycle_id else None,
            "signals_count": signals_count,
            "trends_count": trends_count,
            "ideas_count": ideas_count,
            "passed_ideas_count": passed_count,
            "deleted_signals_older_than_30d": deleted_old,
        }
        logger.info("Maintenance completed stats=%s", stats)

    return {**state, "stage": "completed"}
