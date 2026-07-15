"""Strict decoding and deterministic quality reporting for fixture bundles."""

from __future__ import annotations

import csv
import io
import json
from dataclasses import asdict, dataclass
from datetime import date, datetime
from enum import StrEnum
from hashlib import sha256

from .quality import (
    DataQualityError,
    Membership,
    PriceObservation,
    eligible_tickers,
    validate_memberships,
    validate_prices,
)

PRICE_COLUMNS = ["ticker", "observed_on", "open", "high", "low", "close", "volume"]
MEMBERSHIP_COLUMNS = ["ticker", "valid_from", "valid_to"]


class CorporateActionPolicy(StrEnum):
    RAW = "raw"
    SPLIT_ADJUSTED = "split_adjusted"
    TOTAL_RETURN_ADJUSTED = "total_return_adjusted"


@dataclass(frozen=True, slots=True)
class FixtureDescriptor:
    fixture_id: str
    source_note: str
    license: str
    generated_at: datetime
    generation_method: str
    currency: str
    exchange_calendar: str
    corporate_action_policy: CorporateActionPolicy
    prices_sha256: str
    memberships_sha256: str
    schema_version: int = 1

    @classmethod
    def from_json(cls, raw: str) -> FixtureDescriptor:
        expected = {
            "corporate_action_policy",
            "currency",
            "exchange_calendar",
            "fixture_id",
            "generated_at",
            "generation_method",
            "license",
            "memberships_sha256",
            "prices_sha256",
            "schema_version",
            "source_note",
        }
        try:
            value = json.loads(raw)
            if not isinstance(value, dict) or set(value) != expected:
                raise ValueError("unexpected descriptor fields")
            descriptor = cls(
                fixture_id=value["fixture_id"],
                source_note=value["source_note"],
                license=value["license"],
                generated_at=datetime.fromisoformat(value["generated_at"]),
                generation_method=value["generation_method"],
                currency=value["currency"],
                exchange_calendar=value["exchange_calendar"],
                corporate_action_policy=CorporateActionPolicy(value["corporate_action_policy"]),
                prices_sha256=value["prices_sha256"],
                memberships_sha256=value["memberships_sha256"],
                schema_version=value["schema_version"],
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise DataQualityError("malformed fixture descriptor") from error
        descriptor.validate()
        return descriptor

    def validate(self) -> None:
        if self.schema_version != 1:
            raise DataQualityError("unsupported fixture descriptor schema")
        if self.generated_at.tzinfo is None:
            raise DataQualityError("fixture generated_at must be timezone-aware")
        required = (
            self.fixture_id,
            self.source_note,
            self.license,
            self.generation_method,
            self.currency,
            self.exchange_calendar,
        )
        if any(not value.strip() for value in required):
            raise DataQualityError("fixture descriptor text fields cannot be blank")
        for digest in (self.prices_sha256, self.memberships_sha256):
            if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
                raise DataQualityError("fixture descriptor has invalid SHA-256")


@dataclass(frozen=True, slots=True)
class DataQualityReport:
    fixture_id: str
    price_rows: int
    membership_rows: int
    ticker_count: int
    first_date: date
    last_date: date
    benchmark: str
    currency: str
    exchange_calendar: str
    corporate_action_policy: CorporateActionPolicy
    prices_sha256: str
    memberships_sha256: str
    issues: tuple[str, ...] = ()

    def to_json(self) -> str:
        value = asdict(self)
        value["first_date"] = self.first_date.isoformat()
        value["last_date"] = self.last_date.isoformat()
        value["corporate_action_policy"] = self.corporate_action_policy.value
        value["issues"] = list(self.issues)
        return json.dumps(value, indent=2, sort_keys=True) + "\n"


def _rows(raw: bytes, expected: list[str], label: str) -> list[dict[str, str]]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise DataQualityError(f"{label} CSV must be UTF-8") from error
    reader = csv.DictReader(io.StringIO(text, newline=""))
    if reader.fieldnames != expected:
        raise DataQualityError(f"{label} CSV columns must exactly match {expected}")
    rows = list(reader)
    if not rows:
        raise DataQualityError(f"{label} CSV is empty")
    if any(value is None or not value.strip() for row in rows for value in row.values()):
        raise DataQualityError(f"{label} CSV contains blank fields")
    return rows


def parse_prices(raw: bytes) -> list[PriceObservation]:
    try:
        values = [
            PriceObservation(
                row["ticker"],
                date.fromisoformat(row["observed_on"]),
                float(row["open"]),
                float(row["high"]),
                float(row["low"]),
                float(row["close"]),
                int(row["volume"]),
            )
            for row in _rows(raw, PRICE_COLUMNS, "prices")
        ]
    except (ValueError, OverflowError) as error:
        raise DataQualityError("prices CSV contains an invalid typed value") from error
    validate_prices(values)
    return sorted(values, key=lambda row: (row.observed_on, row.ticker))


def parse_memberships(raw: bytes) -> list[Membership]:
    rows = _rows(raw, MEMBERSHIP_COLUMNS, "memberships")
    try:
        values = [
            Membership(
                row["ticker"],
                date.fromisoformat(row["valid_from"]),
                None if row["valid_to"] == "OPEN" else date.fromisoformat(row["valid_to"]),
            )
            for row in rows
        ]
    except ValueError as error:
        raise DataQualityError("memberships CSV contains an invalid date") from error
    validate_memberships(values)
    return sorted(values, key=lambda row: (row.ticker, row.valid_from))


def build_quality_report(
    price_bytes: bytes, membership_bytes: bytes, descriptor_json: str, *, benchmark: str = "SPY"
) -> DataQualityReport:
    descriptor = FixtureDescriptor.from_json(descriptor_json)
    price_digest = sha256(price_bytes).hexdigest()
    membership_digest = sha256(membership_bytes).hexdigest()
    if (
        price_digest != descriptor.prices_sha256
        or membership_digest != descriptor.memberships_sha256
    ):
        raise DataQualityError("fixture checksum mismatch")
    prices = parse_prices(price_bytes)
    memberships = parse_memberships(membership_bytes)
    member_tickers = {row.ticker for row in memberships}
    equity_prices = [row for row in prices if row.ticker != benchmark]
    unknown = sorted({row.ticker for row in equity_prices} - member_tickers)
    if unknown:
        raise DataQualityError(f"price ticker has no membership history: {unknown[0]}")
    for row in equity_prices:
        if row.ticker not in eligible_tickers(memberships, row.observed_on):
            raise DataQualityError(
                f"{row.ticker} price falls outside membership on {row.observed_on}"
            )
    dates = sorted({row.observed_on for row in prices})
    tickers = {row.ticker for row in prices}
    return DataQualityReport(
        fixture_id=descriptor.fixture_id,
        price_rows=len(prices),
        membership_rows=len(memberships),
        ticker_count=len(tickers),
        first_date=dates[0],
        last_date=dates[-1],
        benchmark=benchmark,
        currency=descriptor.currency,
        exchange_calendar=descriptor.exchange_calendar,
        corporate_action_policy=descriptor.corporate_action_policy,
        prices_sha256=price_digest,
        memberships_sha256=membership_digest,
    )
