from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/trends")
async def trends_stub() -> dict[str, str]:
    return {"status": "not_implemented_yet"}
