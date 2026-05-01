from __future__ import annotations

import json
import logging
from pathlib import Path
from uuid import UUID

from app.agents.schemas import TrendSpotterOutput
from app.agents.state import AgentState, TrendPayload
from app.core.config import build_llm_client
from app.core.database import SessionLocal
from app.models.base import Cycle, Trend

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "trend_spotter.txt"
MAX_SIGNALS_FOR_LLM = 15
MAX_TEXT_LENGTH = 1000


async def trend_spotter_node(state: AgentState) -> AgentState:
    cycle_id = state.get("cycle_id")
    if cycle_id is None:
        logger.warning("Trend spotter skipped due to missing cycle id")
        return {**state, "trends": [], "stage": "completed"}

    raw_signals = state.get("raw_signals", [])
    trend_payloads = await _generate_trends_from_llm(cycle_id=cycle_id, raw_signals=raw_signals)

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
            cycle.current_phase = "analyst"

        await session.commit()
        logger.info("Trend spotter persisted %s trends for cycle %s", len(trend_models), cycle_id)

    return {**state, "trends": trend_payloads, "stage": "analyst"}


async def _generate_trends_from_llm(cycle_id: UUID, raw_signals: list[dict]) -> list[TrendPayload]:
    if not raw_signals:
        return []

    compact_signals = _prepare_signals_for_llm(raw_signals)
    prompt_text = PROMPT_PATH.read_text(encoding="utf-8")
    llm = (await build_llm_client()).with_structured_output(TrendSpotterOutput)

    user_payload = json.dumps(
        {
            "cycle_id": str(cycle_id),
            "raw_signals": compact_signals,
        },
        ensure_ascii=True,
    )

    llm_result = await llm.ainvoke(
        [
            ("system", prompt_text),
            ("user", user_payload),
        ]
    )

    parsed = TrendSpotterOutput.model_validate(llm_result)
    payloads: list[TrendPayload] = []
    available_signal_ids = {signal["id"] for signal in raw_signals}

    for trend in parsed.trends:
        filtered_signal_ids = [signal_id for signal_id in trend.related_signal_ids if signal_id in available_signal_ids]
        if not filtered_signal_ids:
            continue

        payloads.append(
            TrendPayload(
                trend_name=trend.trend_name,
                description=trend.description,
                related_signals=filtered_signal_ids,
                metadata_json={
                    "confidence": trend.confidence,
                    "key_drivers": trend.key_drivers,
                    "signal_count": len(filtered_signal_ids),
                },
            )
        )
    return payloads


def _prepare_signals_for_llm(raw_signals: list[dict]) -> list[dict]:
    sorted_signals = sorted(
        raw_signals,
        key=lambda signal: signal.get("timestamp") or "",
        reverse=True,
    )
    selected = sorted_signals[:MAX_SIGNALS_FOR_LLM]
    compact: list[dict] = []
    for signal in selected:
        raw_data = signal.get("raw_data_json")
        compact.append(
            {
                "id": str(signal["id"]),
                "source_type": signal.get("source_type"),
                "source_url": _trim_text(signal.get("source_url")),
                "headline": _trim_text(_extract_headline(signal)),
                "summary": _trim_text(signal.get("content_snippet")),
                "raw_highlights": _trim_text(_compact_raw_data(raw_data)),
                "timestamp": signal.get("timestamp").isoformat() if signal.get("timestamp") else None,
            }
        )
    return compact


def _extract_headline(signal: dict) -> str:
    raw_data = signal.get("raw_data_json")
    if isinstance(raw_data, dict):
        for key in ("title", "trend_name", "name"):
            value = raw_data.get(key)
            if isinstance(value, str) and value.strip():
                return value
    snippet = signal.get("content_snippet")
    return snippet if isinstance(snippet, str) else ""


def _compact_raw_data(raw_data: object) -> str:
    if isinstance(raw_data, dict):
        preferred_keys = (
            "query",
            "title",
            "company",
            "area",
            "skills",
            "categories",
            "trend_tags",
            "description",
        )
        compact_dict = {key: raw_data.get(key) for key in preferred_keys if key in raw_data}
        return json.dumps(compact_dict, ensure_ascii=True)
    if isinstance(raw_data, list):
        return json.dumps(raw_data[:10], ensure_ascii=True)
    return str(raw_data or "")


def _trim_text(value: object) -> str:
    text = value if isinstance(value, str) else str(value or "")
    return text.strip()[:MAX_TEXT_LENGTH]
