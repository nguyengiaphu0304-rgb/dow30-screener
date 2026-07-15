# Corporate-action and market-data policy

Every dataset must declare exactly one price policy: `raw`, `split_adjusted`, or
`total_return_adjusted`. A report never infers this policy from values and datasets with different
policies must not be combined silently.

The committed quality fixture is raw, synthetic, USD-denominated data on a synthetic three-day
calendar. It contains no actual split, dividend, delisting, constituent, or security history and
cannot support a return claim. Future real-data adapters must document vendor adjustment semantics,
effective timestamps, correction behavior, currencies, calendars, symbol changes, delistings and
whether distributions are reinvested. Unknown semantics fail the trust boundary rather than being
treated as zero corporate-action impact.
