from __future__ import annotations

import asyncio
import logging
import time
from uuid import uuid4

from redis.asyncio import Redis

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class TokenBucketRateLimiter:
    def __init__(self, redis: Redis, key: str = "nvidia_llm", rpm: int | None = None) -> None:
        self.redis = redis
        self.key = key
        self.rpm = rpm if rpm is not None else get_settings().llm_rpm
        self.capacity = self.rpm
        self.refill_rate = self.rpm / 60.0

    async def acquire(self) -> bool:
        now = time.time()
        member = f"{now}:{uuid4()}"
        pipe = self.redis.pipeline(transaction=True)
        pipe.zremrangebyscore(self.key, 0, now - 60)
        pipe.zadd(self.key, {member: now})
        pipe.zcard(self.key)
        pipe.expire(self.key, 60)
        _, _, count, _ = await pipe.execute()
        if int(count) > self.capacity:
            await self.redis.zrem(self.key, member)
            return False
        return True

    async def wait_for_token(self, max_wait: int = 60) -> None:
        for _ in range(max_wait):
            if await self.acquire():
                return
            await asyncio.sleep(1)
        raise TimeoutError("Rate limit exceeded")
