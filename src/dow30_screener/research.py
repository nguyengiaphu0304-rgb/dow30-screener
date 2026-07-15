"""Small, auditable research calculations without network access."""

from dataclasses import dataclass
from datetime import date
from math import isfinite

from .quality import DataQualityError, Membership, eligible_tickers


@dataclass(frozen=True, slots=True)
class SignalObservation:
    ticker: str
    observed_on: date
    score: float
    forward_return: float


@dataclass(frozen=True, slots=True)
class WeeklyResult:
    observed_on: date
    picks: tuple[str, ...]
    gross_return: float
    transaction_cost: float
    net_return: float
    benchmark_return: float
    excess_return: float


def evaluate_week(
    signals: list[SignalObservation],
    memberships: list[Membership],
    *,
    benchmark_return: float,
    top_k: int = 5,
    transaction_cost_bps: float = 0,
) -> WeeklyResult | None:
    if not signals:
        return None
    if top_k <= 0:
        raise DataQualityError("top_k must be positive")
    if not isfinite(transaction_cost_bps) or transaction_cost_bps < 0:
        raise DataQualityError("transaction_cost_bps must be finite and non-negative")
    if not isfinite(benchmark_return):
        raise DataQualityError("benchmark return is required and must be finite")
    observed_on = signals[0].observed_on
    if any(signal.observed_on != observed_on for signal in signals):
        raise DataQualityError("signals must share one observation date")
    if len({signal.ticker for signal in signals}) != len(signals):
        raise DataQualityError("duplicate signal ticker")
    if any(not isfinite(signal.score) or not isfinite(signal.forward_return) for signal in signals):
        raise DataQualityError("signal values must be finite")
    eligible = set(eligible_tickers(memberships, observed_on))
    candidates = [signal for signal in signals if signal.ticker in eligible]
    if not candidates:
        return None
    selected = sorted(candidates, key=lambda signal: (-signal.score, signal.ticker))[:top_k]
    gross = sum(signal.forward_return for signal in selected) / len(selected)
    cost = transaction_cost_bps / 10_000
    net = gross - cost
    return WeeklyResult(
        observed_on=observed_on,
        picks=tuple(signal.ticker for signal in selected),
        gross_return=gross,
        transaction_cost=cost,
        net_return=net,
        benchmark_return=benchmark_return,
        excess_return=net - benchmark_return,
    )
