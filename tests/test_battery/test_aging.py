"""Tests for battery aging model."""

import pytest

from satpower.battery._aging import AgingModel


class TestAgingModel:
    def test_no_aging(self):
        model = AgingModel()
        remaining = model.capacity_remaining(years=0, n_cycles=0, avg_dod=0.5)
        assert remaining == 1.0

    def test_calendar_aging_only(self):
        model = AgingModel(calendar_fade_per_year=0.02)
        remaining = model.capacity_remaining(years=5, n_cycles=0, avg_dod=0.5)
        assert abs(remaining - 0.90) < 0.01

    def test_cycle_aging_only(self):
        model = AgingModel(
            calendar_fade_per_year=0.0,
            cycle_fade_per_cycle_50dod=0.0001,
        )
        remaining = model.capacity_remaining(years=0, n_cycles=1000, avg_dod=0.5)
        assert abs(remaining - 0.90) < 0.01

    def test_combined_aging(self):
        model = AgingModel()
        remaining = model.capacity_remaining(years=3, n_cycles=5000, avg_dod=0.5)
        assert 0.0 < remaining < 1.0

    def test_never_negative(self):
        model = AgingModel()
        remaining = model.capacity_remaining(years=100, n_cycles=100000, avg_dod=1.0)
        assert remaining >= 0.0


class TestArrheniusAging:
    def test_arrhenius_at_reference_temp(self):
        """At reference temperature, factor should be 1.0."""
        model = AgingModel()
        factor = model._arrhenius_factor(298.15)
        assert abs(factor - 1.0) < 1e-6

    def test_arrhenius_higher_temp_faster(self):
        """Higher temperature should give factor > 1 (faster aging)."""
        model = AgingModel()
        factor = model._arrhenius_factor(308.15)  # +10K
        assert factor > 1.0

    def test_arrhenius_lower_temp_slower(self):
        """Lower temperature should give factor < 1 (slower aging)."""
        model = AgingModel()
        factor = model._arrhenius_factor(288.15)  # -10K
        assert factor < 1.0

    def test_capacity_at_high_temp(self):
        """High temperature should cause more capacity fade."""
        model = AgingModel()
        cap_ref = model.capacity_remaining(years=3, n_cycles=5000, avg_dod=0.5, temperature_k=298.15)
        cap_hot = model.capacity_remaining(years=3, n_cycles=5000, avg_dod=0.5, temperature_k=318.15)
        assert cap_hot < cap_ref

    def test_capacity_backwards_compatible(self):
        """Default temperature_k should give same result as before."""
        model = AgingModel()
        cap_default = model.capacity_remaining(years=3, n_cycles=5000, avg_dod=0.5)
        cap_explicit = model.capacity_remaining(years=3, n_cycles=5000, avg_dod=0.5, temperature_k=298.15)
        assert abs(cap_default - cap_explicit) < 1e-10
