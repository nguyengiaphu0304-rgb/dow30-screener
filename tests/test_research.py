import json
from datetime import date
from pathlib import Path

import pytest

from dow30_screener import DataQualityError, Membership, SignalObservation, evaluate_week


def test_fixture_excludes_future_and_expired_constituents() -> None:
    payload = json.loads((Path(__file__).parent / "fixtures/research_case.json").read_text())
    observed_on = date.fromisoformat(payload["observed_on"])
    memberships = [
        Membership(
            item["ticker"],
            date.fromisoformat(item["valid_from"]),
            date.fromisoformat(item["valid_to"]) if item["valid_to"] else None,
        )
        for item in payload["memberships"]
    ]
    signals = [
        SignalObservation(item["ticker"], observed_on, item["score"], item["forward_return"])
        for item in payload["signals"]
    ]
    result = evaluate_week(
        signals,
        memberships,
        benchmark_return=payload["benchmark_return"],
        transaction_cost_bps=payload["transaction_cost_bps"],
    )
    assert result is not None
    assert result.picks == ("AAA",)
    assert result.gross_return == pytest.approx(0.04)
    assert result.net_return == pytest.approx(0.038)
    assert result.excess_return == pytest.approx(0.028)


def test_ranking_is_deterministic_and_does_not_use_forward_return() -> None:
    day = date(2026, 1, 1)
    rows = [SignalObservation("BBB", day, 1, 0.9), SignalObservation("AAA", day, 1, -0.9)]
    memberships = [Membership("AAA", day), Membership("BBB", day)]
    result = evaluate_week(rows, memberships, benchmark_return=0, top_k=1)
    assert result is not None and result.picks == ("AAA",)


def test_requires_benchmark_and_allows_costs_to_exceed_return() -> None:
    day = date(2026, 1, 1)
    rows = [SignalObservation("AAA", day, 1, 0.001)]
    memberships = [Membership("AAA", day)]
    with pytest.raises(DataQualityError, match="benchmark"):
        evaluate_week(rows, memberships, benchmark_return=float("nan"))
    result = evaluate_week(rows, memberships, benchmark_return=0, transaction_cost_bps=20)
    assert result is not None and result.net_return < 0


def test_no_eligible_constituents_returns_none() -> None:
    day = date(2026, 1, 1)
    assert (
        evaluate_week(
            [SignalObservation("AAA", day, 1, 1)],
            [Membership("AAA", date(2026, 2, 1))],
            benchmark_return=0,
        )
        is None
    )
