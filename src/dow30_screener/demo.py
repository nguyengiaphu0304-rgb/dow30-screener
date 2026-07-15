"""Generate the release demo from a fully synthetic, integrity-checked snapshot."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from typing import cast

from .data_quality import build_quality_report
from .evaluation import (
    EvaluationPeriod,
    ExitReturnPolicy,
    MissingReturnPolicy,
    SymbolChangePolicy,
    UniverseDisclosure,
    UniverseKind,
    build_walk_forward_report,
    expanding_window_folds,
)
from .quality import Membership
from .research import SignalObservation

TICKERS = ("AAA", "BBB", "CCC")
START = date(2025, 1, 3)
PERIODS = 8


def _snapshot() -> tuple[bytes, bytes, str]:
    price_lines = ["ticker,observed_on,open,high,low,close,volume"]
    for index in range(PERIODS):
        observed_on = START + timedelta(days=7 * index)
        for ticker_index, ticker in enumerate((*TICKERS, "SPY")):
            close = 100 + ticker_index * 10 + index
            price_lines.append(
                f"{ticker},{observed_on.isoformat()},{close - 1},{close + 1},"
                f"{close - 2},{close},{1000 + index * 10 + ticker_index}"
            )
    price_bytes = ("\n".join(price_lines) + "\n").encode()
    membership_bytes = (
        "ticker,valid_from,valid_to\n"
        + "\n".join(f"{ticker},{START.isoformat()},OPEN" for ticker in TICKERS)
        + "\n"
    ).encode()
    descriptor = json.dumps(
        {
            "corporate_action_policy": "total_return_adjusted",
            "currency": "USD",
            "exchange_calendar": "synthetic-weekly",
            "fixture_id": "dow30-screener-release-demo-v1",
            "generated_at": datetime(2025, 1, 1, tzinfo=UTC).isoformat(),
            "generation_method": "Deterministic project-authored synthetic values.",
            "license": "MIT",
            "memberships_sha256": sha256(membership_bytes).hexdigest(),
            "prices_sha256": sha256(price_bytes).hexdigest(),
            "schema_version": 1,
            "source_note": "Synthetic test fixture; not Dow constituents or market prices.",
        },
        sort_keys=True,
    )
    return price_bytes, membership_bytes, descriptor


def _evaluation_periods() -> tuple[EvaluationPeriod, ...]:
    outcomes = (
        (0.020, 0.010, -0.005, 0.006),
        (0.012, 0.018, -0.004, 0.005),
        (0.025, -0.002, 0.009, 0.004),
        (-0.010, 0.014, 0.022, -0.003),
        (0.017, 0.008, -0.006, 0.004),
        (0.006, 0.021, 0.002, 0.007),
        (-0.004, 0.011, 0.019, 0.001),
        (0.014, -0.005, 0.010, 0.003),
    )
    periods: list[EvaluationPeriod] = []
    for index, (aaa, bbb, ccc, benchmark) in enumerate(outcomes):
        observed_on = START + timedelta(days=7 * index)
        periods.append(
            EvaluationPeriod(
                observed_on=observed_on,
                signals=(
                    SignalObservation("AAA", observed_on, 3.0, aaa),
                    SignalObservation("BBB", observed_on, 2.0, bbb),
                    SignalObservation("CCC", observed_on, 1.0, ccc),
                ),
                benchmark_return=benchmark,
            )
        )
    return tuple(periods)


def _observations_digest(periods: tuple[EvaluationPeriod, ...]) -> str:
    payload = [
        {
            "benchmark_return": period.benchmark_return,
            "observed_on": period.observed_on.isoformat(),
            "signals": [
                {
                    "forward_return": signal.forward_return,
                    "score": signal.score,
                    "ticker": signal.ticker,
                }
                for signal in period.signals
            ],
        }
        for period in periods
    ]
    canonical = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    return sha256(canonical).hexdigest()


def render_demo_report() -> str:
    price_bytes, membership_bytes, descriptor = _snapshot()
    quality = build_quality_report(price_bytes, membership_bytes, descriptor)
    periods = _evaluation_periods()
    memberships = [Membership(ticker, START) for ticker in TICKERS]
    disclosure = UniverseDisclosure(
        universe_kind=UniverseKind.SYNTHETIC,
        includes_exited_members=False,
        exit_return_policy=ExitReturnPolicy.NOT_APPLICABLE,
        symbol_change_policy=SymbolChangePolicy.NOT_APPLICABLE,
        missing_return_policy=MissingReturnPolicy.FAIL_CLOSED,
        methodology_note=(
            "Project-authored synthetic universe; no historical constituents, exits, or symbols."
        ),
    )
    folds = expanding_window_folds(
        tuple(period.observed_on for period in periods),
        minimum_train_periods=4,
        test_periods=2,
    )
    return build_walk_forward_report(
        periods,
        memberships,
        quality,
        disclosure,
        folds,
        observations_sha256=_observations_digest(periods),
        candidate_top_k=(1, 2, 3),
        transaction_cost_scenarios_bps=(0.0, 10.0, 25.0),
        confidence_level=0.90,
        bootstrap_samples=500,
        seed=2026,
    ).to_json()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Write JSON to this path instead of stdout.")
    args = parser.parse_args(argv)
    output = cast(Path | None, args.output)
    report = render_demo_report()
    if output is None:
        print(report, end="")
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(report, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
