"""Monte Carlo wrapper for lifetime analysis."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import numpy as np

from satpower.simulation._lifetime import LifetimeResults, LifetimeSimulation


@dataclass
class MonteCarloResults:
    """Aggregate results for a Monte Carlo lifetime campaign."""

    runs: list[LifetimeResults] = field(default_factory=list)
    final_capacity: np.ndarray = field(default_factory=lambda: np.array([], dtype=float))
    p10_capacity: float = 0.0
    p50_capacity: float = 0.0
    p90_capacity: float = 0.0


class MonteCarloRunner:
    """Monte Carlo simulation for mission lifetime analysis.

    The caller provides a factory that returns a fully configured
    `LifetimeSimulation` per run, allowing uncertainty sampling in
    battery aging parameters, load scaling, temperatures, etc.
    """

    def __init__(self, n_runs: int = 100, seed: int = 42):
        if n_runs <= 0:
            raise ValueError("n_runs must be > 0")
        self._n_runs = n_runs
        self._rng = np.random.default_rng(seed)

    @property
    def rng(self) -> np.random.Generator:
        return self._rng

    def run(
        self,
        simulation_factory: Callable[[np.random.Generator, int], LifetimeSimulation],
        *,
        duration_years: float,
        update_interval_orbits: int = 100,
        orbits_per_segment: int = 3,
    ) -> MonteCarloResults:
        """Run multiple lifetime simulations and return percentile summary."""
        runs: list[LifetimeResults] = []
        final_capacity = np.zeros(self._n_runs, dtype=float)

        for idx in range(self._n_runs):
            lifetime_sim = simulation_factory(self._rng, idx)
            run = lifetime_sim.run(
                duration_years=duration_years,
                update_interval_orbits=update_interval_orbits,
                orbits_per_segment=orbits_per_segment,
            )
            runs.append(run)
            final_capacity[idx] = run.capacity_remaining[-1] if run.capacity_remaining else 1.0

        return MonteCarloResults(
            runs=runs,
            final_capacity=final_capacity,
            p10_capacity=float(np.percentile(final_capacity, 10)),
            p50_capacity=float(np.percentile(final_capacity, 50)),
            p90_capacity=float(np.percentile(final_capacity, 90)),
        )
