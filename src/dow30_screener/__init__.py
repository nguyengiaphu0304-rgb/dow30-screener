"""Trustworthy, deterministic research primitives."""

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
    "eligible_tickers",
    "evaluate_week",
    "validate_memberships",
    "validate_prices",
    "validate_provenance",
]
