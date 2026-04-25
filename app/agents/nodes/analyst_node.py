from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

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
        return {**state, "stage": "completed"}

    selected_trend = _pick_trend(trends)
    analysis = await _generate_analysis(selected_trend=selected_trend)

    async with SessionLocal() as session:
        idea = Idea(
            cycle_id=cycle_id,
            title=analysis.title,
            problem=analysis.problem,
            solution=analysis.solution,
            market_analysis_json=analysis.as_market_analysis_json(),
            validation_status="pending",
        )
        session.add(idea)

        cycle = await session.get(Cycle, cycle_id)
        if cycle is not None:
            cycle.current_phase = "completed"
            cycle.status = "completed"
            cycle.end_date = datetime.now(timezone.utc)

        await session.commit()
        logger.info("Analyst node persisted idea for cycle %s", cycle_id)

    return {**state, "stage": "completed"}


def _pick_trend(trends: list[TrendPayload]) -> TrendPayload:
    return max(
        trends,
        key=lambda trend: float((trend.get("metadata_json") or {}).get("confidence", 0.0)),
    )


async def _generate_analysis(selected_trend: TrendPayload) -> AnalystOutput:
    prompt_text = PROMPT_PATH.read_text(encoding="utf-8")
    llm = build_llm_client().with_structured_output(AnalystOutput)

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
