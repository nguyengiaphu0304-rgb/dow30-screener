# ADR 001: Fail-closed, standard-library research core

Status: accepted.

The original repository coupled downloads, mutable SQLite state and analysis. It could silently
substitute a stock for a missing benchmark and backproject current membership. The verified core
therefore has no runtime dependency or network access, accepts explicit provenance and intervals,
and rejects incomplete inputs. This adds preparation work but prevents plausible-looking results
from being produced from data whose timing or meaning is unknown.
