from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.agents.state import AgentState
from app.core.database import SessionLocal
from app.models.base import Cycle

logger = logging.getLogger(__name__)


async def maintenance_node(state: AgentState) -> AgentState:
    cycle_id = state.get("cycle_id")
    async with SessionLocal() as session:
        cycle = await session.get(Cycle, cycle_id)
        if cycle:
            cycle.status = "completed"
            cycle.end_date = datetime.now(timezone.utc)
            await session.commit()
    logger.info("Maintenance completed cycle %s", cycle_id)
    return {**state, "stage": "completed"}
