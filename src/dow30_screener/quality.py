"""Validation at the research data trust boundary."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime
from math import isfinite
from urllib.parse import urlparse


class DataQualityError(ValueError):
    """Raised when inputs are unsafe for analysis."""


@dataclass(frozen=True, slots=True)
class Provenance:
    source_url: str
    license_note: str
    retrieved_at: datetime
    schema_version: int = 1


@dataclass(frozen=True, slots=True)
class PriceObservation:
    ticker: str
    observed_on: date
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass(frozen=True, slots=True)
class Membership:
    ticker: str
    valid_from: date
    valid_to: date | None = None

    def contains(self, observed_on: date) -> bool:
        return self.valid_from <= observed_on and (
            self.valid_to is None or observed_on <= self.valid_to
        )


def validate_provenance(value: Provenance, *, now: datetime | None = None) -> None:
    parsed = urlparse(value.source_url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise DataQualityError("source_url must be an absolute HTTPS URL")
    if not value.license_note.strip():
        raise DataQualityError("license_note is required")
    if value.schema_version != 1:
        raise DataQualityError("unsupported provenance schema version")
    if value.retrieved_at.tzinfo is None:
        raise DataQualityError("retrieved_at must be timezone-aware")
    if value.retrieved_at > (now or datetime.now(UTC)):
        raise DataQualityError("retrieved_at cannot be in the future")


def validate_prices(rows: list[PriceObservation], *, benchmark: str = "SPY") -> None:
    if not rows:
        raise DataQualityError("price observations are empty")
    seen: set[tuple[str, date]] = set()
    dates: set[date] = set()
    benchmark_dates: set[date] = set()
    for row in rows:
        key = (row.ticker, row.observed_on)
        if key in seen:
            raise DataQualityError(f"duplicate price observation: {row.ticker} {row.observed_on}")
        seen.add(key)
        dates.add(row.observed_on)
        if row.ticker == benchmark:
            benchmark_dates.add(row.observed_on)
        values = (row.open, row.high, row.low, row.close)
        if not all(isfinite(value) and value > 0 for value in values):
            raise DataQualityError(f"invalid OHLC values for {row.ticker}")
        if row.high < max(row.open, row.low, row.close) or row.low > min(values):
            raise DataQualityError(f"inconsistent OHLC values for {row.ticker}")
        if row.volume < 0:
            raise DataQualityError(f"negative volume for {row.ticker}")
    missing = sorted(dates - benchmark_dates)
    if missing:
        raise DataQualityError(f"benchmark {benchmark} missing for {missing[0]}")


def validate_memberships(rows: list[Membership]) -> None:
    if not rows:
        raise DataQualityError("membership history is empty")
    grouped: dict[str, list[Membership]] = defaultdict(list)
    for row in rows:
        if row.valid_to is not None and row.valid_to < row.valid_from:
            raise DataQualityError(f"invalid membership interval for {row.ticker}")
        grouped[row.ticker].append(row)
    for ticker, intervals in grouped.items():
        ordered = sorted(intervals, key=lambda item: item.valid_from)
        for previous, current in zip(ordered, ordered[1:], strict=False):
            if previous.valid_to is None or current.valid_from <= previous.valid_to:
                raise DataQualityError(f"overlapping membership intervals for {ticker}")


def eligible_tickers(rows: list[Membership], observed_on: date) -> tuple[str, ...]:
    validate_memberships(rows)
    return tuple(sorted({row.ticker for row in rows if row.contains(observed_on)}))
