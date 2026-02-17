"""Tests for orbit propagation."""

import numpy as np
import pytest

from satpower.orbit._propagator import Orbit, R_EARTH, MU_EARTH


class TestOrbitCreation:
    def test_circular_orbit_creation(self):
        orbit = Orbit.circular(altitude_km=400, inclination_deg=51.6)
        assert abs(orbit.altitude_km - 400) < 0.01
        assert abs(orbit.inclination_deg - 51.6) < 0.01

    def test_period_iss_like(self):
        orbit = Orbit.circular(altitude_km=408, inclination_deg=51.6)
        # ISS period is ~92.6 minutes
        period_min = orbit.period / 60.0
        assert 90 < period_min < 95

    def test_period_scales_with_altitude(self):
        low = Orbit.circular(altitude_km=300, inclination_deg=0)
        high = Orbit.circular(altitude_km=800, inclination_deg=0)
        assert high.period > low.period


class TestPropagation:
    def test_propagate_returns_correct_shape(self):
        orbit = Orbit.circular(altitude_km=500, inclination_deg=45)
        times = np.linspace(0, orbit.period, 100)
        state = orbit.propagate(times)
        assert state.position.shape == (100, 3)
        assert state.velocity.shape == (100, 3)

    def test_altitude_constant_for_circular(self):
        orbit = Orbit.circular(altitude_km=500, inclination_deg=45)
        times = np.linspace(0, orbit.period * 3, 1000)
        state = orbit.propagate(times)
        altitudes = state.altitude / 1000.0  # to km
        assert np.allclose(altitudes, 500, atol=1.0)

    def test_orbit_radius_matches_sma(self):
        orbit = Orbit.circular(altitude_km=600, inclination_deg=0)
        times = np.linspace(0, orbit.period, 50)
        state = orbit.propagate(times)
        radii = np.linalg.norm(state.position, axis=1)
        expected = R_EARTH + 600e3
        assert np.allclose(radii, expected, rtol=1e-10)

    def test_equatorial_orbit_stays_in_xy_plane(self):
        orbit = Orbit.circular(altitude_km=500, inclination_deg=0)
        times = np.linspace(0, orbit.period, 100)
        state = orbit.propagate(times)
        # For 0° inclination, z should be ~0
        assert np.allclose(state.position[:, 2], 0, atol=1e-6)

    def test_polar_orbit_reaches_poles(self):
        orbit = Orbit.circular(altitude_km=500, inclination_deg=90)
        times = np.linspace(0, orbit.period, 1000)
        state = orbit.propagate(times)
        max_z = np.max(np.abs(state.position[:, 2]))
        expected_r = R_EARTH + 500e3
        assert max_z > expected_r * 0.99
