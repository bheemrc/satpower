"""Tests for DC-DC converter efficiency model."""

import pytest
import numpy as np

from satpower.regulation._converter import DcDcConverter


class TestConverterConstant:
    def test_default_efficiency(self):
        conv = DcDcConverter()
        assert conv.efficiency == 0.92

    def test_custom_efficiency(self):
        conv = DcDcConverter(efficiency=0.95)
        assert conv.efficiency == 0.95

    def test_efficiency_at_load_constant_mode(self):
        """In constant mode, efficiency_at_load returns the constant."""
        conv = DcDcConverter(efficiency=0.92)
        assert conv.efficiency_at_load(5.0) == 0.92
        assert conv.efficiency_at_load(20.0) == 0.92

    def test_invalid_efficiency_raises(self):
        with pytest.raises(ValueError):
            DcDcConverter(efficiency=0.0)


class TestConverterLoadDependent:
    def test_half_load_near_peak(self):
        """At ~50% rated load, efficiency should be near peak."""
        conv = DcDcConverter(
            load_dependent=True,
            rated_power_w=20.0,
            peak_efficiency=0.94,
            light_load_efficiency=0.80,
        )
        eff = conv.efficiency_at_load(10.0)
        assert eff > 0.92

    def test_low_load_lower_efficiency(self):
        """At very low load, efficiency should be lower."""
        conv = DcDcConverter(
            load_dependent=True,
            rated_power_w=20.0,
            peak_efficiency=0.94,
            light_load_efficiency=0.80,
        )
        eff = conv.efficiency_at_load(1.0)
        assert eff < 0.90

    def test_high_load_slight_droop(self):
        """At high load (>80%), efficiency should droop mildly."""
        conv = DcDcConverter(
            load_dependent=True,
            rated_power_w=20.0,
            peak_efficiency=0.94,
            light_load_efficiency=0.80,
        )
        eff_mid = conv.efficiency_at_load(10.0)
        eff_high = conv.efficiency_at_load(25.0)
        # High load should be slightly lower than mid load
        assert eff_high <= eff_mid

    def test_peak_mid_range(self):
        """Efficiency should peak somewhere in the mid-load range."""
        conv = DcDcConverter(
            load_dependent=True,
            rated_power_w=20.0,
            peak_efficiency=0.94,
            light_load_efficiency=0.80,
        )
        loads = np.linspace(0.5, 25, 100)
        effs = [conv.efficiency_at_load(p) for p in loads]
        peak_idx = np.argmax(effs)
        peak_load = loads[peak_idx]
        # Peak should be roughly between 30-80% of rated power
        assert 6.0 < peak_load < 20.0

    def test_zero_load(self):
        """At zero load, efficiency should be at minimum."""
        conv = DcDcConverter(
            load_dependent=True,
            rated_power_w=20.0,
            peak_efficiency=0.94,
            light_load_efficiency=0.80,
        )
        eff = conv.efficiency_at_load(0.0)
        assert eff == 0.80

    def test_output_power(self):
        conv = DcDcConverter(efficiency=0.90)
        assert abs(conv.output_power(10.0) - 9.0) < 0.01

    def test_input_power(self):
        conv = DcDcConverter(efficiency=0.90)
        assert abs(conv.input_power(9.0) - 10.0) < 0.01
