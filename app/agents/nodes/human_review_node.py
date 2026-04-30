from __future__ import annotations

import logging

from langgraph.types import interrupt

from app.agents.state import AgentState

logger = logging.getLogger(__name__)


async def human_review_node(state: AgentState) -> AgentState:
    logger.info("Human review node — interrupting for HITL")
    human_input = interrupt(
        {
            "validated_cards": state.get("validated_cards", []),
            "cycle_id": str(state.get("cycle_id")),
            "message": "Требуется проверка и одобрение идей",
        }
    )
    payload = human_input if isinstance(human_input, dict) else {}
    return {
        **state,
        "human_decision": payload.get("action"),
        "human_comment": payload.get("comment"),
        "target_agent": payload.get("target_agent"),
        "stage": "human_reviewed",
    }
