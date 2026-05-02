from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence
from uuid import UUID

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Signal
from app.services.parsers.base_parser import BaseParser, RawSignal
from app.services.parsers.habr_parser import HabrParser
from app.services.parsers.hh_parser import HHParser

logger = logging.getLogger(__name__)


class ScoutService:
    def __init__(self, parsers: Sequence[BaseParser] | None = None) -> None:
        self.parsers = list(parsers) if parsers is not None else [HHParser(), HabrParser()]

    async def collect_and_store(
        self,
        db_session: AsyncSession,
        cycle_id: UUID | None = None,
    ) -> int:
        parser_tasks = [parser.run_with_rate_limit() for parser in self.parsers]
        parser_outputs = await asyncio.gather(*parser_tasks, return_exceptions=True)

        raw_signals: list[RawSignal] = []
        for parser, output in zip(self.parsers, parser_outputs, strict=True):
            if isinstance(output, Exception):
                logger.exception("Parser failed: %s", parser.source_name, exc_info=output)
                continue
            raw_signals.extend(output)

        if not raw_signals:
            logger.info("Scout collection completed with no signals")
            return 0

        inserted = 0
        try:
            for raw_signal in raw_signals:
                row = self._to_signal_model(signal=raw_signal, cycle_id=cycle_id)
                stmt = (
                    pg_insert(Signal)
                    .values(
                        id=row.id,
                        cycle_id=row.cycle_id,
                        source_url=row.source_url,
                        source_type=row.source_type,
                        content_snippet=row.content_snippet,
                        raw_data_json=row.raw_data_json,
                        timestamp=row.timestamp,
                    )
                    .on_conflict_do_nothing(constraint="uq_signals_source_url")
                )
                result = await db_session.execute(stmt)
                if result.rowcount:
                    inserted += int(result.rowcount)

            await db_session.commit()
        except Exception:
            await db_session.rollback()
            logger.exception("Failed to persist scout signals")
            raise

        logger.info("Scout collection inserted %s new signals (attempted %s)", inserted, len(raw_signals))
        return inserted

    @staticmethod
    def _to_signal_model(signal: RawSignal, cycle_id: UUID | None) -> Signal:
        return Signal(
            cycle_id=cycle_id,
            source_url=signal.source_url,
            source_type=signal.source_type,
            content_snippet=signal.content_snippet,
            raw_data_json=signal.raw_data,
            timestamp=signal.timestamp,
        )
