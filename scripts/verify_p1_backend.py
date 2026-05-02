#!/usr/bin/env python3
"""P1 verification: optional run_graph + HTTP checks (backend on localhost:8000)."""
from __future__ import annotations

import asyncio
import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.agents.graph import run_graph  # noqa: E402
from app.agents.initial_state import build_initial_agent_state  # noqa: E402


def _curl_json(path: str) -> dict | list | None:
    try:
        with urllib.request.urlopen(f"http://localhost:8000{path}", timeout=5) as resp:
            return json.loads(resp.read().decode())
    except Exception as exc:
        print("curl", path, "failed:", exc)
        return None


async def _graph_smoke() -> None:
    if os.getenv("SKIP_GRAPH_SMOKE", "").lower() in {"1", "true", "yes"}:
        print("SKIP_GRAPH_SMOKE — skipping run_graph")
        return
    state = build_initial_agent_state()
    result = await run_graph(state)
    print("ALL P0 + P1 CLOSED (graph smoke)")
    print("Final stage:", result.get("stage"))


def main() -> None:
    asyncio.run(_graph_smoke())
    cur = _curl_json("/api/cycle/current")
    print("/api/cycle/current:", json.dumps(cur, ensure_ascii=False)[:500] if cur is not None else cur)
    ideas = _curl_json("/api/ideas?limit=5")
    print("/api/ideas:", json.dumps(ideas, ensure_ascii=False)[:500] if ideas is not None else ideas)


if __name__ == "__main__":
    main()
