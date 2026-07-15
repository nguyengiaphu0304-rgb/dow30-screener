# Survivorship, exits and symbol changes

Historical research is rejected unless its disclosure says that exited constituents are included,
exit returns are observed or explicitly imputed, symbol changes are mapped, and missing returns fail
closed. A present-day constituent list applied backward is not acceptable point-in-time evidence.

The bundled release demo uses a project-authored synthetic universe. Exits and symbol changes are
therefore marked `not_applicable`, not silently treated as zero. This proves validation and reporting
behavior only. It does not estimate Dow returns, survivorship bias, alpha or investment performance.

An adapter for real history would need to document constituent effective dates, removals, mergers,
bankruptcies, ticker and identifier mappings, final tradable prices, distributions, source license,
vendor corrections and retrieval lineage. Until such a source is available, the package must not
label any real-market result verified or survivorship-bias-free.
