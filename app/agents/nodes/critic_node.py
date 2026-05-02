from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.agents.schemas import CriticOutput
from app.agents.scoring import calculate_total_score, PASS_THRESHOLD
from app.agents.state import AgentState
from app.core.config import build_llm_client, get_settings
from app.core.database import SessionLocal
from app.models.base import AgentLog

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "critic.txt"


async def critic_node(state: AgentState) -> AgentState:
    analysis_drafts = state.get("analysis_drafts", [])
    if not analysis_drafts:
        logger.warning("Critic node skipped: no analysis_drafts")
        return {
            **state,
            "stage": "critic_completed",
            "scored_ideas": [],
            "analyst_retry_count": int(state.get("analyst_retry_count", 0)),
        }

    scored_ideas: list[dict[str, Any]] = []
    settings = get_settings()
    rate_limiter = settings.get_rate_limiter()
    cache = await settings.get_llm_cache()
    llm = (await build_llm_client()).with_structured_output(CriticOutput)

    for draft in analysis_drafts:
        prompt_text = PROMPT_PATH.read_text(encoding="utf-8")
        user_payload = json.dumps({"draft": draft}, ensure_ascii=False)
        cache_key = prompt_text + user_payload

        try:
            cached = await cache.get(cache_key)
            if cached:
                critic_output = CriticOutput.model_validate(cached)
            else:
                await rate_limiter.wait_for_token()
                llm_result = await llm.ainvoke([("system", prompt_text), ("user", user_payload)])
                critic_output = CriticOutput.model_validate(llm_result)
                await cache.set(cache_key, critic_output.model_dump(mode="json"))

            for scored in critic_output.scored_ideas:
                scored_dict = scored.model_dump(mode="json")
                scored_dict["total_score"] = calculate_total_score(scored_dict["scores"])
                scored_dict["verdict"] = "pass" if scored_dict["total_score"] >= PASS_THRESHOLD else "fail"
                scored_ideas.append(scored_dict)

                # Логируем в agent_logs
                async with SessionLocal() as session:
                    log = AgentLog(
                        cycle_id=state.get("cycle_id"),
                        agent_name="critic_node",
                        input_state_json=draft,
                        output_state_json=scored_dict,
                    )
                    session.add(log)
                    await session.commit()

        except Exception as e:
            logger.error(f"Critic LLM error: {e}")
            state.setdefault("errors", []).append(str(e))

    has_pass = any(x.get("verdict") == "pass" for x in scored_ideas)
    prev_streak = int(state.get("analyst_retry_count", 0))
    # Подряд исходов critic без pass; для route_after_critic: при streak < 3 ещё можно вернуться к analyst.
    streak = 0 if has_pass else prev_streak + 1

    new_state = {
        **state,
        "scored_ideas": scored_ideas,
        "stage": "critic_completed",
        "analyst_retry_count": streak,
    }
    logger.info("Critic node processed %s ideas (has_pass=%s)", len(scored_ideas), has_pass)
    return new_state
