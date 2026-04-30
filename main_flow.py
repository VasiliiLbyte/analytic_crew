from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from app.agents.graph import run_graph
from app.models.base import Cycle
from app.core.database import SessionLocal


async def main() -> None:
    load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

    async with SessionLocal() as session:
        cycle = Cycle(start_date=datetime.now(timezone.utc), status="running", current_phase="scout")
        session.add(cycle)
        await session.commit()
        await session.refresh(cycle)

        initial_state = {
            "cycle_id": cycle.id,
            "raw_signals": [],
            "trends": [],
            "stage": "scout",
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

        print("Execution finished")
        print(f"cycle_id: {result.get('cycle_id')}")
        print(f"final_stage: {result.get('stage')}")
        print(f"signals_in_state: {len(result.get('raw_signals', []))}")
        print(f"trends_in_state: {len(result.get('trends', []))}")


if __name__ == "__main__":
    asyncio.run(main())
