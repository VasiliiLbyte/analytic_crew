from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.agents.schemas import AnalystOutput
from app.agents.state import AgentState, TrendPayload
from app.core.config import build_llm_client
from app.core.database import SessionLocal
from app.models.base import Cycle, Idea

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "analyst.txt"


async def analyst_node(state: AgentState) -> AgentState:
    cycle_id = state.get("cycle_id")
    trends = state.get("trends", [])
    if cycle_id is None or not trends:
        logger.warning("Analyst node skipped due to missing cycle or trends")
        return {**state, "stage": "analyst_completed", "analysis_drafts": []}

    # Берём TOP-10 трендов по confidence (или все, если меньше 10)
    top_trends = sorted(
        trends,
        key=lambda t: float((t.get("metadata_json") or {}).get("confidence", 0.0)),
        reverse=True
    )[:10]

    analysis_drafts: list[dict[str, Any]] = []
    for trend in top_trends:
        analysis = await _generate_analysis(selected_trend=trend)
        draft = {
            "trend_id": trend.get("trend_name"),  # или любой уникальный идентификатор
            "title": analysis.title,
            "problem": analysis.problem,
            "solution": analysis.solution,
            "market_analysis_json": analysis.as_market_analysis_json() if hasattr(analysis, "as_market_analysis_json") else {},
            "sources": [str(s) for s in trend.get("related_signals", [])],
        }
        analysis_drafts.append(draft)

    # Сохраняем черновики в state (анализ_drafts)
    new_state = {
        **state,
        "analysis_drafts": analysis_drafts,
        "stage": "analyst_completed",
    }

    # НЕ сохраняем Idea в БД здесь и НЕ ставим cycle.status = completed!
    # Это будет делать Critic / Synthesizer / Maintenance позже
    logger.info(f"Analyst node generated {len(analysis_drafts)} drafts for cycle {cycle_id}")
    return new_state


def _pick_trend(trends: list[TrendPayload]) -> TrendPayload:
    return max(
        trends,
        key=lambda trend: float((trend.get("metadata_json") or {}).get("confidence", 0.0)),
    )


async def _generate_analysis(selected_trend: TrendPayload) -> AnalystOutput:
    prompt_text = PROMPT_PATH.read_text(encoding="utf-8")
    llm = (await build_llm_client()).with_structured_output(AnalystOutput)

    user_payload = json.dumps(
        {
            "trend": {
                "trend_name": selected_trend.get("trend_name"),
                "description": selected_trend.get("description"),
                "related_signals": [str(signal_id) for signal_id in selected_trend.get("related_signals", [])],
                "metadata_json": selected_trend.get("metadata_json", {}),
            }
        },
        ensure_ascii=True,
    )

    llm_result = await llm.ainvoke([("system", prompt_text), ("user", user_payload)])
    return AnalystOutput.model_validate(llm_result)
