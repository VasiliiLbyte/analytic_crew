from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.agents.nodes.analyst_node import analyst_node
from app.agents.nodes.scout_node import scout_node
from app.agents.nodes.trend_spotter_node import trend_spotter_node
from app.agents.state import AgentState


def build_graph():
    graph_builder = StateGraph(AgentState)
    graph_builder.add_node("scout_node", scout_node)
    graph_builder.add_node("trend_spotter_node", trend_spotter_node)
    graph_builder.add_node("analyst_node", analyst_node)
    graph_builder.add_edge(START, "scout_node")
    graph_builder.add_edge("scout_node", "trend_spotter_node")
    graph_builder.add_edge("trend_spotter_node", "analyst_node")
    graph_builder.add_edge("analyst_node", END)
    return graph_builder.compile()


graph_app = build_graph()


async def run_graph(initial_state: AgentState) -> AgentState:
    result = await graph_app.ainvoke(initial_state)
    return result
