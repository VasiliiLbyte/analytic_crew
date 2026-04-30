from __future__ import annotations

SCORING_WEIGHTS = {
    'market_potential': 0.15,
    'competition_freedom': 0.15,
    'mvp_speed': 0.10,
    'revenue_speed': 0.15,
    'unit_economics': 0.10,
    'regulatory_risk': 0.05,
    'scalability': 0.10,
    'validation_speed': 0.10,
    'defensibility': 0.05,
}

PASS_THRESHOLD = 75.0


def calculate_total_score(scores: dict[str, float]) -> float:
    """Расчёт итогового взвешенного скора по 10 критериям."""
    if not scores:
        return 0.0
    total = sum(scores.get(k, 0.0) * v for k, v in SCORING_WEIGHTS.items())
    return round(total * 100, 2)
