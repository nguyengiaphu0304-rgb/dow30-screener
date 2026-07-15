# v1.0 release checklist

## Automated and completed

- [x] Ruff lint and formatting
- [x] Strict MyPy
- [x] Unit and integration tests, including deterministic demo comparison
- [x] Wheel and source distribution build
- [x] Clean-environment wheel installation and demo command
- [x] Dependency consistency and vulnerability audit
- [x] Secret-pattern scan and clean Git diff
- [x] GitHub Actions on Python 3.11 and 3.12

## Repository review and completed

- [x] Architecture, ADR, data model and threat model match behavior
- [x] Synthetic fixtures identify provenance, license and limitations
- [x] Legacy artifacts are labeled unverified
- [x] README states educational use and no financial advice
- [x] Release demo is reproducible and contains no real return claim

## Not performed and not claimed

- [ ] Validation with licensed historical Dow constituent and delisting data
- [ ] Independent financial-model review
- [ ] Production broker, order-routing or live-trading integration testing
- [ ] Tax, market-impact or real exchange-calendar validation

The unchecked items are product limitations, not hidden release gates. Version 1.0 is a verified
educational software release, not a declaration of trading readiness or investment performance.
