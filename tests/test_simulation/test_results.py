"""Tests for simulation results and plotting."""

import numpy as np
import pytest

from satpower.simulation._results import SimulationResults


@pytest.fixture
def mock_results():
    n = 100
    period = 5400.0
    rng = np.random.default_rng(42)
    return SimulationResults(
        time=np.linspace(0, period * 2, n),
        soc=np.linspace(1.0, 0.7, n),
        power_generated=rng.uniform(0, 10, n),
        power_consumed=np.full(n, 4.0),
        battery_voltage=np.linspace(8.4, 7.2, n),
        eclipse=np.array([i % 3 == 0 for i in range(n)]),
        modes=["idle"] * n,
        orbit_period=period,
    )


class TestSimulationResults:
    def test_worst_case_dod(self, mock_results):
        assert abs(mock_results.worst_case_dod - 0.3) < 0.01

    def test_eclipse_fraction(self, mock_results):
        expected = np.mean([i % 3 == 0 for i in range(100)])
        assert abs(mock_results.eclipse_fraction - expected) < 0.01

    def test_summary_returns_dict(self, mock_results):
        summary = mock_results.summary()
        assert isinstance(summary, dict)
        assert "min_soc" in summary

    def test_time_orbits(self, mock_results):
        expected = mock_results.time / 5400.0
        np.testing.assert_allclose(mock_results.time_orbits, expected)
