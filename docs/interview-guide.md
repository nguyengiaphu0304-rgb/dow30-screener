# Design and trade-offs

The main design choice is to make temporal validity a domain concept rather than a DataFrame
convention. Inclusive membership intervals are validated for overlap and queried at the signal
date. Forward outcomes never participate in ranking. Requiring a benchmark and explicit cost makes
failure visible instead of silently improving a result. The small standard-library core is less
convenient than vendor-coupled analysis, but easier to audit, type-check and reproduce.

Walk-forward evaluation makes the information boundary inspectable: training outcomes may choose
`top_k`, while test outcomes are unavailable until evaluation. Expanding windows use all prior
observations; non-overlapping test windows prevent double counting. Predeclared cost scenarios are
reported together rather than selecting the most flattering result. A seeded bootstrap is useful
for regression evidence but does not capture time-series dependence.
