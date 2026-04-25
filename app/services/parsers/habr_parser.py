from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime

import aiohttp

from app.services.parsers.base_parser import BaseParser, RawSignal

logger = logging.getLogger(__name__)

HABR_FEEDS: tuple[str, ...] = (
    "https://habr.com/ru/rss/articles/",
    "https://habr.com/ru/rss/best/daily/",
)


class HabrParser(BaseParser):
    def __init__(self, feeds: tuple[str, ...] = HABR_FEEDS) -> None:
        super().__init__(source_name="habr", source_type="rss", rate_limit_rpm=20, timeout_seconds=20)
        self.feeds = feeds

    async def fetch(self, session: aiohttp.ClientSession, **kwargs: object) -> list[RawSignal]:
        signals: list[RawSignal] = []
        for feed_url in self.feeds:
            try:
                async with session.get(feed_url, headers={"User-Agent": "analytic-crew-scout/1.0"}) as response:
                    response.raise_for_status()
                    xml_text = await response.text()
            except Exception:
                logger.exception("Failed to read Habr feed: %s", feed_url)
                continue

            signals.extend(self._parse_feed(xml_text=xml_text, feed_url=feed_url))

        logger.info("Habr parser produced %s signals", len(signals))
        return signals

    def _parse_feed(self, xml_text: str, feed_url: str) -> list[RawSignal]:
        items: list[RawSignal] = []
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            logger.exception("Failed to parse RSS XML for feed: %s", feed_url)
            return items

        for item in root.findall("./channel/item"):
            title = (item.findtext("title") or "").strip()
            description = (item.findtext("description") or "").strip()
            link = (item.findtext("link") or "").strip() or feed_url
            pub_date_raw = item.findtext("pubDate")
            pub_date = self._parse_pub_date(pub_date_raw)
            categories = [node.text.strip() for node in item.findall("category") if node.text]
            trend_tags = self._extract_trend_tags(title=title, categories=categories, description=description)

            snippet = f"{title}. {description}".strip()[:500]
            items.append(
                RawSignal(
                    source_url=link,
                    source_type=self.source_type,
                    content_snippet=snippet,
                    raw_data={
                        "feed_url": feed_url,
                        "title": title,
                        "description": description,
                        "categories": categories,
                        "trend_tags": trend_tags,
                    },
                    timestamp=pub_date,
                )
            )
        return items

    @staticmethod
    def _parse_pub_date(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _extract_trend_tags(title: str, categories: list[str], description: str) -> list[str]:
        text = " ".join([title, " ".join(categories), description])
        pattern = re.compile(
            r"\b(ai|llm|python|ml|machine learning|devops|kubernetes|cloud|architecture|security|postgresql|redis)\b",
            re.IGNORECASE,
        )
        tags = {match.group(0).lower() for match in pattern.finditer(text)}
        tags.update(category.lower() for category in categories if category)
        return sorted(tags)
