# Data model and provenance

- `Provenance`: HTTPS source, license note, timezone-aware retrieval time, schema version.
- `PriceObservation`: ticker, market date, positive and internally consistent OHLC, nonnegative volume.
- `Membership`: ticker and inclusive validity interval.
- `SignalObservation`: date, contemporaneous score and later outcome.

Fixtures are synthetic. A future snapshot must also record checksum, vendor terms, adjustment
policy, calendar, currency and lineage. Membership must represent what was knowable on each date.

`SnapshotManifest` now records an HTTPS source, license note, UTC-aware retrieval timestamp,
schema version, SHA-256, byte size and adjustment policy. It describes lineage, not data validity:
domain-specific price and membership validators must still run after decoding the payload.

`FixtureDescriptor` binds two CSV fixtures to their SHA-256 digests and records generation method,
license, currency, calendar and a typed corporate-action policy. `DataQualityReport` deterministically
summarizes validated coverage; an empty issue list means the declared checks passed, not that a
dataset is complete or suitable for investment research.

`EvaluationPeriod` groups same-date signals with a required benchmark outcome. `WalkForwardFold`
contains explicit training and test dates. `WalkForwardReport` binds scenario and uncertainty
results to the quality report's fixture ID and input SHA-256 digests.
