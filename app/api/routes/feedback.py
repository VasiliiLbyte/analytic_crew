from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from langgraph.types import Command

from app.agents.graph import build_graph

router = APIRouter()


@router.post("/ideas/{idea_id}/feedback")
async def submit_feedback(idea_id: str, body: dict[str, Any]) -> dict[str, Any]:
    action = body.get("action")
    if not isinstance(action, str) or not action.strip():
        raise HTTPException(status_code=400, detail="Field 'action' is required")

    thread_id = body.get("thread_id") or idea_id
    if not isinstance(thread_id, str) or not thread_id.strip():
        raise HTTPException(status_code=400, detail="Field 'thread_id' must be a non-empty string")

    feedback_payload = {
        "action": action,
        "comment": body.get("comment"),
        "target_agent": body.get("target_agent"),
    }
    config = {"configurable": {"thread_id": thread_id}}
    async with build_graph() as graph:
        result = await graph.ainvoke(Command(resume=feedback_payload), config=config)

    return {
        "status": "ok",
        "message": "HITL feedback processed",
        "idea_id": idea_id,
        "thread_id": thread_id,
        "stage": result.get("stage"),
    }
