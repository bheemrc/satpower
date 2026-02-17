"""Tests for battery pack configurations."""

import pytest

from satpower.battery._pack import BatteryPack, _parse_config


class TestConfigParsing:
    def test_2s2p(self):
        ns, np_ = _parse_config("2S2P")
        assert ns == 2
        assert np_ == 2

    def test_1s1p(self):
        ns, np_ = _parse_config("1S1P")
        assert ns == 1
        assert np_ == 1

    def test_invalid_config(self):
        with pytest.raises(ValueError):
            _parse_config("2x2")


class TestBatteryPack:
    def test_from_cell_creation(self):
        pack = BatteryPack.from_cell("panasonic_ncr18650b", "2S2P")
        assert pack.n_series == 2
        assert pack.n_parallel == 2

    def test_capacity_scaling(self, battery_2s2p):
        # 2P doubles capacity
        assert abs(battery_2s2p.capacity_ah - 3.35 * 2) < 0.01

    def test_voltage_scaling(self, battery_2s2p):
        # 2S doubles nominal voltage
        assert abs(battery_2s2p.nominal_voltage - 3.6 * 2) < 0.01

    def test_energy(self, battery_2s2p):
        expected = 3.35 * 2 * 3.6 * 2  # Ah * V
        assert abs(battery_2s2p.energy_wh - expected) < 0.1

    def test_terminal_voltage_no_load(self, battery_2s2p):
        v = battery_2s2p.terminal_voltage(1.0, current=0.0)
        # Should be 2 * OCV(1.0) = 2 * 4.20 = 8.40 V
        assert abs(v - 8.40) < 0.05

    def test_voltage_limits(self, battery_2s2p):
        assert abs(battery_2s2p.max_voltage - 8.4) < 0.01
        assert abs(battery_2s2p.min_voltage - 5.0) < 0.01
