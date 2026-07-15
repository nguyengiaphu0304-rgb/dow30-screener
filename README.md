# Dow 30 Screener

A provenance-aware, educational equity-research toolkit. The verified core validates price,
benchmark and point-in-time membership data, then evaluates deterministic weekly selections with
explicit transaction costs. It is **not financial advice** and is not production-trading software.

## Trust status

The repository retains the original scripts, database, charts and CSV outputs for auditability.
Those legacy artifacts are **unverified exploratory results**, not evidence of returns or alpha:
they apply a current constituent list to earlier dates, use unadjusted Yahoo Finance prices, tune
parameters over broad history, omit transaction costs and lack a source/license manifest. Claims
in those artifacts must not be relied on.

The new `src/dow30_screener` core is offline and deterministic. It fails closed on duplicate or
invalid prices, missing benchmark observations, future retrieval timestamps, overlapping
membership intervals, non-finite signals and invalid costs. Selection uses only information
available on the observation date; forward returns are used solely after ranking.

Its ingestion boundary adds versioned manifests, SHA-256 verification, bounded retry and atomic
cache refresh. Serving stale data requires an explicit opt-in and is limited to transient failures;
corruption and permanent errors always fail closed. Network transports remain adapter code rather
than part of the deterministic domain model.

The repository also ships a small MIT-licensed **synthetic** fixture plus a stable quality-report
generator. It validates schema, checksums, benchmark coverage, membership timing and an explicit
corporate-action policy. The fixture is test evidence only and contains no real security history.
See the [corporate-action policy](docs/corporate-actions.md).

## Architecture

`quality.py` owns the data trust boundary and point-in-time eligibility. `research.py` owns the
small, auditable weekly calculation. Network ingestion and legacy notebooks stay outside the
domain core. See [architecture](docs/architecture.md), [data model](docs/data-model.md),
[threat model](docs/threat-model.md), and [ADR 001](docs/adr/001-trustworthy-foundation.md).

## Reproducible setup and verification

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
ruff check src tests
ruff format --check src tests
mypy src
pytest
python -m build
python -m pip check
pip-audit
```

Tests use synthetic fixtures and require no network. To run old exploratory scripts, install
`.[legacy]`; review their source and limitations before execution.

## Limitations and roadmap

No verified point-in-time Dow membership or licensed price snapshot ships yet. Corporate actions,
delistings, taxes, slippage, uncertainty and walk-forward parameter selection are not fully
modeled. See the [roadmap](docs/roadmap.md) and [interview guide](docs/interview-guide.md).
