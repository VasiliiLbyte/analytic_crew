from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/access")
async def access_stub() -> dict[str, str]:
    return {"status": "not_implemented_yet"}
