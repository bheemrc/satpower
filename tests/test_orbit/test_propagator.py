"""Tests for orbit propagation."""

import numpy as np
import pytest

from satpower.orbit._propagator import Orbit, R_EARTH, MU_EARTH, J2


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


class TestJ2Perturbation:
    def test_j2_raan_drift_sso(self):
        """SSO at 550 km should precess ~0.9856 deg/day."""
        orbit = Orbit.circular(altitude_km=550, inclination_deg=97.6, j2=True)
        one_day = 86400.0
        times = np.array([0.0, one_day])
        state = orbit.propagate(times)
        # The RAAN drift should be close to 0.9856 deg/day for SSO
        drift_deg = np.degrees(orbit._raan_rate * one_day)
        assert abs(drift_deg - 0.9856) < 0.15  # within 0.15 deg/day

    def test_j2_polar_no_drift(self):
        """Polar orbit (i=90°) should have zero RAAN drift."""
        orbit = Orbit.circular(altitude_km=500, inclination_deg=90, j2=True)
        assert abs(orbit._raan_rate) < 1e-12

    def test_j2_equatorial_max_drift(self):
        """Equatorial orbit should have maximum RAAN drift rate."""
        equatorial = Orbit.circular(altitude_km=500, inclination_deg=0, j2=True)
        inclined = Orbit.circular(altitude_km=500, inclination_deg=45, j2=True)
        assert abs(equatorial._raan_rate) > abs(inclined._raan_rate)

    def test_j2_disabled_by_default(self):
        """J2 should be disabled by default."""
        orbit = Orbit.circular(altitude_km=500, inclination_deg=45)
        assert orbit._raan_rate == 0.0

    def test_j2_altitude_unchanged(self):
        """J2 should not affect altitude (circular orbit stays circular)."""
        orbit = Orbit.circular(altitude_km=500, inclination_deg=45, j2=True)
        times = np.linspace(0, orbit.period * 10, 2000)
        state = orbit.propagate(times)
        altitudes = state.altitude / 1000.0
        assert np.allclose(altitudes, 500, atol=1.0)

    def test_j2_drift_direction(self):
        """Prograde orbit (i<90°) should have negative RAAN drift (westward)."""
        orbit = Orbit.circular(altitude_km=500, inclination_deg=45, j2=True)
        assert orbit._raan_rate < 0
        # Retrograde orbit (i>90°) should have positive RAAN drift (eastward)
        retro = Orbit.circular(altitude_km=500, inclination_deg=120, j2=True)
        assert retro._raan_rate > 0
