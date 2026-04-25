from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

import aiohttp
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


class RawSignal(BaseModel):
    model_config = ConfigDict(extra="allow")

    source_url: str | None = None
    source_type: str
    content_snippet: str
    raw_data: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime | None = None

    def with_default_timestamp(self) -> "RawSignal":
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)
        return self


class BaseParser(ABC):
    def __init__(
        self,
        source_name: str,
        source_type: str,
        rate_limit_rpm: int = 40,
        timeout_seconds: int = 15,
        max_retries: int = 2,
    ) -> None:
        self.source_name = source_name
        self.source_type = source_type
        self.rate_limit_rpm = max(rate_limit_rpm, 1)
        self.request_delay = 60.0 / self.rate_limit_rpm
        self.timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        self.max_retries = max(max_retries, 0)

    @abstractmethod
    async def fetch(self, session: aiohttp.ClientSession, **kwargs: Any) -> list[RawSignal]:
        raise NotImplementedError

    async def run_with_rate_limit(self, **kwargs: Any) -> list[RawSignal]:
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                logger.info("Parser %s started", self.source_name)
                result = await self.fetch(session, **kwargs)
                await asyncio.sleep(self.request_delay)
                return [signal.with_default_timestamp() for signal in result]
        except Exception:
            logger.exception("Parser %s failed", self.source_name)
            return []

    async def get_json(
        self,
        session: aiohttp.ClientSession,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                async with session.get(url, params=params, headers=headers) as response:
                    response.raise_for_status()
                    return await response.json()
            except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                last_error = exc
                if attempt < self.max_retries:
                    backoff = min(2**attempt, 5)
                    await asyncio.sleep(backoff)
                    continue
                break

        if last_error is not None:
            raise last_error
        raise RuntimeError(f"Failed to fetch JSON from {url}")
