import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import aiohttp
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RawSignal(BaseModel):
    source_url: str
    source_type: str
    content_snippet: str
    raw_data: Dict[str, Any]
    timestamp: Optional[str] = None

class BaseParser(ABC):
    """
    Base class for all data ingestion parsers.
    Implements rate limiting and common error handling.
    """
    def __init__(self, source_name: str, rate_limit_rpm: int = 40):
        self.source_name = source_name
        self.rate_limit_rpm = rate_limit_rpm
        self._delay = 60.0 / rate_limit_rpm

    @abstractmethod
    async def fetch(self, session: aiohttp.ClientSession, **kwargs) -> List[RawSignal]:
        """Fetch data from the source."""
        pass

    async def run_with_rate_limit(self, **kwargs) -> List[RawSignal]:
        """Execute fetch with rate limiting."""
        async with aiohttp.ClientSession() as session:
            logger.info(f"Starting fetch for {self.source_name}")
            try:
                result = await self.fetch(session, **kwargs)
                await asyncio.sleep(self._delay)  # Basic rate limit enforcement
                return result
            except Exception as e:
                logger.error(f"Error fetching from {self.source_name}: {e}")
                return []

# Example Implementation for RSS
class RSSParser(BaseParser):
    async def fetch(self, session: aiohttp.ClientSession, url: str) -> List[RawSignal]:
        async with session.get(url) as response:
            if response.status == 200:
                # In a real scenario, use feedparser or similar
                text = await response.text()
                logger.info(f"Fetched RSS content from {url}")
                return [RawSignal(
                    source_url=url,
                    source_type="rss",
                    content_snippet=text[:500],
                    raw_data={"full_text": text}
                )]
            return []

# Requirements file content
"""
fastapi
uvicorn
sqlalchemy[asyncio]
asyncpg
pydantic-settings
langgraph
langchain-openai
aiohttp
redis
python-dotenv
alembic
psycopg2-binary
"""
