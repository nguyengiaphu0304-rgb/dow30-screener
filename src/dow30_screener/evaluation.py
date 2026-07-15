"""Leakage-resistant walk-forward evaluation over verified offline observations."""

from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass
from datetime import date
from enum import StrEnum
from math import isfinite

from .data_quality import DataQualityReport
from .quality import DataQualityError, Membership, eligible_tickers
from .research import SignalObservation, evaluate_week


@dataclass(frozen=True, slots=True)
class EvaluationPeriod:
    observed_on: date
    signals: tuple[SignalObservation, ...]
    benchmark_return: float


class UniverseKind(StrEnum):
    SYNTHETIC = "synthetic"
    POINT_IN_TIME_HISTORICAL = "point_in_time_historical"


class ExitReturnPolicy(StrEnum):
    NOT_APPLICABLE = "not_applicable"
    OBSERVED = "observed"
    IMPUTED = "imputed"
    UNAVAILABLE = "unavailable"


class SymbolChangePolicy(StrEnum):
    NOT_APPLICABLE = "not_applicable"
    MAPPED = "mapped"
    UNAVAILABLE = "unavailable"


class MissingReturnPolicy(StrEnum):
    FAIL_CLOSED = "fail_closed"
    ZERO = "zero"


@dataclass(frozen=True, slots=True)
class UniverseDisclosure:
    universe_kind: UniverseKind
    includes_exited_members: bool
    exit_return_policy: ExitReturnPolicy
    symbol_change_policy: SymbolChangePolicy
    missing_return_policy: MissingReturnPolicy
    methodology_note: str

    def validate(self) -> None:
        if not self.methodology_note.strip():
            raise DataQualityError("universe disclosure methodology note is required")
        if self.missing_return_policy is not MissingReturnPolicy.FAIL_CLOSED:
            raise DataQualityError("missing returns must fail closed")
        if self.universe_kind is UniverseKind.SYNTHETIC:
            if self.includes_exited_members:
                raise DataQualityError("synthetic universe cannot claim historical exited members")
            if self.exit_return_policy is not ExitReturnPolicy.NOT_APPLICABLE:
                raise DataQualityError(
                    "synthetic universe exit-return policy must be not_applicable"
                )
            if self.symbol_change_policy is not SymbolChangePolicy.NOT_APPLICABLE:
                raise DataQualityError("synthetic universe symbol policy must be not_applicable")
            return
        if not self.includes_exited_members:
            raise DataQualityError("historical universe must include exited members")
        if self.exit_return_policy not in (ExitReturnPolicy.OBSERVED, ExitReturnPolicy.IMPUTED):
            raise DataQualityError("historical universe requires an explicit exit-return treatment")
        if self.symbol_change_policy is not SymbolChangePolicy.MAPPED:
            raise DataQualityError("historical universe requires mapped symbol changes")


@dataclass(frozen=True, slots=True)
class WalkForwardFold:
    train_dates: tuple[date, ...]
    test_dates: tuple[date, ...]


@dataclass(frozen=True, slots=True)
class PeriodResult:
    observed_on: date
    selected_top_k: int
    strategy_net_return: float
    benchmark_return: float
    equal_weight_net_return: float
    excess_return: float


@dataclass(frozen=True, slots=True)
class UncertaintyInterval:
    confidence_level: float
    lower: float
    estimate: float
    upper: float
    bootstrap_samples: int
    seed: int


@dataclass(frozen=True, slots=True)
class SensitivityResult:
    transaction_cost_bps: float
    periods: tuple[PeriodResult, ...]
    mean_strategy_return: float
    mean_benchmark_return: float
    mean_equal_weight_return: float
    mean_excess_return: float
    uncertainty: UncertaintyInterval


@dataclass(frozen=True, slots=True)
class WalkForwardReport:
    schema_version: int
    fixture_id: str
    prices_sha256: str
    memberships_sha256: str
    observations_sha256: str
    universe_disclosure: UniverseDisclosure
    candidate_top_k: tuple[int, ...]
    scenarios: tuple[SensitivityResult, ...]
    limitations: tuple[str, ...]

    def to_json(self) -> str:
        value = asdict(self)
        for scenario in value["scenarios"]:
            for period in scenario["periods"]:
                period["observed_on"] = period["observed_on"].isoformat()
        return json.dumps(_normalize_numbers(value), indent=2, sort_keys=True) + "\n"


def _normalize_numbers(value: object) -> object:
    if isinstance(value, float):
        rounded = round(value, 12)
        return 0.0 if rounded == 0 else rounded
    if isinstance(value, dict):
        return {str(key): _normalize_numbers(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalize_numbers(item) for item in value]
    return value


def expanding_window_folds(
    dates: tuple[date, ...], *, minimum_train_periods: int, test_periods: int
) -> tuple[WalkForwardFold, ...]:
    if minimum_train_periods <= 0 or test_periods <= 0:
        raise DataQualityError("train and test period counts must be positive")
    ordered = tuple(sorted(dates))
    if len(set(ordered)) != len(ordered):
        raise DataQualityError("evaluation dates must be unique")
    if len(ordered) < minimum_train_periods + test_periods:
        raise DataQualityError("not enough periods for one walk-forward fold")
    folds: list[WalkForwardFold] = []
    cursor = minimum_train_periods
    while cursor + test_periods <= len(ordered):
        folds.append(WalkForwardFold(ordered[:cursor], ordered[cursor : cursor + test_periods]))
        cursor += test_periods
    return tuple(folds)


def _validate_folds(folds: tuple[WalkForwardFold, ...], available: set[date]) -> None:
    if not folds:
        raise DataQualityError("at least one walk-forward fold is required")
    previous_test_end: date | None = None
    for fold in folds:
        if not fold.train_dates or not fold.test_dates:
            raise DataQualityError("fold train and test windows cannot be empty")
        if tuple(sorted(set(fold.train_dates))) != fold.train_dates:
            raise DataQualityError("fold training dates must be sorted and unique")
        if tuple(sorted(set(fold.test_dates))) != fold.test_dates:
            raise DataQualityError("fold test dates must be sorted and unique")
        if set(fold.train_dates + fold.test_dates) - available:
            raise DataQualityError("fold references an unavailable observation date")
        if fold.train_dates[-1] >= fold.test_dates[0]:
            raise DataQualityError("training must end before testing begins")
        if previous_test_end is not None and fold.test_dates[0] <= previous_test_end:
            raise DataQualityError("fold test windows cannot overlap or move backward")
        previous_test_end = fold.test_dates[-1]


def _validate_lineage(report: DataQualityReport, dates: set[date]) -> None:
    if report.issues:
        raise DataQualityError("quality report contains unresolved issues")
    if not report.fixture_id.strip():
        raise DataQualityError("quality report fixture_id is required")
    for digest in (report.prices_sha256, report.memberships_sha256):
        if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
            raise DataQualityError("quality report has invalid SHA-256 lineage")
    if min(dates) < report.first_date or max(dates) > report.last_date:
        raise DataQualityError("evaluation dates fall outside verified snapshot coverage")


def _validate_periods(periods: tuple[EvaluationPeriod, ...]) -> dict[date, EvaluationPeriod]:
    if not periods:
        raise DataQualityError("evaluation periods are empty")
    indexed: dict[date, EvaluationPeriod] = {}
    for period in periods:
        if period.observed_on in indexed:
            raise DataQualityError("duplicate evaluation period")
        if not period.signals:
            raise DataQualityError("evaluation period signals are empty")
        if not isfinite(period.benchmark_return):
            raise DataQualityError("benchmark return must be finite")
        if any(signal.observed_on != period.observed_on for signal in period.signals):
            raise DataQualityError("signal date does not match its evaluation period")
        indexed[period.observed_on] = period
    return indexed


def _mean(values: list[float]) -> float:
    if not values:
        raise DataQualityError("cannot summarize an empty return series")
    return sum(values) / len(values)


def _choose_top_k(
    train_dates: tuple[date, ...],
    periods: dict[date, EvaluationPeriod],
    memberships: list[Membership],
    candidates: tuple[int, ...],
    cost_bps: float,
) -> int:
    scored: list[tuple[float, int]] = []
    for top_k in candidates:
        excess: list[float] = []
        for observed_on in train_dates:
            period = periods[observed_on]
            result = evaluate_week(
                list(period.signals),
                memberships,
                benchmark_return=period.benchmark_return,
                top_k=top_k,
                transaction_cost_bps=cost_bps,
            )
            if result is None:
                raise DataQualityError("training period has no eligible signals")
            excess.append(result.excess_return)
        scored.append((_mean(excess), top_k))
    return min(scored, key=lambda item: (-item[0], item[1]))[1]


def bootstrap_mean_interval(
    values: tuple[float, ...], *, confidence_level: float, samples: int, seed: int
) -> UncertaintyInterval:
    if not values or any(not isfinite(value) for value in values):
        raise DataQualityError("bootstrap values must be non-empty and finite")
    if not 0 < confidence_level < 1:
        raise DataQualityError("confidence level must be between zero and one")
    if samples <= 0:
        raise DataQualityError("bootstrap samples must be positive")
    rng = random.Random(seed)
    estimates = sorted(
        _mean([values[rng.randrange(len(values))] for _ in values]) for _ in range(samples)
    )
    tail = (1 - confidence_level) / 2
    lower_index = int(tail * (samples - 1))
    upper_index = int((1 - tail) * (samples - 1))
    return UncertaintyInterval(
        confidence_level=confidence_level,
        lower=estimates[lower_index],
        estimate=_mean(list(values)),
        upper=estimates[upper_index],
        bootstrap_samples=samples,
        seed=seed,
    )


def build_walk_forward_report(
    periods: tuple[EvaluationPeriod, ...],
    memberships: list[Membership],
    quality_report: DataQualityReport,
    universe_disclosure: UniverseDisclosure,
    folds: tuple[WalkForwardFold, ...],
    *,
    observations_sha256: str,
    candidate_top_k: tuple[int, ...],
    transaction_cost_scenarios_bps: tuple[float, ...],
    confidence_level: float = 0.95,
    bootstrap_samples: int = 2_000,
    seed: int = 0,
) -> WalkForwardReport:
    indexed = _validate_periods(periods)
    dates = set(indexed)
    _validate_lineage(quality_report, dates)
    universe_disclosure.validate()
    if len(observations_sha256) != 64 or any(
        char not in "0123456789abcdef" for char in observations_sha256
    ):
        raise DataQualityError("evaluation observations require valid SHA-256 lineage")
    _validate_folds(folds, dates)
    if not candidate_top_k or any(value <= 0 for value in candidate_top_k):
        raise DataQualityError("candidate top_k values must be positive")
    if tuple(sorted(set(candidate_top_k))) != candidate_top_k:
        raise DataQualityError("candidate top_k values must be sorted and unique")
    if not transaction_cost_scenarios_bps:
        raise DataQualityError("at least one transaction-cost scenario is required")
    if tuple(sorted(set(transaction_cost_scenarios_bps))) != transaction_cost_scenarios_bps:
        raise DataQualityError("transaction-cost scenarios must be sorted and unique")
    if any(not isfinite(value) or value < 0 for value in transaction_cost_scenarios_bps):
        raise DataQualityError("transaction-cost scenarios must be finite and non-negative")

    scenarios: list[SensitivityResult] = []
    for scenario_index, cost_bps in enumerate(transaction_cost_scenarios_bps):
        results: list[PeriodResult] = []
        for fold in folds:
            selected_top_k = _choose_top_k(
                fold.train_dates, indexed, memberships, candidate_top_k, cost_bps
            )
            for observed_on in fold.test_dates:
                period = indexed[observed_on]
                strategy = evaluate_week(
                    list(period.signals),
                    memberships,
                    benchmark_return=period.benchmark_return,
                    top_k=selected_top_k,
                    transaction_cost_bps=cost_bps,
                )
                if strategy is None:
                    raise DataQualityError("test period has no eligible signals")
                eligible = set(eligible_tickers(memberships, observed_on))
                eligible_signals = [
                    signal for signal in period.signals if signal.ticker in eligible
                ]
                if not eligible_signals:
                    raise DataQualityError("equal-weight baseline has no eligible signals")
                equal_weight = _mean([signal.forward_return for signal in eligible_signals]) - (
                    cost_bps / 10_000
                )
                results.append(
                    PeriodResult(
                        observed_on=observed_on,
                        selected_top_k=selected_top_k,
                        strategy_net_return=strategy.net_return,
                        benchmark_return=period.benchmark_return,
                        equal_weight_net_return=equal_weight,
                        excess_return=strategy.excess_return,
                    )
                )
        excess = tuple(result.excess_return for result in results)
        scenarios.append(
            SensitivityResult(
                transaction_cost_bps=cost_bps,
                periods=tuple(results),
                mean_strategy_return=_mean([result.strategy_net_return for result in results]),
                mean_benchmark_return=_mean([result.benchmark_return for result in results]),
                mean_equal_weight_return=_mean(
                    [result.equal_weight_net_return for result in results]
                ),
                mean_excess_return=_mean(list(excess)),
                uncertainty=bootstrap_mean_interval(
                    excess,
                    confidence_level=confidence_level,
                    samples=bootstrap_samples,
                    seed=seed + scenario_index,
                ),
            )
        )
    return WalkForwardReport(
        schema_version=1,
        fixture_id=quality_report.fixture_id,
        prices_sha256=quality_report.prices_sha256,
        memberships_sha256=quality_report.memberships_sha256,
        observations_sha256=observations_sha256,
        universe_disclosure=universe_disclosure,
        candidate_top_k=candidate_top_k,
        scenarios=tuple(scenarios),
        limitations=(
            "Synthetic fixtures are test evidence, not historical Dow performance.",
            "Delistings, symbol changes, taxes and vendor corrections are not modeled.",
            "This educational report is not financial advice or production-trading evidence.",
        ),
    )
