# Data model and provenance

- `Provenance`: HTTPS source, license note, timezone-aware retrieval time, schema version.
- `PriceObservation`: ticker, market date, positive and internally consistent OHLC, nonnegative volume.
- `Membership`: ticker and inclusive validity interval.
- `SignalObservation`: date, contemporaneous score and later outcome.

Fixtures are synthetic. A future snapshot must also record checksum, vendor terms, adjustment
policy, calendar, currency and lineage. Membership must represent what was knowable on each date.
