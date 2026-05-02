from __future__ import annotations

import asyncio
import os

from app.agents.graph import run_graph
from app.agents.initial_state import build_initial_agent_state
from app.agents.state import AgentState


async def main() -> None:
    initial_state = build_initial_agent_state()
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
