from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, START, StateGraph
from psycopg import OperationalError

from app.agents.nodes.analyst_node import analyst_node
from app.agents.nodes.critic_node import critic_node
from app.agents.nodes.human_review_node import human_review_node
from app.agents.nodes.maintenance_node import maintenance_node
from app.agents.nodes.scout_node import scout_node
from app.agents.nodes.synthesizer_node import synthesizer_node
from app.agents.nodes.trend_spotter_node import trend_spotter_node
from app.agents.nodes.validator_node import validator_node
from app.agents.state import AgentState
from app.core.config import get_settings

# Максимум 2 возврата к analyst после critic без pass (streak 1..2 → analyst, 3 → maintenance).
MAX_CRITIC_TO_ANALYST_RETRIES = 2


def route_after_critic(state: AgentState) -> str:
    scored = state.get("scored_ideas") or []
    if not scored:
        return "maintenance_node"
    if any(x.get("verdict") == "pass" for x in scored):
        return "synthesizer_node"
    streak = int(state.get("analyst_retry_count", 0))
    if streak <= MAX_CRITIC_TO_ANALYST_RETRIES:
        return "analyst_node"
    return "maintenance_node"


def route_after_human_review(state: AgentState) -> str:
    target = (state.get("target_agent") or "").lower()
    action = (state.get("human_decision") or "").lower()
    if target == "analyst" or action in ("revise_analyst", "back_to_analyst"):
        return "analyst_node"
    if target == "critic" or action in ("revise_critic", "back_to_critic"):
        return "critic_node"
    if target == "synthesizer" or action in ("revise_synthesizer", "back_to_synthesizer"):
        return "synthesizer_node"
    return "maintenance_node"


def build_state_graph() -> StateGraph:
    graph_builder = StateGraph(AgentState)
    graph_builder.add_node("scout_node", scout_node)
    graph_builder.add_node("trend_spotter_node", trend_spotter_node)
    graph_builder.add_node("analyst_node", analyst_node)
    graph_builder.add_node("critic_node", critic_node)
    graph_builder.add_node("synthesizer_node", synthesizer_node)
    graph_builder.add_node("validator_node", validator_node)
    graph_builder.add_node("human_review_node", human_review_node)
    graph_builder.add_node("maintenance_node", maintenance_node)

    graph_builder.add_edge(START, "scout_node")
    graph_builder.add_edge("scout_node", "trend_spotter_node")
    graph_builder.add_edge("trend_spotter_node", "analyst_node")
    graph_builder.add_edge("analyst_node", "critic_node")
    graph_builder.add_conditional_edges(
        "critic_node",
        route_after_critic,
        {
            "synthesizer_node": "synthesizer_node",
            "analyst_node": "analyst_node",
            "maintenance_node": "maintenance_node",
        },
    )
    graph_builder.add_edge("synthesizer_node", "validator_node")
    graph_builder.add_edge("validator_node", "human_review_node")
    graph_builder.add_conditional_edges(
        "human_review_node",
        route_after_human_review,
        {
            "analyst_node": "analyst_node",
            "critic_node": "critic_node",
            "synthesizer_node": "synthesizer_node",
            "maintenance_node": "maintenance_node",
        },
    )
    graph_builder.add_edge("maintenance_node", END)
    return graph_builder


@asynccontextmanager
async def build_graph() -> AsyncIterator[Any]:
    """Compile graph with AsyncPostgresSaver and HITL interrupt point."""
    settings = get_settings()
    primary_dsn = settings.database_url.replace("+asyncpg", "")
    candidates = [primary_dsn]
    if "localhost:55432" in primary_dsn:
        candidates.append(primary_dsn.replace("localhost:55432", "localhost:5432"))
    if "127.0.0.1:55432" in primary_dsn:
        candidates.append(primary_dsn.replace("127.0.0.1:55432", "127.0.0.1:5432"))

    last_error: Exception | None = None
    for dsn in candidates:
        try:
            async with AsyncPostgresSaver.from_conn_string(dsn) as checkpointer:
                await checkpointer.setup()
                yield build_state_graph().compile(
                    checkpointer=checkpointer,
                    interrupt_before=["human_review_node"],
                )
                return
        except OperationalError as exc:
            last_error = exc

    if last_error:
        # Local fallback for environments where host Postgres points to a different instance.
        yield build_state_graph().compile(
            checkpointer=InMemorySaver(),
            interrupt_before=["human_review_node"],
        )
        return

    raise RuntimeError("Unable to initialize graph checkpointer")


async def run_graph(initial_state: AgentState) -> AgentState:
    """Run full pipeline with Postgres checkpointer (required for HITL / interrupt)."""
    settings = get_settings()
    # Pre-initialize shared infra used by nodes.
    _ = settings.get_rate_limiter()
    _ = await settings.get_llm_cache()
    thread_id = str(initial_state.get("cycle_id") or "default-thread")
    config = {"configurable": {"thread_id": thread_id}}
    async with build_graph() as app:
        return await app.ainvoke(initial_state, config=config)


# Deprecated: compile via `async with build_graph() as app` or `await run_graph(...)`.
graph_app = None
