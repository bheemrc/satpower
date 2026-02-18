"""Tests for MPPT efficiency model."""

import pytest
import numpy as np

from satpower.solar._mppt import MpptModel


class TestMpptConstant:
    def test_default_efficiency(self):
        mppt = MpptModel()
        assert mppt.efficiency == 0.97

    def test_custom_efficiency(self):
        mppt = MpptModel(efficiency=0.95)
        assert mppt.efficiency == 0.95

    def test_constant_mode_ignores_power(self):
        mppt = MpptModel(efficiency=0.95)
        assert mppt.tracking_efficiency(panel_power=0.0) == 0.95
        assert mppt.tracking_efficiency(panel_power=10.0) == 0.95

    def test_invalid_efficiency_raises(self):
        with pytest.raises(ValueError):
            MpptModel(efficiency=1.5)


class TestMpptPowerDependent:
    def test_at_rated_power(self):
        """At rated power, efficiency should be close to peak."""
        mppt = MpptModel(
            efficiency=0.97, power_dependent=True, rated_power_w=10.0, min_efficiency=0.85
        )
        eff = mppt.tracking_efficiency(panel_power=10.0)
        assert eff > 0.96

    def test_at_low_power(self):
        """At very low power, efficiency should drop toward min."""
        mppt = MpptModel(
            efficiency=0.97, power_dependent=True, rated_power_w=10.0, min_efficiency=0.85
        )
        eff = mppt.tracking_efficiency(panel_power=0.1)
        assert eff < 0.92

    def test_at_zero_power(self):
        """At zero power, efficiency should equal min_efficiency."""
        mppt = MpptModel(
            efficiency=0.97, power_dependent=True, rated_power_w=10.0, min_efficiency=0.85
        )
        eff = mppt.tracking_efficiency(panel_power=0.0)
        # At zero power: η = η_peak - (η_peak - η_min) * exp(0) = η_min
        assert abs(eff - 0.85) < 0.01

    def test_monotonically_increasing(self):
        """Efficiency should increase with power."""
        mppt = MpptModel(
            efficiency=0.97, power_dependent=True, rated_power_w=10.0, min_efficiency=0.85
        )
        powers = np.linspace(0, 15, 50)
        effs = [mppt.tracking_efficiency(panel_power=p) for p in powers]
        for i in range(1, len(effs)):
            assert effs[i] >= effs[i - 1] - 1e-12
