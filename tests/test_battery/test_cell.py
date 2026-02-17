"""Tests for battery cell model — validate voltage curves."""

import numpy as np
import pytest

from satpower.battery._cell import BatteryCell


class TestBatteryCellCreation:
    def test_from_datasheet(self):
        cell = BatteryCell.from_datasheet("panasonic_ncr18650b")
        assert cell.name == "Panasonic NCR18650B"
        assert abs(cell.capacity_ah - 3.35) < 0.01

    def test_sony_vtc6(self):
        cell = BatteryCell.from_datasheet("sony_vtc6")
        assert cell.name == "Sony VTC6"

    def test_unknown_cell_raises(self):
        with pytest.raises(FileNotFoundError):
            BatteryCell.from_datasheet("nonexistent_battery")


class TestOCV:
    def test_ocv_at_full_charge(self, ncr18650b):
        ocv = ncr18650b.ocv(1.0)
        assert abs(ocv - 4.20) < 0.01

    def test_ocv_at_empty(self, ncr18650b):
        ocv = ncr18650b.ocv(0.0)
        assert abs(ocv - 3.20) < 0.01

    def test_ocv_monotonically_increases(self, ncr18650b):
        socs = np.linspace(0, 1, 20)
        ocvs = [ncr18650b.ocv(s) for s in socs]
        for i in range(1, len(ocvs)):
            assert ocvs[i] >= ocvs[i - 1]


class TestTerminalVoltage:
    def test_no_load_equals_ocv(self, ncr18650b):
        """With zero current, terminal voltage should equal OCV."""
        for soc in [0.2, 0.5, 0.8, 1.0]:
            v = ncr18650b.terminal_voltage(soc, current=0.0)
            ocv = ncr18650b.ocv(soc)
            assert abs(v - ocv) < 0.001

    def test_discharge_drops_voltage(self, ncr18650b):
        v_no_load = ncr18650b.terminal_voltage(0.5, current=0.0)
        v_loaded = ncr18650b.terminal_voltage(0.5, current=1.0)
        assert v_loaded < v_no_load

    def test_charge_raises_voltage(self, ncr18650b):
        v_no_load = ncr18650b.terminal_voltage(0.5, current=0.0)
        v_charging = ncr18650b.terminal_voltage(0.5, current=-1.0)
        assert v_charging > v_no_load


class TestInternalResistance:
    def test_positive_at_room_temp(self, ncr18650b):
        r = ncr18650b.internal_resistance(0.5, 298.15)
        assert r > 0
        # Datasheet: R0 = 0.035 ohm
        assert abs(r - 0.035) < 0.01

    def test_increases_at_low_temp(self, ncr18650b):
        r_warm = ncr18650b.internal_resistance(0.5, 298.15)
        r_cold = ncr18650b.internal_resistance(0.5, 253.15)  # -20°C
        assert r_cold > r_warm


class TestDerivatives:
    def test_derivatives_shape(self, ncr18650b):
        dv1, dv2 = ncr18650b.derivatives(1.0, 0.0, 0.0)
        assert isinstance(dv1, float)
        assert isinstance(dv2, float)

    def test_charging_rc_dynamics(self, ncr18650b):
        # With current and zero initial RC voltage, RC should build up
        dv1, _ = ncr18650b.derivatives(1.0, 0.0)
        assert dv1 > 0  # RC voltage increases during discharge
