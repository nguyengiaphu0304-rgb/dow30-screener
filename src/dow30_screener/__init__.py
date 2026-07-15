"""Trustworthy, deterministic research primitives."""

from .data_quality import (
    CorporateActionPolicy,
    DataQualityReport,
    FixtureDescriptor,
    build_quality_report,
    parse_memberships,
    parse_prices,
)
from .ingestion import (
    IngestionError,
    PermanentFetchError,
    Snapshot,
    SnapshotCache,
    SnapshotIngestor,
    SnapshotManifest,
    TransientFetchError,
)
from .quality import (
    DataQualityError,
    Membership,
    PriceObservation,
    Provenance,
    eligible_tickers,
    validate_memberships,
    validate_prices,
    validate_provenance,
)
from .research import SignalObservation, WeeklyResult, evaluate_week

__version__ = "0.2.0"

__all__ = [
    "DataQualityError",
    "DataQualityReport",
    "CorporateActionPolicy",
    "FixtureDescriptor",
    "Membership",
    "IngestionError",
    "PermanentFetchError",
    "PriceObservation",
    "Provenance",
    "SignalObservation",
    "Snapshot",
    "SnapshotCache",
    "SnapshotIngestor",
    "SnapshotManifest",
    "TransientFetchError",
    "WeeklyResult",
    "build_quality_report",
    "eligible_tickers",
    "evaluate_week",
    "parse_memberships",
    "parse_prices",
    "validate_memberships",
    "validate_prices",
    "validate_provenance",
]
