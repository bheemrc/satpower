"""Tests for power bus and converter."""

import pytest

from satpower.regulation._bus import PowerBus
from satpower.regulation._converter import DcDcConverter


class TestDcDcConverter:
    def test_output_power(self):
        conv = DcDcConverter(efficiency=0.90)
        assert abs(conv.output_power(10.0) - 9.0) < 0.01

    def test_input_power(self):
        conv = DcDcConverter(efficiency=0.90)
        assert abs(conv.input_power(9.0) - 10.0) < 0.01

    def test_invalid_efficiency(self):
        with pytest.raises(ValueError):
            DcDcConverter(efficiency=1.5)


class TestPowerBus:
    def test_discharge_current_positive(self):
        """When load exceeds solar, battery current should be positive (discharge)."""
        bus = PowerBus(converter=DcDcConverter(efficiency=0.92))
        current = bus.net_battery_current(
            solar_power=0.0, load_power=4.5, battery_voltage=8.4
        )
        assert current > 0
        # 4.5W load / 0.92 efficiency / 8.4V ≈ 0.58A
        assert abs(current - 4.5 / 0.92 / 8.4) < 0.01

    def test_charge_current_negative(self):
        """When solar exceeds load, battery current should be negative (charging)."""
        bus = PowerBus(converter=DcDcConverter(efficiency=0.92))
        current = bus.net_battery_current(
            solar_power=10.0, load_power=3.0, battery_voltage=8.4
        )
        assert current < 0

    def test_zero_battery_voltage(self):
        bus = PowerBus()
        current = bus.net_battery_current(10.0, 5.0, 0.0)
        assert current == 0.0

    def test_discharge_efficiency_applied(self):
        """Discharge should require more power from battery due to converter loss."""
        bus = PowerBus(converter=DcDcConverter(efficiency=0.90))
        current = bus.net_battery_current(
            solar_power=0.0, load_power=9.0, battery_voltage=10.0
        )
        # Battery must supply 9.0 / 0.90 = 10.0 W → 10.0 / 10.0 V = 1.0 A
        assert abs(current - 1.0) < 0.01

    def test_charge_efficiency_applied(self):
        """Charging should store less energy due to converter loss."""
        bus = PowerBus(converter=DcDcConverter(efficiency=0.90))
        current = bus.net_battery_current(
            solar_power=10.0, load_power=0.0, battery_voltage=10.0
        )
        # Solar to bus: 10 * 0.9 = 9W surplus
        # Charge: -9 * 0.9 = -8.1W stored → -8.1 / 10V = -0.81A
        assert abs(current - (-0.81)) < 0.01


class TestCoulombCounter:
    def test_discharge_gives_negative_dsoc(self):
        from satpower.battery._soc import CoulombCounter
        # Positive current = discharge → SoC should decrease
        dsoc = CoulombCounter.dsoc_dt(current=1.0, capacity_ah=3.35)
        assert dsoc < 0

    def test_charge_gives_positive_dsoc(self):
        from satpower.battery._soc import CoulombCounter
        # Negative current = charge → SoC should increase
        dsoc = CoulombCounter.dsoc_dt(current=-1.0, capacity_ah=3.35)
        assert dsoc > 0
