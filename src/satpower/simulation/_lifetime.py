"""Long-duration lifetime simulation with capacity fade between segments."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from satpower.simulation._engine import Simulation
from satpower.battery._aging import AgingModel


@dataclass
class LifetimeResults:
    """Results from a multi-segment lifetime simulation."""

    segment_years: list[float] = field(default_factory=list)
    capacity_remaining: list[float] = field(default_factory=list)
    min_soc_per_segment: list[float] = field(default_factory=list)
    worst_dod_per_segment: list[float] = field(default_factory=list)


class LifetimeSimulation:
    """Long-duration simulation with capacity fade between segments.

    Avoids adding aging to the ODE (timescale mismatch: aging = months,
    ODE = seconds). Instead, runs short simulation segments and updates
    battery capacity between them.
    """

    def __init__(self, simulation: Simulation, aging_model: AgingModel):
        self._simulation = simulation
        self._aging_model = aging_model

    def run(
        self,
        duration_years: float,
        update_interval_orbits: int = 100,
        orbits_per_segment: int = 3,
    ) -> LifetimeResults:
        """Run lifetime simulation.

        Parameters
        ----------
        duration_years : Total mission duration in years.
        update_interval_orbits : How often to re-evaluate aging (in orbits).
        orbits_per_segment : Number of orbits per simulation segment.
        """
        orbit_period_s = self._simulation._orbit.period
        orbits_per_year = 365.25 * 86400.0 / orbit_period_s
        total_orbits = duration_years * orbits_per_year

        results = LifetimeResults()
        elapsed_orbits = 0.0
        elapsed_years = 0.0

        while elapsed_orbits < total_orbits:
            # Run a short simulation segment
            seg_results = self._simulation.run(
                duration_orbits=orbits_per_segment, dt_max=60.0
            )

            # Record metrics
            results.segment_years.append(elapsed_years)
            results.min_soc_per_segment.append(float(np.min(seg_results.soc)))
            results.worst_dod_per_segment.append(seg_results.worst_case_dod)

            # Update aging
            elapsed_orbits += update_interval_orbits
            elapsed_years = elapsed_orbits / orbits_per_year
            n_cycles = int(elapsed_orbits)
            avg_dod = seg_results.worst_case_dod

            cap_remaining = self._aging_model.capacity_remaining(
                years=elapsed_years,
                n_cycles=n_cycles,
                avg_dod=avg_dod,
            )
            results.capacity_remaining.append(cap_remaining)

        return results
