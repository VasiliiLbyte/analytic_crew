from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from app.agents.state import AgentState, RawSignalPayload, TrendPayload
from app.core.database import SessionLocal
from app.models.base import Cycle, Trend

logger = logging.getLogger(__name__)

TREND_KEYWORDS: tuple[str, ...] = ("AI", "SaaS", "Web3")


async def trend_spotter_node(state: AgentState) -> AgentState:
    cycle_id = state.get("cycle_id")
    if cycle_id is None:
        logger.warning("Trend spotter skipped due to missing cycle_id")
        return {**state, "trends": [], "stage": "completed"}

    grouped = _group_signals_by_keyword(raw_signals=state.get("raw_signals", []))
    trend_payloads = _build_trend_payloads(grouped=grouped)

    async with SessionLocal() as session:
        trend_models = [
            Trend(
                cycle_id=cycle_id,
                trend_name=payload["trend_name"],
                description=payload["description"],
                related_signals=payload["related_signals"],
                metadata_json=payload["metadata_json"],
            )
            for payload in trend_payloads
        ]
        if trend_models:
            session.add_all(trend_models)

        cycle = await session.get(Cycle, cycle_id)
        if cycle is not None:
            cycle.current_phase = "completed"
            cycle.status = "completed"
            cycle.end_date = datetime.now(timezone.utc)

        await session.commit()
        logger.info("Trend spotter persisted %s trends for cycle %s", len(trend_models), cycle_id)

    return {**state, "trends": trend_payloads, "stage": "completed"}


def _group_signals_by_keyword(raw_signals: list[RawSignalPayload]) -> dict[str, list[RawSignalPayload]]:
    grouped: dict[str, list[RawSignalPayload]] = {keyword: [] for keyword in TREND_KEYWORDS}
    for signal in raw_signals:
        searchable_text = " ".join(
            [
                str(signal.get("content_snippet") or ""),
                str(signal.get("raw_data_json") or ""),
                str(signal.get("source_type") or ""),
            ]
        ).lower()

        for keyword in TREND_KEYWORDS:
            if keyword.lower() in searchable_text:
                grouped[keyword].append(signal)
    return grouped


def _build_trend_payloads(grouped: dict[str, list[RawSignalPayload]]) -> list[TrendPayload]:
    payloads: list[TrendPayload] = []
    for keyword, signals in grouped.items():
        if not signals:
            continue

        signal_ids: list[UUID] = [signal["id"] for signal in signals]
        payloads.append(
            TrendPayload(
                trend_name=keyword,
                description=f"Keyword cluster for {keyword} based on scout signals.",
                related_signals=signal_ids,
                metadata_json={
                    "signal_count": len(signals),
                    "source_types": sorted({str(signal.get("source_type") or "unknown") for signal in signals}),
                },
            )
        )
    return payloads
