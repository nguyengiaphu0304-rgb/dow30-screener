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

The walk-forward evaluator adds explicit expanding-window folds, training-only portfolio-size
selection, benchmark and equal-weight baselines, predeclared transaction-cost sensitivity, and a
seeded bootstrap interval. Its deterministic JSON report is accepted only with a clean quality
report and includes the verified fixture digests. Synthetic results demonstrate correctness, not
historical returns.

Every report now carries a typed [survivorship disclosure](docs/survivorship-policy.md) and a digest
of the exact evaluation observations. Historical inputs fail closed unless they include exited
members, exit-return treatment and mapped symbol changes. The bundled demo is explicitly synthetic.

## Architecture

`quality.py` owns the data trust boundary and point-in-time eligibility. `research.py` owns the
small, auditable weekly calculation. `evaluation.py` owns chronological folds, baselines,
uncertainty and stable reporting. Network ingestion and legacy notebooks stay outside the
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
dow30-screener-demo --output /tmp/walk-forward-report.json
diff -u docs/demo/walk-forward-report.json /tmp/walk-forward-report.json
```

Tests use synthetic fixtures and require no network. To run old exploratory scripts, install
`.[legacy]`; review their source and limitations before execution.

## Limitations and roadmap

No verified historical Dow membership or real price snapshot ships. The included fixture is
project-authored synthetic data. Delistings, symbol changes, taxes, real exchange calendars,
serial dependence and vendor corrections are not fully modeled. See the [roadmap](docs/roadmap.md)
and [interview guide](docs/interview-guide.md).

Release evidence and unperformed checks are listed in the
[v1.0 checklist](docs/release-checklist.md). Release notes are in
[`docs/releases/v1.0.0.md`](docs/releases/v1.0.0.md).
