from __future__ import annotations

import asyncio
import json
import logging
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from app.agents.graph import run_graph
from app.agents.initial_state import build_initial_agent_state
from app.agents.state import AgentState
from app.core.database import SessionLocal
from app.models.base import AgentLog, Cycle

logger = logging.getLogger(__name__)

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
