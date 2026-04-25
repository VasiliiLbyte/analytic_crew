from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any

import aiohttp

from app.services.parsers.base_parser import BaseParser, RawSignal

logger = logging.getLogger(__name__)

HH_VACANCIES_URL = "https://api.hh.ru/vacancies"
DEFAULT_KEYWORDS = ("AI", "LLM", "Python")


class HHParser(BaseParser):
    def __init__(
        self,
        keywords: tuple[str, ...] = DEFAULT_KEYWORDS,
        pages_per_keyword: int = 1,
        per_page: int = 20,
    ) -> None:
        super().__init__(source_name="headhunter", source_type="api", rate_limit_rpm=30, timeout_seconds=20)
        self.keywords = keywords
        self.pages_per_keyword = max(1, pages_per_keyword)
        self.per_page = max(1, min(per_page, 100))

    async def fetch(self, session: aiohttp.ClientSession, **kwargs: Any) -> list[RawSignal]:
        results: list[RawSignal] = []
        for keyword in self.keywords:
            for page in range(self.pages_per_keyword):
                payload = await self.get_json(
                    session=session,
                    url=HH_VACANCIES_URL,
                    params={
                        "text": keyword,
                        "per_page": self.per_page,
                        "page": page,
                    },
                    headers={"User-Agent": "analytic-crew-scout/1.0"},
                )
                items = payload.get("items", [])
                for item in items:
                    signal = await self._build_signal(session=session, vacancy=item, query=keyword)
                    if signal is not None:
                        results.append(signal)
        logger.info("HH parser produced %s signals", len(results))
        return results

    async def _build_signal(
        self,
        session: aiohttp.ClientSession,
        vacancy: dict[str, Any],
        query: str,
    ) -> RawSignal | None:
        vacancy_id = vacancy.get("id")
        if not vacancy_id:
            return None

        detail_url = f"{HH_VACANCIES_URL}/{vacancy_id}"
        try:
            details = await self.get_json(
                session=session,
                url=detail_url,
                headers={"User-Agent": "analytic-crew-scout/1.0"},
            )
        except Exception:
            logger.exception("Failed to fetch vacancy details for %s", vacancy_id)
            details = vacancy

        key_skills = details.get("key_skills") or []
        skill_names = [skill.get("name", "").strip() for skill in key_skills if skill.get("name")]
        if not skill_names:
            skill_names = self._extract_skills_from_text(
                " ".join(
                    filter(
                        None,
                        [
                            details.get("name"),
                            (details.get("snippet") or {}).get("requirement"),
                            (details.get("snippet") or {}).get("responsibility"),
                        ],
                    )
                )
            )

        published_at = self._parse_hh_datetime(details.get("published_at"))
        snippet = (details.get("snippet") or {}).get("requirement") or details.get("name") or ""

        return RawSignal(
            source_url=details.get("alternate_url"),
            source_type=self.source_type,
            content_snippet=snippet[:500],
            raw_data={
                "query": query,
                "vacancy_id": vacancy_id,
                "title": details.get("name"),
                "company": (details.get("employer") or {}).get("name"),
                "area": (details.get("area") or {}).get("name"),
                "skills": skill_names,
                "salary": details.get("salary"),
            },
            timestamp=published_at,
        )

    @staticmethod
    def _parse_hh_datetime(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None

    @staticmethod
    def _extract_skills_from_text(text: str) -> list[str]:
        skill_pattern = re.compile(
            r"\b(Python|SQL|FastAPI|Django|Flask|PyTorch|TensorFlow|NLP|LLM|LangChain|Docker|Kubernetes|PostgreSQL|Redis)\b",
            re.IGNORECASE,
        )
        found = {match.group(0).strip() for match in skill_pattern.finditer(text or "")}
        return sorted(found, key=str.lower)
