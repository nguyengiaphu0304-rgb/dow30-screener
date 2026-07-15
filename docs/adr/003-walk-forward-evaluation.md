# ADR 003: Expanding-window evaluation with predeclared sensitivity scenarios

## Status

Accepted.

## Decision

Evaluation uses explicit expanding-window folds. Candidate portfolio sizes are selected only from
each fold's training dates, with the smallest `top_k` winning an equal-score tie. Test dates are
chronologically later and cannot overlap. Every test observation reports the selected portfolio,
the required benchmark, and an equal-weight eligible-universe baseline.

Transaction-cost scenarios are declared before evaluation and all are emitted. The report never
selects the most favorable test scenario. A seeded non-parametric bootstrap summarizes uncertainty
in mean out-of-sample benchmark-relative returns. Report lineage includes the fixture ID and both
validated input digests.

## Consequences

The engine is deterministic, offline and auditable. It prevents a common parameter-selection leak,
but it cannot fix incomplete universes or missing delisting returns. Bootstrap observations are
treated as exchangeable and do not model serial dependence. Synthetic fixtures verify behavior;
they are not market evidence or financial advice.
