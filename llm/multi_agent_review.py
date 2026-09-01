"""Structured multi-agent review of deterministic scanner evidence.

LLMs critique and synthesize existing evidence; they do not calculate prices,
probabilities, or trading instructions. The module imports the optional Agents
SDK only when a review is requested.
"""

from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass, field
import json
import math
import os
from typing import Any


@dataclass
class SpecialistReview:
    agent: str
    stance: str
    confidence: int
    evidence: list[str] = field(default_factory=list)
    contradictions: list[str] = field(default_factory=list)
    missing_data: list[str] = field(default_factory=list)


@dataclass
class FinalReview:
    ticker: str
    stance: str
    confidence: int
    thesis: str
    bull_case: str
    bear_case: str
    forecast_interpretation: str
    invalidation_conditions: list[str] = field(default_factory=list)
    disagreements: list[str] = field(default_factory=list)
    data_limitations: list[str] = field(default_factory=list)
    disclaimer: str = "Research summary only; not personalized investment advice or a guaranteed forecast."


def is_available() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


def _clean(value: Any, depth: int = 0) -> Any:
    if depth > 5:
        return None
    if isinstance(value, dict):
        return {str(k): _clean(v, depth + 1) for k, v in list(value.items())[:80]}
    if isinstance(value, (list, tuple)):
        return [_clean(v, depth + 1) for v in value[:50]]
    if isinstance(value, (str, bool, int)) or value is None:
        return value
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return str(value)[:500]


def build_review_context(ticker: str, details: dict) -> dict:
    """Create a bounded, auditable evidence packet for all reviewers."""
    scores = details.get("scores", {}) or {}
    return _clean(
        {
            "ticker": ticker,
            "asset_type": details.get("asset_type", "equity"),
            "index_memberships": details.get("index_memberships", []),
            "as_of": details.get("as_of"),
            "price_features": details.get("price_features", {}),
            "technical": details.get("technical", {}),
            "fundamentals": details.get("fundamentals", {}),
            "fundamental_screen": details.get("fundamental_results", {}),
            "options": details.get("options_data", {}),
            "patterns": details.get("patterns", {}),
            "sentiment": details.get("sentiment", {}),
            "causal_analysis": details.get("causal_results", {}),
            "bayesian_analysis": details.get("bayesian_results", {}),
            "forecast_scenarios": details.get("forecast", {}),
            "multi_factor_scores": {
                "bull_score": scores.get("bull_score"),
                "bear_score": scores.get("bear_score"),
                "confidence": scores.get("confidence"),
                "category_scores": scores.get("category_scores", {}),
                "lookalike_stats": scores.get("lookalike_stats", {}),
                "win_rate_stats": scores.get("win_rate_stats", {}),
            },
            "risk_analysis": scores.get("risk_analysis", {}),
        }
    )


SPECIALISTS = {
    "Technical reviewer": "Audit trend, momentum, patterns, regime analogs, and scenario consistency.",
    "Fundamental reviewer": "Audit quality, valuation, growth, causal and sentiment evidence; flag stale or missing data.",
    "Options reviewer": "Audit options positioning, implied-volatility evidence, liquidity, and whether flow is ambiguous.",
    "Risk skeptic": "Challenge every bullish claim using drawdown, tail loss, beta, liquidity, model uncertainty, and contradictions.",
}


async def review_stock(ticker: str, details: dict, model: str | None = None) -> dict:
    """Run independent specialists in parallel and synthesize their disagreement."""
    if not is_available():
        return {"available": False, "error": "OPENAI_API_KEY is not configured."}
    try:
        from agents import Agent, Runner
    except ImportError:
        return {"available": False, "error": "Install the openai-agents package to enable LLM review."}

    chosen_model = model or os.getenv("OPENAI_REVIEW_MODEL", "gpt-5.6-sol")
    packet = build_review_context(ticker, details)
    packet_json = json.dumps(packet, separators=(",", ":"), sort_keys=True)
    shared = (
        "Use only the supplied JSON evidence. Never invent current events, prices, probabilities, or missing facts. "
        "Treat model outputs as estimates, explicitly identify contradictions, and return insufficient evidence when warranted. "
        "Confidence is 0-100 epistemic confidence in the written assessment, not probability of a price move."
    )

    async def run_specialist(name: str, mandate: str) -> SpecialistReview:
        agent = Agent(
            name=name,
            model=chosen_model,
            instructions=f"{shared} {mandate}",
            output_type=SpecialistReview,
        )
        result = await Runner.run(agent, f"Review this evidence packet:\n{packet_json}", max_turns=2)
        return result.final_output

    specialist_outputs = await asyncio.gather(
        *(run_specialist(name, mandate) for name, mandate in SPECIALISTS.items())
    )
    reviews_json = json.dumps([asdict(review) for review in specialist_outputs], separators=(",", ":"))
    arbiter = Agent(
        name="Critical investment-research arbiter",
        model=chosen_model,
        instructions=(
            f"{shared} Reconcile the independent reviews without majority voting. Preserve disagreements. "
            "Interpret only the deterministic forecast scenarios supplied; do not create new price targets. "
            "A high-risk or contradictory case must not receive high confidence without explicit justification."
        ),
        output_type=FinalReview,
    )
    final = await Runner.run(
        arbiter,
        f"Ticker: {ticker}\nEvidence: {packet_json}\nIndependent reviews: {reviews_json}",
        max_turns=2,
    )
    return {
        "available": True,
        "model": chosen_model,
        "specialists": [asdict(review) for review in specialist_outputs],
        "final": asdict(final.final_output),
    }


def review_stock_sync(ticker: str, details: dict, model: str | None = None) -> dict:
    return asyncio.run(review_stock(ticker, details, model))
