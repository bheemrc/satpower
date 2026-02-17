"""Integration tests for simulation engine — full orbit simulation."""

import numpy as np
import pytest

from satpower.orbit._propagator import Orbit
from satpower.solar._panel import SolarPanel
from satpower.battery._pack import BatteryPack
from satpower.loads._profile import LoadProfile
from satpower.simulation._engine import Simulation


@pytest.fixture
def basic_sim():
    """A basic 3U CubeSat simulation setup."""
    orbit = Orbit.circular(altitude_km=550, inclination_deg=97.6)
    panels = SolarPanel.cubesat_body("3U", cell_type="azur_3g30c")
    battery = BatteryPack.from_cell("panasonic_ncr18650b", config="2S2P")
    loads = LoadProfile()
    loads.add_mode("idle", power_w=2.0)
    loads.add_mode("comms", power_w=8.0, duty_cycle=0.15)
    loads.add_mode("payload", power_w=5.0, duty_cycle=0.30)
    return Simulation(orbit, panels, battery, loads)


class TestSimulationRun:
    def test_runs_one_orbit(self, basic_sim):
        results = basic_sim.run(duration_orbits=1, dt_max=60)
        assert len(results.time) > 10
        assert results.time[-1] > 0

    def test_soc_stays_bounded(self, basic_sim):
        results = basic_sim.run(duration_orbits=3, dt_max=60)
        assert np.all(results.soc >= 0.0)
        assert np.all(results.soc <= 1.0)

    def test_power_generated_nonnegative(self, basic_sim):
        results = basic_sim.run(duration_orbits=2, dt_max=60)
        assert np.all(results.power_generated >= 0.0)

    def test_eclipse_exists(self, basic_sim):
        results = basic_sim.run(duration_orbits=2, dt_max=60)
        # Should have both sunlit and eclipse periods
        assert np.any(results.eclipse)
        assert np.any(~results.eclipse)

    def test_zero_power_in_eclipse(self, basic_sim):
        results = basic_sim.run(duration_orbits=2, dt_max=60)
        eclipse_mask = results.eclipse
        if np.any(eclipse_mask):
            eclipse_power = results.power_generated[eclipse_mask]
            assert np.allclose(eclipse_power, 0.0, atol=0.01)

    def test_soc_decreases_in_eclipse(self, basic_sim):
        """SoC should generally decrease during eclipse (no generation)."""
        results = basic_sim.run(duration_orbits=2, dt_max=30)
        # Find a sustained eclipse region
        eclipse_runs = []
        in_run = False
        start = 0
        for i in range(len(results.eclipse)):
            if results.eclipse[i] and not in_run:
                start = i
                in_run = True
            elif not results.eclipse[i] and in_run:
                if i - start > 5:
                    eclipse_runs.append((start, i))
                in_run = False

        if eclipse_runs:
            s, e = eclipse_runs[0]
            # SoC at end of eclipse should be less than or equal to at start
            # (first eclipse may start before any significant discharge)
            assert results.soc[e - 1] <= results.soc[s]

    def test_duration_seconds(self, basic_sim):
        results = basic_sim.run(duration_s=3600, dt_max=60)
        assert abs(results.time[-1] - 3600) < 60


class TestSimulationResults:
    def test_summary_keys(self, basic_sim):
        results = basic_sim.run(duration_orbits=1, dt_max=60)
        summary = results.summary()
        assert "min_soc" in summary
        assert "worst_case_dod" in summary
        assert "power_margin_w" in summary
        assert "eclipse_fraction" in summary

    def test_worst_case_dod_reasonable(self, basic_sim):
        results = basic_sim.run(duration_orbits=3, dt_max=60)
        # For a well-designed 3U, DoD should be < 50%
        assert results.worst_case_dod < 0.5

    def test_eclipse_fraction_reasonable(self, basic_sim):
        results = basic_sim.run(duration_orbits=3, dt_max=60)
        # LEO eclipse fraction is typically 30-40%
        assert 0.1 < results.eclipse_fraction < 0.5

    def test_time_conversions(self, basic_sim):
        results = basic_sim.run(duration_orbits=1, dt_max=60)
        assert results.time_minutes[-1] == results.time[-1] / 60.0
        assert results.time_hours[-1] == results.time[-1] / 3600.0
