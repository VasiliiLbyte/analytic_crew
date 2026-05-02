#!/usr/bin/env python3
"""Smoke: run_graph with build_initial_agent_state (needs DB + NVIDIA_API_KEY for full run)."""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.agents.graph import run_graph  # noqa: E402
from app.agents.initial_state import build_initial_agent_state  # noqa: E402


async def test() -> None:
    if os.getenv("SKIP_GRAPH_SMOKE", "").lower() in {"1", "true", "yes"}:
        print("SKIP_GRAPH_SMOKE set — skipping run_graph")
        return
    state = build_initial_agent_state()
    result = await run_graph(state)
    print("ALL P0 + P1 graph smoke OK")
    print("Final stage:", result.get("stage"))


if __name__ == "__main__":
    asyncio.run(test())
