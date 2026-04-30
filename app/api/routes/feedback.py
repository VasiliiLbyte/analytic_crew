from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.agents.graph import run_graph  # noqa: F401 — возобновление графа через checkpointer (Sprint 2)
from app.agents.state import AgentState  # noqa: F401

router = APIRouter()


@router.post("/ideas/{idea_id}/feedback")
async def submit_feedback(idea_id: str, body: dict[str, Any]) -> dict[str, Any]:
    # Здесь будет возобновление графа через checkpointer
    # Пока заглушка
    return {"status": "feedback received", "idea_id": idea_id, "action": body.get("action")}
