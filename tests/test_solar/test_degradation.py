"""Tests for radiation degradation model."""

import pytest

from satpower.solar._degradation import apply_radiation_degradation


class TestRadiationDegradation:
    def test_zero_fluence_no_degradation(self):
        result = apply_radiation_degradation(10.0, 0, 0.93, 0.88)
        assert result == 10.0

    def test_at_1e14(self):
        result = apply_radiation_degradation(10.0, 1e14, 0.93, 0.88)
        assert abs(result - 9.3) < 0.1

    def test_at_1e15(self):
        result = apply_radiation_degradation(10.0, 1e15, 0.93, 0.88)
        assert abs(result - 8.8) < 0.1

    def test_degradation_increases_with_fluence(self):
        p1 = apply_radiation_degradation(10.0, 1e13, 0.93, 0.88)
        p2 = apply_radiation_degradation(10.0, 1e14, 0.93, 0.88)
        p3 = apply_radiation_degradation(10.0, 1e15, 0.93, 0.88)
        assert p1 > p2 > p3

    def test_result_never_negative(self):
        result = apply_radiation_degradation(10.0, 1e20, 0.93, 0.88)
        assert result >= 0.0
