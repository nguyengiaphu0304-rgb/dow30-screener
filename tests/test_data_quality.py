import json
from pathlib import Path

import pytest

from dow30_screener import DataQualityError, build_quality_report, parse_memberships, parse_prices

FIXTURES = Path(__file__).parent / "fixtures/quality"
PRICES = (FIXTURES / "prices.csv").read_bytes()
MEMBERSHIPS = (FIXTURES / "memberships.csv").read_bytes()
DESCRIPTOR = (FIXTURES / "descriptor.json").read_text()


def report(
    price_bytes: bytes = PRICES, membership_bytes: bytes = MEMBERSHIPS, descriptor: str = DESCRIPTOR
):
    return build_quality_report(price_bytes, membership_bytes, descriptor)


def test_fixture_builds_stable_auditable_report() -> None:
    result = report()
    assert result.fixture_id == "synthetic-quality-v1"
    assert (result.price_rows, result.membership_rows, result.ticker_count) == (8, 2, 3)
    assert result.corporate_action_policy.value == "raw"
    assert result.issues == ()
    assert result.to_json() == (FIXTURES / "expected-report.json").read_text()
    assert json.loads(result.to_json())["first_date"] == "2026-01-05"


@pytest.mark.parametrize(
    "value",
    [
        b"",
        b"ticker,observed_on,open,high,low,close\n",
        PRICES.replace(b"ticker,observed_on", b"observed_on,ticker", 1),
    ],
)
def test_price_schema_is_strict(value: bytes) -> None:
    with pytest.raises(DataQualityError):
        parse_prices(value)


@pytest.mark.parametrize("bad", [b"nan", b"-1"])
def test_rejects_non_finite_or_negative_price(bad: bytes) -> None:
    with pytest.raises(DataQualityError):
        parse_prices(PRICES.replace(b"100,103", bad + b",103", 1))


def test_rejects_duplicate_price_key() -> None:
    duplicate = PRICES + PRICES.splitlines(keepends=True)[1]
    with pytest.raises(DataQualityError, match="duplicate"):
        parse_prices(duplicate)


def test_rejects_missing_benchmark_date() -> None:
    lines = [
        line for line in PRICES.splitlines(keepends=True) if not line.startswith(b"SPY,2026-01-06")
    ]
    with pytest.raises(DataQualityError, match="benchmark"):
        parse_prices(b"".join(lines))


def test_rejects_checksum_mismatch() -> None:
    with pytest.raises(DataQualityError, match="checksum"):
        report(PRICES.replace(b"AAA", b"ZZZ", 1))


def test_rejects_unknown_policy_and_schema() -> None:
    value = json.loads(DESCRIPTOR)
    value["corporate_action_policy"] = "sometimes_adjusted"
    with pytest.raises(DataQualityError, match="malformed"):
        report(descriptor=json.dumps(value))
    value = json.loads(DESCRIPTOR)
    value["schema_version"] = 2
    with pytest.raises(DataQualityError, match="schema"):
        report(descriptor=json.dumps(value))


def test_rejects_price_outside_membership() -> None:
    changed = MEMBERSHIPS.replace(b"BBB,2026-01-06", b"BBB,2026-01-07")
    descriptor = json.loads(DESCRIPTOR)
    from hashlib import sha256

    descriptor["memberships_sha256"] = sha256(changed).hexdigest()
    with pytest.raises(DataQualityError, match="outside membership"):
        report(membership_bytes=changed, descriptor=json.dumps(descriptor))


def test_membership_open_interval_and_overlap() -> None:
    values = parse_memberships(MEMBERSHIPS)
    assert values[0].valid_to is None
    overlap = MEMBERSHIPS + b"AAA,2026-01-02,OPEN\n"
    with pytest.raises(DataQualityError, match="overlapping"):
        parse_memberships(overlap)


def test_decoded_records_have_canonical_order() -> None:
    header, *rows = PRICES.splitlines()
    reversed_prices = b"\n".join([header, *reversed(rows)]) + b"\n"
    parsed = parse_prices(reversed_prices)
    assert [(row.observed_on.isoformat(), row.ticker) for row in parsed] == sorted(
        (row.observed_on.isoformat(), row.ticker) for row in parsed
    )
