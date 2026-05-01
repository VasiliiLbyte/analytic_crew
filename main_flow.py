from __future__ import annotations

import asyncio
from uuid import uuid4

from app.agents.state import AgentState
from app.agents.graph import run_graph


async def main() -> None:
    initial_state: AgentState = {
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
    result = await run_graph(initial_state)
    print("Cycle completed:", result.get("stage"))
    print("Validated cards:", len(result.get("validated_cards", [])))


if __name__ == "__main__":
    asyncio.run(main())
