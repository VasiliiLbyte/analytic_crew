from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.core.database import SessionLocal
from app.models.base import LLMCache as LLMCacheModel

logger = logging.getLogger(__name__)


def compute_prompt_hash(prompt: str) -> str:
    return hashlib.sha256(prompt.encode()).hexdigest()


class LLMCache:
    async def get(self, prompt: str) -> dict | list | None:
        prompt_hash = compute_prompt_hash(prompt)
        now = datetime.now(timezone.utc)

        async with SessionLocal() as session:
            stmt = select(LLMCacheModel).where(
                LLMCacheModel.prompt_hash == prompt_hash,
                LLMCacheModel.expires_at.is_(None) | (LLMCacheModel.expires_at > now),
            )
            result = await session.execute(stmt)
            cache = result.scalar_one_or_none()
            if cache is None:
                return None

            cache.hit_count += 1
            await session.commit()
            return cache.response_json

    async def set(
        self, prompt: str, response: dict | list, ttl_days: int = 7
    ) -> None:
        prompt_hash = compute_prompt_hash(prompt)
        expires = datetime.now(timezone.utc) + timedelta(days=ttl_days)

        async with SessionLocal() as session:
            stmt = insert(LLMCacheModel).values(
                prompt_hash=prompt_hash,
                response_json=response,
                expires_at=expires,
                hit_count=1,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=[LLMCacheModel.prompt_hash],
                set_={
                    "response_json": response,
                    "expires_at": expires,
                    "hit_count": LLMCacheModel.hit_count + 1,
                },
            )
            await session.execute(stmt)
            await session.commit()
