from datetime import UTC, date, datetime, timedelta

import pytest

from dow30_screener import (
    DataQualityError,
    Membership,
    PriceObservation,
    Provenance,
    eligible_tickers,
    validate_memberships,
    validate_prices,
    validate_provenance,
)


def price(ticker: str, *, close: float = 10, volume: int = 100) -> PriceObservation:
    return PriceObservation(ticker, date(2026, 1, 5), 9, 11, 8, close, volume)


def test_validates_complete_prices() -> None:
    validate_prices([price("AAA"), price("SPY")])


@pytest.mark.parametrize(
    "rows",
    [
        [],
        [price("AAA"), price("AAA"), price("SPY")],
        [price("AAA")],
        [price("AAA", close=-1), price("SPY")],
        [price("AAA", volume=-1), price("SPY")],
    ],
)
def test_rejects_unsafe_prices(rows: list[PriceObservation]) -> None:
    with pytest.raises(DataQualityError):
        validate_prices(rows)


def test_rejects_future_provenance() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    value = Provenance("https://example.com/data", "CC0 synthetic", now + timedelta(days=1))
    with pytest.raises(DataQualityError, match="future"):
        validate_provenance(value, now=now)


def test_membership_boundaries_are_inclusive_and_non_overlapping() -> None:
    rows = [Membership("AAA", date(2025, 1, 1), date(2025, 12, 31))]
    assert eligible_tickers(rows, date(2025, 1, 1)) == ("AAA",)
    assert eligible_tickers(rows, date(2025, 12, 31)) == ("AAA",)
    with pytest.raises(DataQualityError, match="overlapping"):
        validate_memberships(rows + [Membership("AAA", date(2025, 12, 31))])
