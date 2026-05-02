from __future__ import annotations

from uuid import uuid4

from app.agents.state import AgentState


def build_initial_agent_state() -> AgentState:
    """Единая фабрика начального state для main_flow и API /cycle/start."""
    return {
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
        "analyst_retry_count": 0,
    }
