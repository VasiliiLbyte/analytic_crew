from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.schemas import IdeaCard, SynthesizerOutput
from app.agents.state import AgentState
from app.core.config import build_llm_client, get_settings
from app.core.database import SessionLocal
from app.models.base import AgentLog, Idea

logger = logging.getLogger(__name__)
PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "synthesizer.txt"


def _draft_for_scored_idea(
    drafts: list[dict[str, Any]], scored_title: str | None
) -> dict[str, Any] | None:
    st = (scored_title or "").strip().lower()
    if not st:
        return None
    for d in drafts:
        if (d.get("title") or "").strip().lower() == st:
            return d
    for d in drafts:
        dt = (d.get("title") or "").strip().lower()
        if st in dt or dt in st:
            return d
    return None


def _critic_comment_snippet(scored: dict[str, Any]) -> str | None:
    parts: list[str] = []
    for key in ("improvement_suggestions", "fact_check_notes", "red_team_attacks"):
        val = scored.get(key)
        if isinstance(val, list) and val:
            parts.extend(str(x) for x in val[:3])
        elif isinstance(val, str) and val:
            parts.append(val)
    if not parts:
        return None
    text = " | ".join(parts)
    return text[:4000]


async def synthesizer_node(state: AgentState) -> AgentState:
    scored_ideas = state.get("scored_ideas", [])
    passed = [i for i in scored_ideas if i.get("verdict") == "pass"]
    if not passed:
        logger.warning("Synthesizer skipped: no passed ideas")
        return {**state, "stage": "synthesizer_completed", "validated_cards": []}

    cycle_id = state.get("cycle_id")
    if cycle_id is None:
        logger.error("Synthesizer skipped: missing cycle_id")
        return {**state, "stage": "synthesizer_completed", "validated_cards": [], "errors": state.get("errors", []) + ["synthesizer: no cycle_id"]}

    drafts = state.get("analysis_drafts", [])
    settings = get_settings()
    rate_limiter = settings.get_rate_limiter()
    cache = await settings.get_llm_cache()
    llm = (await build_llm_client()).with_structured_output(SynthesizerOutput)

    validated_cards: list[dict[str, Any]] = []

    for idea in passed[:5]:
        prompt_text = PROMPT_PATH.read_text(encoding="utf-8")
        user_payload = json.dumps(idea, ensure_ascii=False)
        cache_key = prompt_text + user_payload
        cached = await cache.get(cache_key)
        if cached:
            output = SynthesizerOutput.model_validate(cached)
        else:
            await rate_limiter.wait_for_token()
            result = await llm.ainvoke([("system", prompt_text), ("user", user_payload)])
            output = SynthesizerOutput.model_validate(result)
            await cache.set(cache_key, output.model_dump(mode="json"))

        draft = _draft_for_scored_idea(drafts, idea.get("idea_title"))
        market_json = (draft or {}).get("market_analysis_json")

        async with SessionLocal() as session:
            log = AgentLog(
                cycle_id=cycle_id,
                agent_name="synthesizer_node",
                input_state_json=idea,
                output_state_json=output.model_dump(mode="json"),
            )
            session.add(log)

            for card in output.cards:
                card_dict = _persist_idea_from_card(
                    session=session,
                    cycle_id=cycle_id,
                    card=card,
                    scored_idea=idea,
                    market_analysis_json=market_json if isinstance(market_json, (dict, list)) else None,
                )
                validated_cards.append(card_dict)

            await session.commit()

    new_state = {
        **state,
        "validated_cards": validated_cards,
        "stage": "synthesizer_completed",
    }
    logger.info("Synthesizer created %s cards with DB rows", len(validated_cards))
    return new_state


def _persist_idea_from_card(
    session: AsyncSession,
    cycle_id: UUID,
    card: IdeaCard,
    scored_idea: dict[str, Any],
    market_analysis_json: dict[str, Any] | list[Any] | None,
) -> dict[str, Any]:
    gtm_plan: dict[str, Any] = {
        "mvp_path": card.mvp_path,
        "gtm_scenarios": card.gtm_scenarios,
        "monetization_models": card.monetization_models,
        "budget_to_1m_rub_per_month": card.budget_to_1m_rub_per_month,
        "team_size_needed": card.team_size_needed,
        "target_audience": card.target_audience,
        "cross_niche_potential": card.cross_niche_potential,
    }
    sources_val: list[str] = list(card.sources_used)
    critic_score = scored_idea.get("total_score")
    score_f = float(critic_score) if critic_score is not None else None

    row = Idea(
        cycle_id=cycle_id,
        title=card.title,
        problem=card.problem_statement,
        solution=card.proposed_solution,
        market_analysis_json=market_analysis_json,
        critic_score=score_f,
        critic_comment=_critic_comment_snippet(scored_idea),
        gtm_plan_json=gtm_plan,
        sources_json=sources_val,
        status="draft",
    )
    session.add(row)
    session.flush()

    out = card.model_dump(mode="json")
    out["idea_id"] = str(row.id)
    return out
