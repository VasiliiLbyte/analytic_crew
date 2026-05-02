from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select

from app.agents.graph import run_graph
from app.agents.initial_state import build_initial_agent_state
from app.agents.scoring import PASS_THRESHOLD
from app.agents.state import AgentState
from app.core.database import SessionLocal
from app.models.base import AgentLog, Cycle, Idea, Signal, Trend

logger = logging.getLogger(__name__)

router = APIRouter()

_PHASE_TO_PROGRESS: dict[str, int] = {
    "scout": 10,
    "trend_spotter": 22,
    "analyst": 40,
    "critic": 52,
    "synthesizer": 68,
    "validator": 82,
    "human_review": 94,
    "completed": 100,
    "running": 5,
}


def _progress_percent(phase: str | None) -> int:
    if not phase:
        return 0
    key = (phase or "").strip().lower()
    return _PHASE_TO_PROGRESS.get(key, 15)


@router.get("/cycle/current")
async def get_current_cycle() -> dict | None:
    async with SessionLocal() as session:
        stmt = select(Cycle).order_by(Cycle.created_at.desc()).limit(1)
        result = await session.execute(stmt)
        cycle = result.scalar_one_or_none()
        if cycle is None:
            return None

        cid = cycle.id
        signals_count = int(
            await session.scalar(select(func.count()).select_from(Signal).where(Signal.cycle_id == cid)) or 0
        )
        trends_count = int(
            await session.scalar(select(func.count()).select_from(Trend).where(Trend.cycle_id == cid)) or 0
        )
        ideas_count = int(
            await session.scalar(select(func.count()).select_from(Idea).where(Idea.cycle_id == cid)) or 0
        )
        passed_ideas_count = int(
            await session.scalar(
                select(func.count())
                .select_from(Idea)
                .where(Idea.cycle_id == cid, Idea.critic_score.is_not(None), Idea.critic_score >= PASS_THRESHOLD)
            )
            or 0
        )

        payload = jsonable_encoder(cycle)
        payload["timestamp"] = datetime.now(timezone.utc).isoformat()
        payload["signals_count"] = signals_count
        payload["trends_count"] = trends_count
        payload["ideas_count"] = ideas_count
        payload["passed_ideas_count"] = passed_ideas_count
        payload["current_phase"] = cycle.current_phase
        payload["progress_percent"] = _progress_percent(cycle.current_phase)
        return payload


async def fetch_latest_logs_for_cycle(cycle_id: UUID) -> list[dict]:
    async with SessionLocal() as session:
        stmt = (
            select(AgentLog)
            .where(AgentLog.cycle_id == cycle_id)
            .order_by(AgentLog.timestamp.desc())
            .limit(50)
        )
        result = await session.execute(stmt)
        rows = result.scalars().all()
        return [jsonable_encoder(row) for row in rows]


async def _run_graph_background(initial_state: AgentState) -> None:
    try:
        await run_graph(initial_state)
    except Exception:
        logger.exception("Background run_graph failed for cycle_id=%s", initial_state.get("cycle_id"))


@router.post("/cycle/start")
async def start_cycle(background_tasks: BackgroundTasks) -> dict[str, str]:
    initial_state = build_initial_agent_state()
    background_tasks.add_task(_run_graph_background, initial_state)
    return {"status": "started", "cycle_id": str(initial_state["cycle_id"])}


@router.get("/cycle/{cycle_id}/stream")
async def stream_cycle_status(cycle_id: str, request: Request) -> StreamingResponse:
    try:
        wid = UUID(cycle_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid cycle_id") from exc

    async def event_generator():
        while True:
            if await request.is_disconnected():
                break
            logs = await fetch_latest_logs_for_cycle(wid)
            yield f"data: {json.dumps(logs)}\n\n"
            await asyncio.sleep(2)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
