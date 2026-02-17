"""Tests for EPSBoard class."""

import pytest

from satpower.regulation._eps_board import EPSBoard
from satpower.regulation._bus import PowerBus


class TestEPSBoardFromDatasheet:
    def test_load_gomspace_p31u(self):
        eps = EPSBoard.from_datasheet("gomspace_p31u")
        assert eps.name == "GomSpace P31u"
        assert eps.bus_voltage == 3.3
        assert eps.mppt_efficiency == 0.97
        assert eps.converter_efficiency == 0.92
        assert eps.num_solar_inputs == 6

    def test_load_clydespace(self):
        eps = EPSBoard.from_datasheet("clydespace_3g_eps")
        assert eps.name == "Clyde Space 3rd Gen EPS"
        assert eps.bus_voltage == 5.0
        assert eps.num_solar_inputs == 7

    def test_load_endurosat(self):
        eps = EPSBoard.from_datasheet("endurosat_eps_i_plus")
        assert eps.bus_voltage == 3.3
        assert eps.mppt_efficiency == 0.96

    def test_load_isis(self):
        eps = EPSBoard.from_datasheet("isis_ieps")
        assert eps.bus_voltage == 3.3

    def test_unknown_raises(self):
        with pytest.raises(FileNotFoundError):
            EPSBoard.from_datasheet("nonexistent_eps")


class TestEPSBoardProperties:
    @pytest.fixture
    def eps(self):
        return EPSBoard.from_datasheet("gomspace_p31u")

    def test_bus_is_power_bus(self, eps):
        assert isinstance(eps.bus, PowerBus)

    def test_bus_voltage_matches(self, eps):
        assert eps.bus.bus_voltage == eps.bus_voltage

    def test_converter_efficiency_matches(self, eps):
        assert eps.bus.converter_efficiency == eps.converter_efficiency

    def test_bus_voltage_range(self, eps):
        low, high = eps.bus_voltage_range
        assert low == 3.0
        assert high == 5.0

    def test_max_solar_input(self, eps):
        assert eps.max_solar_input_v == 6.5
        assert eps.max_solar_input_a == 1.5

    def test_battery_config(self, eps):
        assert eps.battery_config == "2S1P"

    def test_mass(self, eps):
        assert eps.mass_g == 75.0


class TestEPSBoardInSimulation:
    def test_simulation_with_eps_board(self):
        from satpower.orbit._propagator import Orbit
        from satpower.solar._panel import SolarPanel
        from satpower.battery._pack import BatteryPack
        from satpower.loads._profile import LoadProfile
        from satpower.simulation._engine import Simulation

        orbit = Orbit.circular(altitude_km=550, inclination_deg=97.6)
        panels = SolarPanel.cubesat_body("3U", cell_type="azur_3g30c")
        battery = BatteryPack.from_cell("panasonic_ncr18650b", config="2S2P")
        loads = LoadProfile()
        loads.add_mode("idle", power_w=2.0)

        eps = EPSBoard.from_datasheet("gomspace_p31u")
        sim = Simulation(orbit, panels, battery, loads, eps_board=eps)
        results = sim.run(duration_orbits=1, dt_max=60)

        assert len(results.time) > 10
        assert results.soc[-1] > 0

    def test_eps_board_overrides_bus_and_mppt(self):
        from satpower.orbit._propagator import Orbit
        from satpower.solar._panel import SolarPanel
        from satpower.battery._pack import BatteryPack
        from satpower.loads._profile import LoadProfile
        from satpower.simulation._engine import Simulation

        orbit = Orbit.circular(altitude_km=550, inclination_deg=97.6)
        panels = SolarPanel.cubesat_body("3U", cell_type="azur_3g30c")
        battery = BatteryPack.from_cell("panasonic_ncr18650b", config="2S2P")
        loads = LoadProfile()
        loads.add_mode("idle", power_w=2.0)

        eps = EPSBoard.from_datasheet("gomspace_p31u")
        # Provide conflicting bus and mppt — eps_board should win
        custom_bus = PowerBus(bus_voltage=12.0)
        sim = Simulation(
            orbit, panels, battery, loads,
            bus=custom_bus,
            mppt_efficiency=0.50,
            eps_board=eps,
        )
        # Verify EPS board values were used
        assert sim._bus.bus_voltage == 3.3  # from EPS, not 12.0
        assert sim._mppt_efficiency == 0.97  # from EPS, not 0.50
