#!/usr/bin/env python3
"""
Полный смок бэкенда: опционально run_graph (см. HITL / NVIDIA), затем проверка API.

Переменные:
  SKIP_GRAPH_SMOKE=1 — не вызывать run_graph (граф может зависнуть на human_review без resume).
  API_BASE=http://localhost:8000 — базовый URL FastAPI.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.agents.graph import run_graph  # noqa: E402
from app.agents.initial_state import build_initial_agent_state  # noqa: E402


def _get_json(url: str) -> object | None:
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        print("HTTP", exc.code, url, exc.read().decode()[:200])
        return None
    except Exception as exc:
        print("GET failed", url, exc)
        return None


def _check_cycle_payload(data: object) -> bool:
    if not isinstance(data, dict):
        print("cycle/current: expected dict, got", type(data))
        return False
    for key in ("id", "status", "current_phase", "progress_percent"):
        if key not in data:
            print("cycle/current: missing key", key)
            return False
    print("cycle/current OK keys:", sorted(data.keys())[:12], "...")
    return True


def _check_ideas_payload(data: object) -> bool:
    if data is None:
        print("ideas: null response")
        return False
    if not isinstance(data, list):
        print("ideas: expected list, got", type(data))
        return False
    print("ideas count:", len(data))
    return True


async def _maybe_run_graph() -> None:
    if os.getenv("SKIP_GRAPH_SMOKE", "").lower() in {"1", "true", "yes"}:
        print("SKIP_GRAPH_SMOKE — пропуск run_graph (HITL / LLM без resume)")
        return
    state = build_initial_agent_state()
    result = await run_graph(state)
    print("run_graph завершён stage=", result.get("stage"))


def main() -> None:
    base = os.getenv("API_BASE", "http://localhost:8000").rstrip("/")
    asyncio.run(_maybe_run_graph())

    cur = _get_json(f"{base}/api/cycle/current")
    ideas = _get_json(f"{base}/api/ideas?limit=10")

    ok_cycle = cur is not None and _check_cycle_payload(cur)
    ok_ideas = ideas is not None and _check_ideas_payload(ideas)

    if ok_cycle and ok_ideas:
        print("FINAL BACKEND SMOKE TEST PASSED (API cycle + ideas reachable)")
    else:
        print("FINAL BACKEND SMOKE TEST: API checks incomplete (см. вывод выше)")
        sys.exit(1)


if __name__ == "__main__":
    main()
