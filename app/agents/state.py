from __future__ import annotations

from datetime import datetime
from typing import Any, TypedDict
from uuid import UUID


class RawSignalPayload(TypedDict):
    id: UUID
    source_url: str | None
    source_type: str | None
    content_snippet: str | None
    raw_data_json: dict[str, Any] | list[Any] | None
    timestamp: datetime


class TrendPayload(TypedDict):
    trend_name: str
    description: str
    related_signals: list[UUID]
    metadata_json: dict[str, Any]


class AgentState(TypedDict):
    cycle_id: UUID | None
    raw_signals: list[RawSignalPayload]
    trends: list[TrendPayload]
    stage: str
