from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from app.agents.state import AgentState
from app.core.config import build_llm_client
from app.core.database import SessionLocal
from app.models.base import AgentLog

logger = logging.getLogger(__name__)
PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "validator.txt"


def _llm_result_to_jsonable(result: Any) -> dict[str, Any]:
    if hasattr(result, "model_dump"):
        return result.model_dump(mode="json")
    content = getattr(result, "content", None)
    if isinstance(content, str):
        return {"content": content}
    if isinstance(content, list):
        return {"content": content}
    return {"content": str(result)}


async def validator_node(state: AgentState) -> AgentState:
    validated_cards = state.get("validated_cards", [])
    if not validated_cards:
        return {**state, "stage": "validator_completed"}

    llm = build_llm_client()  # structured output позже
    for card in validated_cards:
        prompt_text = PROMPT_PATH.read_text(encoding="utf-8")
        result = await llm.ainvoke([("system", prompt_text), ("user", str(card))])
        # пока просто логируем
        async with SessionLocal() as session:
            log = AgentLog(
                cycle_id=state.get("cycle_id"),
                agent_name="validator_node",
                input_state_json=card if isinstance(card, dict) else {"card": str(card)},
                output_state_json=_llm_result_to_jsonable(result),
            )
            session.add(log)
            await session.commit()

    new_state = {**state, "stage": "validator_completed"}
    logger.info("Validator node completed")
    return new_state
