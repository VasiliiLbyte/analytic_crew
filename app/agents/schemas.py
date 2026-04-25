from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class TrendCandidate(BaseModel):
    trend_name: str = Field(min_length=3, max_length=120)
    description: str = Field(min_length=10, max_length=1000)
    confidence: float = Field(ge=0.0, le=1.0)
    related_signal_ids: list[UUID] = Field(default_factory=list)
    key_drivers: list[str] = Field(default_factory=list)


class TrendSpotterOutput(BaseModel):
    trends: list[TrendCandidate] = Field(default_factory=list)


class MarketSizing(BaseModel):
    tam_estimate: str
    sam_estimate: str
    assumptions: list[str] = Field(default_factory=list)


class CompetitorInsight(BaseModel):
    category: str
    examples: list[str] = Field(default_factory=list)
    notes: str


class UnitEconomics(BaseModel):
    pricing_model: str
    acquisition_channels: list[str] = Field(default_factory=list)
    gross_margin_outlook: str
    key_cost_centers: list[str] = Field(default_factory=list)
    break_even_factors: list[str] = Field(default_factory=list)


class AnalystOutput(BaseModel):
    title: str = Field(min_length=5, max_length=200)
    problem: str = Field(min_length=10, max_length=1200)
    solution: str = Field(min_length=10, max_length=1200)
    market_sizing: MarketSizing
    competitors: list[CompetitorInsight] = Field(default_factory=list)
    unit_economics: UnitEconomics
    recommendation: str = Field(min_length=10, max_length=1200)
    top_risks: list[str] = Field(default_factory=list)
    next_validation_steps: list[str] = Field(default_factory=list)

    def as_market_analysis_json(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
