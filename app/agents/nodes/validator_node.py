from __future__ import annotations

import json
import logging
from pathlib import Path
from uuid import UUID

from app.agents.schemas import ValidatorOutput
from app.agents.state import AgentState
from app.core.config import build_llm_client, get_settings
from app.core.database import SessionLocal
from app.models.base import AgentLog, Idea

logger = logging.getLogger(__name__)
PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "validator.txt"


async def validator_node(state: AgentState) -> AgentState:
    validated_cards = state.get("validated_cards", [])
    if not validated_cards:
        return {**state, "stage": "validator_completed"}

    cycle_id = state.get("cycle_id")
    settings = get_settings()
    rate_limiter = settings.get_rate_limiter()
    cache = await settings.get_llm_cache()
    llm = (await build_llm_client()).with_structured_output(ValidatorOutput)
    errors = list(state.get("errors", []))

    for card in validated_cards:
        prompt_text = PROMPT_PATH.read_text(encoding="utf-8")
        user_payload = json.dumps(card, ensure_ascii=False) if isinstance(card, dict) else str(card)
        cache_key = prompt_text + user_payload

        idea_id_raw = card.get("idea_id") if isinstance(card, dict) else None
        idea_uuid: UUID | None = None
        if isinstance(idea_id_raw, str) and idea_id_raw:
            try:
                idea_uuid = UUID(idea_id_raw)
            except ValueError:
                logger.warning("validator_node: invalid idea_id %s", idea_id_raw)

        try:
            cached = await cache.get(cache_key)
            if cached:
                validator_output = ValidatorOutput.model_validate(cached)
            else:
                await rate_limiter.wait_for_token()
                llm_result = await llm.ainvoke([("system", prompt_text), ("user", user_payload)])
                validator_output = ValidatorOutput.model_validate(llm_result)
                await cache.set(cache_key, validator_output.model_dump(mode="json"))

            payload = validator_output.model_dump(mode="json")

            async with SessionLocal() as session:
                log = AgentLog(
                    cycle_id=cycle_id,
                    agent_name="validator_node",
                    input_state_json=card if isinstance(card, dict) else {"card": str(card)},
                    output_state_json=payload,
                )
                session.add(log)

                if idea_uuid is not None and cycle_id is not None:
                    row = await session.get(Idea, idea_uuid)
                    if row is not None and row.cycle_id == cycle_id:
                        row.validation_data_json = payload
                        row.status = "approved"
                    elif row is not None:
                        logger.warning(
                            "validator_node: idea %s cycle mismatch (skip DB update)", idea_uuid
                        )
                    else:
                        logger.warning("validator_node: Idea %s not found", idea_uuid)

                await session.commit()

        except Exception as exc:
            logger.exception("validator_node failed for card idea_id=%s", idea_id_raw)
            errors.append(f"validator_node: {exc}")
            async with SessionLocal() as session:
                log = AgentLog(
                    cycle_id=cycle_id,
                    agent_name="validator_node",
                    input_state_json=card if isinstance(card, dict) else {"card": str(card)},
                    output_state_json={"error": str(exc)},
                    error_message=str(exc),
                )
                session.add(log)
                if idea_uuid is not None and cycle_id is not None:
                    row = await session.get(Idea, idea_uuid)
                    if row is not None and row.cycle_id == cycle_id:
                        row.status = "rejected"
                await session.commit()

    return {**state, "stage": "validator_completed", "errors": errors}
