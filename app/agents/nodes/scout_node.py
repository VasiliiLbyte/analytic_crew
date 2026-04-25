from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select

from app.agents.state import AgentState, RawSignalPayload
from app.core.database import SessionLocal
from app.models.base import Cycle, Signal
from app.services.scout_service import ScoutService

logger = logging.getLogger(__name__)


async def scout_node(state: AgentState) -> AgentState:
    async with SessionLocal() as session:
        cycle_id = await _ensure_cycle(session=session, cycle_id=state.get("cycle_id"))
        await _set_cycle_phase(session=session, cycle_id=cycle_id, phase="scout")

        scout_service = ScoutService()
        await scout_service.collect_and_store(db_session=session, cycle_id=cycle_id)

        raw_signals = await _load_cycle_signals(session=session, cycle_id=cycle_id)
        logger.info("Scout node loaded %s signals for cycle %s", len(raw_signals), cycle_id)

    return {
        **state,
        "cycle_id": cycle_id,
        "raw_signals": raw_signals,
        "stage": "trend_spotter",
    }


async def _ensure_cycle(session, cycle_id: UUID | None) -> UUID:
    if cycle_id is not None:
        existing = await session.get(Cycle, cycle_id)
        if existing is not None:
            return existing.id

    new_cycle = Cycle(start_date=datetime.now(timezone.utc), status="running", current_phase="scout")
    session.add(new_cycle)
    await session.commit()
    await session.refresh(new_cycle)
    return new_cycle.id


async def _set_cycle_phase(session, cycle_id: UUID, phase: str) -> None:
    cycle = await session.get(Cycle, cycle_id)
    if cycle is None:
        return
    cycle.current_phase = phase
    await session.commit()


async def _load_cycle_signals(session, cycle_id: UUID) -> list[RawSignalPayload]:
    stmt = select(Signal).where(Signal.cycle_id == cycle_id).order_by(Signal.timestamp.desc())
    rows = await session.scalars(stmt)
    result: list[RawSignalPayload] = []
    for signal in rows.all():
        result.append(
            RawSignalPayload(
                id=signal.id,
                source_url=signal.source_url,
                source_type=signal.source_type,
                content_snippet=signal.content_snippet,
                raw_data_json=signal.raw_data_json,
                timestamp=signal.timestamp,
            )
        )
    return result
