from __future__ import annotations

from typing import Any, Dict, List, Literal
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


class ScoredIdea(BaseModel):
    idea_title: str
    scores: dict[str, float]
    total_score: float
    verdict: Literal['pass', 'fail', 'borderline']
    red_team_attacks: list[str]
    counterarguments: list[str]
    fact_check_notes: list[str]
    improvement_suggestions: list[str]


class CriticOutput(BaseModel):
    scored_ideas: list[ScoredIdea]


class IdeaCard(BaseModel):
    title: str
    problem_statement: str
    proposed_solution: str
    target_audience: str
    mvp_path: List[str]
    team_size_needed: int
    budget_to_1m_rub_per_month: str
    gtm_scenarios: List[Dict[str, Any]]
    cross_niche_potential: str
    monetization_models: List[str]
    sources_used: List[str]


class SynthesizerOutput(BaseModel):
    cards: List[IdeaCard]


class ValidatorOutput(BaseModel):
    validated_cards: List[Dict[str, Any]]  # будет расширяться в validator_node
