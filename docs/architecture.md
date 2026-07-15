# Architecture

The package separates untrusted acquisition from deterministic research. `quality` validates
provenance, OHLCV invariants, benchmark completeness and non-overlapping point-in-time membership.
Only validated domain objects should reach `research`, which ranks by contemporaneous score,
applies an explicit cost and reports benchmark-relative results. This boundary makes tests offline,
repeatable and independent of a data vendor. Legacy scripts remain isolated until migrated.

`ingestion.py` accepts a transport interface, so HTTP behavior is separated from snapshot policy.
It verifies source metadata, payload size and SHA-256 on every cache read. Refreshes use temporary
files plus atomic replacement; a caller must explicitly opt into stale data after transient failure.
