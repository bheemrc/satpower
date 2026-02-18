"""Tests for thermal model."""

import numpy as np
import pytest

from satpower.thermal._model import ThermalModel, ThermalConfig, STEFAN_BOLTZMANN


class TestThermalConfig:
    def test_defaults(self):
        cfg = ThermalConfig()
        assert cfg.panel_thermal_mass_j_per_k == 450.0
        assert cfg.battery_thermal_mass_j_per_k == 95.0
        assert cfg.initial_panel_temp_k == 301.15


class TestPanelThermal:
    def test_panel_equilibrium_sunlit(self):
        """Panel in sunlight should reach equilibrium between 280-360K."""
        model = ThermalModel()
        # Try various temperatures — equilibrium is where dT/dt ≈ 0
        # Solar absorbed ~5W on small panel, albedo ~100 W/m², Earth IR ~200 W/m²
        area = 0.06
        # At equilibrium, absorbed ≈ radiated
        # Find temp where derivative is ~0 (iterate manually)
        t_eq = 300.0
        for _ in range(100):
            dt = model.panel_derivatives(t_eq, 3.0, 100.0, 200.0, area)
            t_eq += dt * 10.0  # step forward
        assert 250 < t_eq < 400

    def test_panel_cools_in_eclipse(self):
        """Panel with no solar input should cool down."""
        model = ThermalModel()
        # No solar, no albedo → should cool
        dt = model.panel_derivatives(
            t_panel=350.0,
            solar_absorbed_w=0.0,
            albedo_flux_w_m2=0.0,
            earth_ir_flux_w_m2=200.0,
            panel_area_m2=0.06,
        )
        # At 350K with only Earth IR, radiation exceeds input
        assert dt < 0

    def test_panel_heats_in_sunlight(self):
        """Cold panel with strong solar input should heat up."""
        model = ThermalModel()
        dt = model.panel_derivatives(
            t_panel=200.0,
            solar_absorbed_w=5.0,
            albedo_flux_w_m2=100.0,
            earth_ir_flux_w_m2=200.0,
            panel_area_m2=0.06,
        )
        assert dt > 0


class TestBatteryThermal:
    def test_battery_joule_heating(self):
        """Joule heat should increase battery temperature."""
        model = ThermalModel()
        dt = model.battery_derivatives(
            t_battery=293.15,
            joule_heat_w=0.5,
        )
        assert dt > 0

    def test_battery_equilibrium(self):
        """Battery should reach thermal equilibrium."""
        model = ThermalModel()
        t_eq = 298.15
        for _ in range(200):
            dt = model.battery_derivatives(t_eq, joule_heat_w=0.1)
            t_eq += dt * 10.0
        # Should settle near spacecraft interior temp (293.15K) + a bit for Joule heat
        assert 290 < t_eq < 350

    def test_battery_bounded_temps(self):
        """Battery temp should stay in physically reasonable range during simulation."""
        model = ThermalModel()
        t = 298.15
        for _ in range(10000):
            dt_val = model.battery_derivatives(t, joule_heat_w=0.2)
            t += dt_val * 1.0
            # Should never exceed extreme bounds
            assert 100 < t < 500


class TestThermalDisabled:
    def test_thermal_disabled_uses_defaults(self):
        """When thermal is None, simulation should use default temps."""
        from satpower.simulation._engine import _DEFAULT_PANEL_TEMP_K, _DEFAULT_BATTERY_TEMP_K
        assert _DEFAULT_PANEL_TEMP_K == 301.15
        assert _DEFAULT_BATTERY_TEMP_K == 298.15


class TestThermalIntegration:
    def test_sim_with_thermal_returns_temperatures(self):
        """Simulation with thermal model should return temperature arrays."""
        from satpower.orbit._propagator import Orbit
        from satpower.solar._panel import SolarPanel
        from satpower.battery._pack import BatteryPack
        from satpower.loads._profile import LoadProfile
        from satpower.simulation._engine import Simulation

        orbit = Orbit.circular(altitude_km=500, inclination_deg=45)
        panels = SolarPanel.cubesat_body("3U", cell_type="azur_3g30c")
        battery = BatteryPack.from_cell("panasonic_ncr18650b", "2S2P")
        loads = LoadProfile()
        loads.add_mode("idle", power_w=2.0)

        thermal = ThermalModel(ThermalConfig(
            panel_area_m2=sum(p.area_m2 for p in panels),
        ))

        sim = Simulation(
            orbit=orbit,
            panels=panels,
            battery=battery,
            loads=loads,
            thermal_model=thermal,
        )
        results = sim.run(duration_orbits=1, dt_max=60.0)

        assert results.panel_temperature is not None
        assert results.battery_temperature is not None
        assert len(results.panel_temperature) == len(results.time)
        # Temperatures should be physically reasonable
        assert np.all(results.panel_temperature > 100)
        assert np.all(results.panel_temperature < 500)
        assert np.all(results.battery_temperature > 200)
        assert np.all(results.battery_temperature < 400)
