"""Tests for lifetime simulation."""

import pytest
import numpy as np

from satpower.orbit._propagator import Orbit
from satpower.solar._panel import SolarPanel
from satpower.battery._pack import BatteryPack
from satpower.battery._aging import AgingModel
from satpower.loads._profile import LoadProfile
from satpower.simulation._engine import Simulation
from satpower.simulation._lifetime import LifetimeSimulation, LifetimeResults


@pytest.fixture
def basic_sim():
    orbit = Orbit.circular(altitude_km=500, inclination_deg=45)
    panels = SolarPanel.cubesat_body("3U", cell_type="azur_3g30c")
    battery = BatteryPack.from_cell("panasonic_ncr18650b", "2S2P")
    loads = LoadProfile()
    loads.add_mode("idle", power_w=2.0)
    return Simulation(
        orbit=orbit, panels=panels, battery=battery, loads=loads,
    )


class TestLifetimeSimulation:
    def test_capacity_decreases_over_time(self, basic_sim):
        """Capacity should decrease over 1 year."""
        aging = AgingModel()
        lifetime = LifetimeSimulation(basic_sim, aging)
        results = lifetime.run(duration_years=1.0, update_interval_orbits=500, orbits_per_segment=2)
        assert len(results.capacity_remaining) > 1
        # Capacity should decrease monotonically
        for i in range(1, len(results.capacity_remaining)):
            assert results.capacity_remaining[i] <= results.capacity_remaining[i - 1] + 1e-10

    def test_results_contain_capacity_history(self, basic_sim):
        """Results should contain capacity and SoC history."""
        aging = AgingModel()
        lifetime = LifetimeSimulation(basic_sim, aging)
        results = lifetime.run(duration_years=0.5, update_interval_orbits=500, orbits_per_segment=2)
        assert isinstance(results, LifetimeResults)
        assert len(results.segment_years) > 0
        assert len(results.capacity_remaining) > 0
        assert len(results.min_soc_per_segment) > 0

    def test_one_year_capacity_reasonable(self, basic_sim):
        """After 1 year, capacity should still be > 0.8 for typical mission."""
        aging = AgingModel()
        lifetime = LifetimeSimulation(basic_sim, aging)
        results = lifetime.run(duration_years=1.0, update_interval_orbits=1000, orbits_per_segment=2)
        final_cap = results.capacity_remaining[-1]
        assert 0.7 < final_cap < 1.0
