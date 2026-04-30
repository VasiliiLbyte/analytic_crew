from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, START, StateGraph

from app.agents.nodes.analyst_node import analyst_node
from app.agents.nodes.critic_node import critic_node
from app.agents.nodes.human_review_node import human_review_node
from app.agents.nodes.maintenance_node import maintenance_node
from app.agents.nodes.scout_node import scout_node
from app.agents.nodes.synthesizer_node import synthesizer_node
from app.agents.nodes.trend_spotter_node import trend_spotter_node
from app.agents.nodes.validator_node import validator_node
from app.agents.state import AgentState

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def checkpoint_dsn() -> str:
    """DSN for psycopg (LangGraph AsyncPostgresSaver), not asyncpg."""
    raw = os.getenv("CHECKPOINT_DATABASE_URL") or os.getenv("DATABASE_URL") or ""
    if not raw:
        msg = "DATABASE_URL or CHECKPOINT_DATABASE_URL is required for the LangGraph checkpointer"
        raise ValueError(msg)
    if raw.startswith("postgresql+asyncpg://"):
        return "postgresql://" + raw.removeprefix("postgresql+asyncpg://")
    return raw


def route_after_critic(state: AgentState) -> str:
    scored = state.get("scored_ideas") or []
    if any(x.get("verdict") == "pass" for x in scored):
        return "synthesizer_node"
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
        {"synthesizer_node": "synthesizer_node", "maintenance_node": "maintenance_node"},
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
    """Compile LangGraph with AsyncPostgresSaver; keep connection open for the whole run."""
    dsn = checkpoint_dsn()
    async with AsyncPostgresSaver.from_conn_string(dsn) as checkpointer:
        await checkpointer.setup()
        yield build_state_graph().compile(checkpointer=checkpointer)


async def run_graph(initial_state: AgentState) -> AgentState:
    """Run full pipeline with Postgres checkpointer (required for HITL / interrupt)."""
    async with build_graph() as app:
        return await app.ainvoke(initial_state)


# Deprecated: compile via `async with build_graph() as app` or `await run_graph(...)`.
graph_app = None
