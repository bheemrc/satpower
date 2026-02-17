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
