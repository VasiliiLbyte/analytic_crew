from __future__ import annotations

import asyncio
import os
from uuid import uuid4

from app.agents.graph import run_graph
from app.agents.state import AgentState


def _build_initial_state() -> AgentState:
    return {
        "cycle_id": uuid4(),
        "raw_signals": [],
        "trends": [],
        "stage": "start",
        "user_id": None,
        "workspace_id": None,
        "analysis_drafts": [],
        "scored_ideas": [],
        "validated_cards": [],
        "feedback_history": [],
        "errors": [],
        "human_decision": None,
        "human_comment": None,
        "target_agent": None,
    }


async def main() -> None:
    initial_state = _build_initial_state()
    if os.getenv("MOCK_RUN", "false").lower() in {"1", "true", "yes", "on"}:
        result: AgentState = {
            **initial_state,
            "stage": "mock_completed",
            "validated_cards": [{"title": "Mock Idea", "source": "main_flow"}],
        }
    else:
        result = await run_graph(initial_state)
    print("Cycle completed:", result.get("stage"))
    print("Validated cards:", len(result.get("validated_cards", [])))


if __name__ == "__main__":
    asyncio.run(main())
