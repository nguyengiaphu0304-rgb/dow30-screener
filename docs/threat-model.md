# Threat model

Protected properties are reproducibility, provenance and temporal integrity. Threats include
malformed or duplicated rows, missing benchmarks, revised data, look-ahead membership, target
leakage, unsafe fallback behavior, dependency compromise and misleading performance claims.
Current controls are immutable typed records, fail-closed validation, deterministic tie-breaking,
offline fixtures, least-privilege CI and dependency audit. Vendor authenticity and historical
membership accuracy remain outside the current trust envelope.
