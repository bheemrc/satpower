"""Monte Carlo wrapper for lifetime analysis (Phase 2+ full implementation)."""

from __future__ import annotations


class MonteCarloRunner:
    """Monte Carlo simulation for mission lifetime analysis.

    Phase 1 stub — Phase 2 will implement parameter sampling and
    multi-run aggregation.
    """

    def __init__(self, n_runs: int = 100, seed: int = 42):
        self._n_runs = n_runs
        self._seed = seed
