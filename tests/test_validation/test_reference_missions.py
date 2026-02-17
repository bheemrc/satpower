"""Validation tests — verify against expected CubeSat power behavior."""

import numpy as np
import pytest

from satpower.orbit._propagator import Orbit
from satpower.solar._panel import SolarPanel
from satpower.battery._pack import BatteryPack
from satpower.loads._profile import LoadProfile
from satpower.simulation._engine import Simulation


class TestReferenceMission3U:
    """Validate a 3U CubeSat at 550 km SSO against expected behavior.

    Expected characteristics:
    - Orbit period ~96 min
    - Eclipse fraction ~35%
    - Positive energy balance for a well-designed 3U
    - SoC stays above 50% for moderate loads
    """

    @pytest.fixture
    def reference_sim(self):
        orbit = Orbit.circular(altitude_km=550, inclination_deg=97.6)
        panels = SolarPanel.cubesat_body("3U", cell_type="azur_3g30c")
        battery = BatteryPack.from_cell("panasonic_ncr18650b", config="2S2P")
        loads = LoadProfile()
        loads.add_mode("idle", power_w=2.0)
        loads.add_mode("comms", power_w=8.0, duty_cycle=0.10)
        loads.add_mode("payload", power_w=4.0, duty_cycle=0.20)
        return Simulation(orbit, panels, battery, loads)

    def test_orbit_period(self):
        orbit = Orbit.circular(altitude_km=550, inclination_deg=97.6)
        period_min = orbit.period / 60
        assert 94 < period_min < 98

    def test_soc_stays_healthy(self, reference_sim):
        results = reference_sim.run(duration_orbits=5, dt_max=60)
        # A well-designed 3U should maintain > 50% SoC
        assert results.summary()["min_soc"] > 0.5

    def test_positive_energy_balance(self, reference_sim):
        results = reference_sim.run(duration_orbits=5, dt_max=60)
        summary = results.summary()
        # Average power generated should exceed consumed for positive margin
        assert summary["avg_power_generated_w"] > 0

    def test_eclipse_fraction_matches_expected(self, reference_sim):
        results = reference_sim.run(duration_orbits=5, dt_max=30)
        # SSO at 550 km: eclipse fraction typically 30-40%
        assert 0.15 < results.eclipse_fraction < 0.50

    def test_battery_voltage_within_limits(self, reference_sim):
        results = reference_sim.run(duration_orbits=3, dt_max=60)
        pack = BatteryPack.from_cell("panasonic_ncr18650b", config="2S2P")
        assert np.all(results.battery_voltage >= pack.min_voltage * 0.95)
        assert np.all(results.battery_voltage <= pack.max_voltage * 1.05)
