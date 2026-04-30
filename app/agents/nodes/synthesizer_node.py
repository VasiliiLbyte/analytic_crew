from __future__ import annotations

import json
import logging
from pathlib import Path

from app.agents.schemas import SynthesizerOutput
from app.agents.state import AgentState
from app.core.config import build_llm_client
from app.core.database import SessionLocal
from app.models.base import AgentLog

logger = logging.getLogger(__name__)
PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "synthesizer.txt"


async def synthesizer_node(state: AgentState) -> AgentState:
    scored_ideas = state.get("scored_ideas", [])
    passed = [i for i in scored_ideas if i.get("verdict") == "pass"]
    if not passed:
        logger.warning("Synthesizer skipped: no passed ideas")
        return {**state, "stage": "synthesizer_completed", "validated_cards": []}

    llm = build_llm_client().with_structured_output(SynthesizerOutput)
    cards = []
    for idea in passed[:5]:  # топ-5
        prompt_text = PROMPT_PATH.read_text(encoding="utf-8")
        result = await llm.ainvoke(
            [("system", prompt_text), ("user", json.dumps(idea, ensure_ascii=False))]
        )
        output = SynthesizerOutput.model_validate(result)
        cards.extend(output.cards)

        # логируем
        async with SessionLocal() as session:
            log = AgentLog(
                cycle_id=state.get("cycle_id"),
                agent_name="synthesizer_node",
                input_state_json=idea,
                output_state_json=output.model_dump(mode="json"),
            )
            session.add(log)
            await session.commit()

    new_state = {**state, "validated_cards": [c.model_dump(mode="json") for c in cards], "stage": "synthesizer_completed"}
    logger.info("Synthesizer created %s cards", len(cards))
    return new_state
