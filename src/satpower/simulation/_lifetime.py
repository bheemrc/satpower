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

        if update_interval_orbits <= 0:
            raise ValueError("update_interval_orbits must be > 0")
        if orbits_per_segment <= 0:
            raise ValueError("orbits_per_segment must be > 0")

        # Save original state so we can restore after run
        original_initial_soc = self._simulation._initial_soc
        original_capacity_scale = self._simulation._capacity_scale

        results = LifetimeResults()
        elapsed_orbits = 0.0
        elapsed_years = 0.0
        cumulative_efc = 0.0  # equivalent full cycles
        current_capacity_scale = 1.0
        next_initial_soc = original_initial_soc

        try:
            while elapsed_orbits < total_orbits:
                represented_orbits = min(update_interval_orbits, total_orbits - elapsed_orbits)
                segment_orbits = min(orbits_per_segment, represented_orbits)
                self._simulation._initial_soc = float(np.clip(next_initial_soc, 0.0, 1.0))
                self._simulation.set_capacity_scale(current_capacity_scale)

                seg_results = self._simulation.run(
                    duration_orbits=segment_orbits, dt_max=60.0
                )

                results.segment_years.append(elapsed_years)
                results.min_soc_per_segment.append(float(np.min(seg_results.soc)))
                results.worst_dod_per_segment.append(seg_results.worst_case_dod)

                # Compute equivalent full cycles using peak-to-trough depth.
                # This is more robust than summing np.diff (which amplifies
                # solver noise) and better represents actual cycle loading.
                dod = seg_results.worst_case_dod
                cycles_per_orbit = 1.0  # one charge/discharge cycle per orbit
                cumulative_efc += dod * cycles_per_orbit * represented_orbits

                elapsed_orbits += represented_orbits
                elapsed_years = elapsed_orbits / orbits_per_year
                next_initial_soc = float(seg_results.soc[-1])

                cap_remaining = self._aging_model.capacity_remaining(
                    years=elapsed_years,
                    n_cycles=int(round(cumulative_efc)),
                    avg_dod=dod,
                )
                current_capacity_scale = cap_remaining
                results.capacity_remaining.append(cap_remaining)
        finally:
            # Restore original simulation state
            self._simulation._initial_soc = original_initial_soc
            self._simulation._capacity_scale = original_capacity_scale

        return results
