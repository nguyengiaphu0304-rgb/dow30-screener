# ADR 002: Integrity-checked cache with explicit stale fallback

Status: accepted.

Acquisition is nondeterministic, while research should be reproducible. Each downloaded payload is
therefore paired with a canonical manifest containing its source, license note, retrieval time,
schema, size, digest and adjustment policy. Cache reads always verify size and SHA-256. Refreshes
write content-addressed payloads first, then atomically replace the manifest pointer. Stale data may be returned only when a
caller explicitly opts in and the refresh failed transiently; corruption and permanent HTTP errors
always fail closed. This prioritizes data integrity over availability.
