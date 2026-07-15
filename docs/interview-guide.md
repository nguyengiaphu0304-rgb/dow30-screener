# Design and trade-offs

The main design choice is to make temporal validity a domain concept rather than a DataFrame
convention. Inclusive membership intervals are validated for overlap and queried at the signal
date. Forward outcomes never participate in ranking. Requiring a benchmark and explicit cost makes
failure visible instead of silently improving a result. The small standard-library core is less
convenient than vendor-coupled analysis, but easier to audit, type-check and reproduce.
