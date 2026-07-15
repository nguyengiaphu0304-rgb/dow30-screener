# Architecture

The package separates untrusted acquisition from deterministic research. `quality` validates
provenance, OHLCV invariants, benchmark completeness and non-overlapping point-in-time membership.
Only validated domain objects should reach `research`, which ranks by contemporaneous score,
applies an explicit cost and reports benchmark-relative results. This boundary makes tests offline,
repeatable and independent of a data vendor. Legacy scripts remain isolated until migrated.
