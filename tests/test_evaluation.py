from dataclasses import replace
from datetime import date, timedelta

import pytest

from dow30_screener import (
    CorporateActionPolicy,
    DataQualityError,
    DataQualityReport,
    EvaluationPeriod,
    Membership,
    SignalObservation,
    WalkForwardFold,
    bootstrap_mean_interval,
    build_walk_forward_report,
    expanding_window_folds,
)


def _period(day: date, winner: str = "AAA", *, benchmark: float = 0.005) -> EvaluationPeriod:
    returns = {"AAA": 0.03, "BBB": 0.01, "CCC": -0.01}
    scores = {"AAA": 3.0, "BBB": 2.0, "CCC": 1.0}
    if winner == "CCC":
        returns["AAA"], returns["CCC"] = returns["CCC"], returns["AAA"]
    return EvaluationPeriod(
        day,
        tuple(SignalObservation(ticker, day, scores[ticker], returns[ticker]) for ticker in scores),
        benchmark,
    )


def _inputs() -> tuple[
    tuple[EvaluationPeriod, ...], list[Membership], DataQualityReport, tuple[WalkForwardFold, ...]
]:
    start = date(2025, 1, 3)
    periods = tuple(_period(start + timedelta(days=7 * index)) for index in range(6))
    memberships = [Membership(ticker, start) for ticker in ("AAA", "BBB", "CCC")]
    report = DataQualityReport(
        fixture_id="synthetic-walk-forward-v1",
        price_rows=24,
        membership_rows=3,
        ticker_count=4,
        first_date=start,
        last_date=periods[-1].observed_on,
        benchmark="SPY",
        currency="USD",
        exchange_calendar="synthetic-weekly",
        corporate_action_policy=CorporateActionPolicy.TOTAL_RETURN_ADJUSTED,
        prices_sha256="a" * 64,
        memberships_sha256="b" * 64,
    )
    folds = expanding_window_folds(
        tuple(period.observed_on for period in periods), minimum_train_periods=2, test_periods=2
    )
    return periods, memberships, report, folds


def test_expanding_folds_are_ordered_and_non_overlapping() -> None:
    periods, _, _, folds = _inputs()
    assert len(folds) == 2
    assert folds[0].train_dates == tuple(period.observed_on for period in periods[:2])
    assert folds[0].test_dates == tuple(period.observed_on for period in periods[2:4])
    assert folds[1].train_dates == tuple(period.observed_on for period in periods[:4])
    assert folds[1].test_dates == tuple(period.observed_on for period in periods[4:])


@pytest.mark.parametrize("train,test", [(0, 1), (1, 0)])
def test_fold_counts_must_be_positive(train: int, test: int) -> None:
    with pytest.raises(DataQualityError, match="positive"):
        expanding_window_folds((date(2025, 1, 1),), minimum_train_periods=train, test_periods=test)


def test_too_few_periods_fail_closed() -> None:
    with pytest.raises(DataQualityError, match="not enough"):
        expanding_window_folds(
            (date(2025, 1, 1), date(2025, 1, 8)),
            minimum_train_periods=2,
            test_periods=1,
        )


def test_report_is_deterministic_and_binds_verified_lineage() -> None:
    periods, memberships, quality, folds = _inputs()
    kwargs = {
        "candidate_top_k": (1, 2, 3),
        "transaction_cost_scenarios_bps": (0.0, 20.0),
        "bootstrap_samples": 100,
        "seed": 7,
    }
    first = build_walk_forward_report(periods, memberships, quality, folds, **kwargs)
    second = build_walk_forward_report(periods, memberships, quality, folds, **kwargs)
    assert first.to_json() == second.to_json()
    assert first.fixture_id == quality.fixture_id
    assert first.prices_sha256 == "a" * 64
    assert [scenario.transaction_cost_bps for scenario in first.scenarios] == [0, 20]
    assert all(
        period.selected_top_k == 1 for scenario in first.scenarios for period in scenario.periods
    )
    assert first.scenarios[1].mean_strategy_return < first.scenarios[0].mean_strategy_return
    assert "not financial advice" in first.limitations[-1]


def test_parameter_selection_never_uses_future_test_outcome() -> None:
    periods, memberships, quality, folds = _inputs()
    changed = periods[:2] + tuple(
        _period(period.observed_on, winner="CCC") for period in periods[2:]
    )
    report = build_walk_forward_report(
        changed,
        memberships,
        quality,
        folds[:1],
        candidate_top_k=(1, 3),
        transaction_cost_scenarios_bps=(0.0,),
        bootstrap_samples=20,
    )
    assert all(period.selected_top_k == 1 for period in report.scenarios[0].periods)
    assert report.scenarios[0].mean_excess_return < 0


def test_equal_weight_baseline_and_costs_are_explicit() -> None:
    periods, memberships, quality, folds = _inputs()
    report = build_walk_forward_report(
        periods,
        memberships,
        quality,
        folds[:1],
        candidate_top_k=(1,),
        transaction_cost_scenarios_bps=(400.0,),
        bootstrap_samples=20,
    )
    period = report.scenarios[0].periods[0]
    assert period.strategy_net_return < 0
    assert period.equal_weight_net_return == pytest.approx(-0.03)


def test_bootstrap_constant_series_has_zero_width_and_seed_is_repeatable() -> None:
    interval = bootstrap_mean_interval((0.02, 0.02), confidence_level=0.9, samples=50, seed=4)
    assert interval.lower == pytest.approx(0.02)
    assert interval.estimate == pytest.approx(0.02)
    assert interval.upper == pytest.approx(0.02)
    assert interval == bootstrap_mean_interval(
        (0.02, 0.02), confidence_level=0.9, samples=50, seed=4
    )


@pytest.mark.parametrize(
    "values,confidence,samples,match",
    [
        ((), 0.95, 10, "non-empty"),
        ((float("nan"),), 0.95, 10, "finite"),
        ((0.1,), 1.0, 10, "between"),
        ((0.1,), 0.95, 0, "positive"),
    ],
)
def test_bootstrap_rejects_invalid_inputs(
    values: tuple[float, ...], confidence: float, samples: int, match: str
) -> None:
    with pytest.raises(DataQualityError, match=match):
        bootstrap_mean_interval(values, confidence_level=confidence, samples=samples, seed=0)


def test_overlapping_or_leaking_folds_are_rejected() -> None:
    periods, memberships, quality, _ = _inputs()
    dates = tuple(period.observed_on for period in periods)
    leaking = (WalkForwardFold(dates[:3], dates[2:4]),)
    with pytest.raises(DataQualityError, match="training must end"):
        build_walk_forward_report(
            periods,
            memberships,
            quality,
            leaking,
            candidate_top_k=(1,),
            transaction_cost_scenarios_bps=(0.0,),
        )
    overlapping = (
        WalkForwardFold(dates[:2], dates[2:4]),
        WalkForwardFold(dates[:3], dates[3:5]),
    )
    with pytest.raises(DataQualityError, match="overlap"):
        build_walk_forward_report(
            periods,
            memberships,
            quality,
            overlapping,
            candidate_top_k=(1,),
            transaction_cost_scenarios_bps=(0.0,),
        )


def test_dirty_or_invalid_lineage_fails_closed() -> None:
    periods, memberships, quality, folds = _inputs()
    dirty = replace(quality, issues=("missing delisting outcome",))
    with pytest.raises(DataQualityError, match="unresolved"):
        build_walk_forward_report(
            periods,
            memberships,
            dirty,
            folds,
            candidate_top_k=(1,),
            transaction_cost_scenarios_bps=(0.0,),
        )
    invalid_digest = replace(quality, prices_sha256="bad")
    with pytest.raises(DataQualityError, match="SHA-256"):
        build_walk_forward_report(
            periods,
            memberships,
            invalid_digest,
            folds,
            candidate_top_k=(1,),
            transaction_cost_scenarios_bps=(0.0,),
        )


def test_empty_eligible_universe_and_nonfinite_benchmark_fail_closed() -> None:
    periods, _, quality, folds = _inputs()
    with pytest.raises(DataQualityError, match="no eligible"):
        build_walk_forward_report(
            periods,
            [Membership("ZZZ", periods[0].observed_on)],
            quality,
            folds,
            candidate_top_k=(1,),
            transaction_cost_scenarios_bps=(0.0,),
        )
    invalid = (replace(periods[0], benchmark_return=float("nan")),) + periods[1:]
    with pytest.raises(DataQualityError, match="benchmark"):
        build_walk_forward_report(
            invalid,
            [Membership("AAA", periods[0].observed_on)],
            quality,
            folds,
            candidate_top_k=(1,),
            transaction_cost_scenarios_bps=(0.0,),
        )
