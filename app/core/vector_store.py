from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ChromaStore:
    """
    Минимальная заглушка под Chroma (контекст v2.0 §3.3).

    Дальше: HTTP-клиент к CHROMA_URL, коллекция (например rejected_ideas),
    эмбеддинг title+problem, upsert с metadata {cycle_id, idea_id, status}.
    Сейчас только контракт для maintenance_node и логирование.
    """

    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = (base_url or "http://localhost:8000").rstrip("/")

    async def upsert_rejected_idea(self, payload: dict[str, Any]) -> None:
        """Позже: реальный upsert в Chroma; сейчас без сетевых вызовов."""
        logger.info(
            "ChromaStore.upsert_rejected_idea (stub) base_url=%s payload_keys=%s",
            self.base_url,
            sorted(payload.keys()),
        )

    async def close(self) -> None:
        """Позже: закрыть aiohttp/httpx клиент."""
        return None
