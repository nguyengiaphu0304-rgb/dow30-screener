# Synthetic quality fixture

These values are deterministic, project-authored synthetic test data licensed under this
repository's MIT license. They do not represent Dow constituents, securities, historical prices,
returns, or investment performance. The three-date calendar and `AAA`/`BBB` identifiers exist only
to test benchmark coverage and point-in-time membership behavior.

`expected-report.json` is the canonical output of `build_quality_report` for the two CSV files and
is checked byte-for-byte in tests. `descriptor.json` binds the source bytes to their SHA-256 values.
