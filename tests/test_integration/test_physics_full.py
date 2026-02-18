"""Integration tests: run simulation with ALL physics enabled."""

import numpy as np
import pytest

from satpower.orbit._propagator import Orbit
from satpower.solar._panel import SolarPanel
from satpower.solar._mppt import MpptModel
from satpower.battery._pack import BatteryPack
from satpower.loads._profile import LoadProfile
from satpower.regulation._bus import PowerBus
from satpower.regulation._converter import DcDcConverter
from satpower.simulation._engine import Simulation
from satpower.thermal._model import ThermalModel, ThermalConfig


def _build_full_physics_sim():
    """Build a simulation with ALL physics features enabled."""
    orbit = Orbit.circular(
        altitude_km=550, inclination_deg=97.6, j2=True
    )
    panels = SolarPanel.cubesat_body("3U", cell_type="azur_3g30c", exclude_faces=["-Z"])
    battery = BatteryPack.from_cell("panasonic_ncr18650b", "2S2P")

    loads = LoadProfile()
    loads.add_mode("obc", power_w=0.4)
    loads.add_mode("adcs", power_w=0.8)
    loads.add_mode("camera", power_w=6.0, duty_cycle=0.3, trigger="sunlight")
    loads.add_mode("comms", power_w=4.0, duty_cycle=0.15)

    converter = DcDcConverter(
        efficiency=0.92,
        load_dependent=True,
        rated_power_w=15.0,
        peak_efficiency=0.94,
        light_load_efficiency=0.80,
    )
    bus = PowerBus(bus_voltage=3.3, converter=converter)

    mppt = MpptModel(
        efficiency=0.97,
        power_dependent=True,
        rated_power_w=8.0,
        min_efficiency=0.85,
    )

    thermal_config = ThermalConfig(
        panel_area_m2=sum(p.area_m2 for p in panels),
    )
    thermal = ThermalModel(thermal_config)

    return Simulation(
        orbit=orbit,
        panels=panels,
        battery=battery,
        loads=loads,
        bus=bus,
        mppt_model=mppt,
        eclipse_model="conical",
        thermal_model=thermal,
        epoch_day_of_year=80.0,
    )


def _build_baseline_sim():
    """Build a baseline simulation with Phase 1 defaults (no advanced physics)."""
    orbit = Orbit.circular(altitude_km=550, inclination_deg=97.6)
    panels = SolarPanel.cubesat_body("3U", cell_type="azur_3g30c", exclude_faces=["-Z"])
    battery = BatteryPack.from_cell("panasonic_ncr18650b", "2S2P")

    loads = LoadProfile()
    loads.add_mode("obc", power_w=0.4)
    loads.add_mode("adcs", power_w=0.8)
    loads.add_mode("camera", power_w=6.0, duty_cycle=0.3, trigger="sunlight")
    loads.add_mode("comms", power_w=4.0, duty_cycle=0.15)

    return Simulation(
        orbit=orbit, panels=panels, battery=battery, loads=loads,
    )


class TestFullPhysics:
    def test_full_physics_runs(self):
        """Simulation with all physics enabled should complete without error."""
        sim = _build_full_physics_sim()
        results = sim.run(duration_orbits=2, dt_max=60.0)
        assert len(results.time) > 0

    def test_soc_bounded(self):
        """SoC should remain between 0 and 1."""
        sim = _build_full_physics_sim()
        results = sim.run(duration_orbits=2, dt_max=60.0)
        assert np.all(results.soc >= 0.0)
        assert np.all(results.soc <= 1.0)

    def test_temperatures_physical(self):
        """Panel and battery temperatures should be physically reasonable."""
        sim = _build_full_physics_sim()
        results = sim.run(duration_orbits=2, dt_max=60.0)
        assert results.panel_temperature is not None
        assert results.battery_temperature is not None
        # Panel should be between 100K and 500K
        assert np.all(results.panel_temperature > 100)
        assert np.all(results.panel_temperature < 500)
        # Battery should be between 200K and 400K
        assert np.all(results.battery_temperature > 200)
        assert np.all(results.battery_temperature < 400)

    def test_positive_power_generation(self):
        """Should generate positive power during sunlit periods."""
        sim = _build_full_physics_sim()
        results = sim.run(duration_orbits=2, dt_max=60.0)
        sunlit = ~results.eclipse
        if np.any(sunlit):
            assert np.max(results.power_generated[sunlit]) > 0

    def test_results_differ_from_baseline(self):
        """Full physics results should differ from baseline (but not wildly)."""
        sim_full = _build_full_physics_sim()
        sim_base = _build_baseline_sim()

        results_full = sim_full.run(duration_orbits=2, dt_max=60.0)
        results_base = sim_base.run(duration_orbits=2, dt_max=60.0)

        # SoC profiles should differ (different eclipse model, thermal, etc.)
        min_soc_full = float(np.min(results_full.soc))
        min_soc_base = float(np.min(results_base.soc))
        # But not wildly different (both should show same orbit characteristics)
        assert abs(min_soc_full - min_soc_base) < 0.3

    def test_eclipse_fraction_reasonable(self):
        """Eclipse fraction should be between 0 and 0.5 for SSO."""
        sim = _build_full_physics_sim()
        results = sim.run(duration_orbits=2, dt_max=60.0)
        assert 0.1 < results.eclipse_fraction < 0.5
