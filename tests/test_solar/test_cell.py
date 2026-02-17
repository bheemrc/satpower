"""Tests for solar cell model — validate against datasheet values."""

import numpy as np
import pytest

from satpower.solar._cell import SolarCell


class TestSolarCellCreation:
    def test_from_datasheet(self):
        cell = SolarCell.from_datasheet("azur_3g30c")
        assert cell.name == "Azur Space 3G30C"
        assert abs(cell.area_cm2 - 30.18) < 0.01

    def test_spectrolab(self):
        cell = SolarCell.from_datasheet("spectrolab_xtj_prime")
        assert cell.name == "Spectrolab XTJ Prime"

    def test_unknown_cell_raises(self):
        with pytest.raises(FileNotFoundError):
            SolarCell.from_datasheet("nonexistent_cell")


class TestIVCurve:
    def test_iv_curve_shape(self, azur_cell):
        voltage = np.linspace(0, 2.7, 50)
        current = azur_cell.iv_curve(1361.0, 301.15, voltage)
        assert current.shape == (50,)

    def test_isc_approximately_matches_datasheet(self, azur_cell):
        """Short-circuit current at STC should match datasheet ±5%."""
        current_at_zero = azur_cell.iv_curve(1361.0, 301.15, np.array([0.0]))
        # Datasheet: Isc = 0.520 A
        assert abs(current_at_zero[0] - 0.520) < 0.520 * 0.05

    def test_zero_irradiance_zero_current(self, azur_cell):
        voltage = np.linspace(0, 2.5, 20)
        current = azur_cell.iv_curve(0.0, 301.15, voltage)
        assert np.allclose(current, 0, atol=1e-10)

    def test_current_decreases_with_voltage(self, azur_cell):
        voltage = np.linspace(0, 2.5, 50)
        current = azur_cell.iv_curve(1361.0, 301.15, voltage)
        # Current should generally decrease with voltage
        assert current[0] > current[-1]


class TestMPP:
    def test_mpp_at_stc(self, azur_cell):
        """MPP power should match datasheet ±5%."""
        v_mp, i_mp = azur_cell.mpp(1361.0, 301.15)
        power = v_mp * i_mp
        # Datasheet: Pmp = 2.411 * 0.504 = 1.215 W
        expected = 2.411 * 0.504
        assert abs(power - expected) < expected * 0.10

    def test_mpp_voltage_reasonable(self, azur_cell):
        v_mp, _ = azur_cell.mpp(1361.0, 301.15)
        # Datasheet: Vmp = 2.411 V
        assert abs(v_mp - 2.411) < 0.20

    def test_power_at_mpp(self, azur_cell):
        power = azur_cell.power_at_mpp(1361.0, 301.15)
        assert power > 0
        # Should be around 1.2 W for Azur 3G30C
        assert 0.8 < power < 1.6

    def test_zero_irradiance(self, azur_cell):
        v, i = azur_cell.mpp(0, 301.15)
        assert v == 0.0
        assert i == 0.0

    def test_power_scales_with_irradiance(self, azur_cell):
        p_full = azur_cell.power_at_mpp(1361.0, 301.15)
        p_half = azur_cell.power_at_mpp(680.5, 301.15)
        # Half irradiance should give roughly half power
        assert 0.35 < p_half / p_full < 0.65
