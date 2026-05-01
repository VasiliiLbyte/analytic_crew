from __future__ import annotations

from typing import Any

from fastapi import APIRouter

router = APIRouter()


@router.post("/access/approve")
async def approve_access(body: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "approved",
        "user_id": body.get("user_id"),
        "workspace_id": body.get("workspace_id"),
    }
