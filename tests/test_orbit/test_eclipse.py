"""Tests for eclipse detection."""

import numpy as np
import pytest

from satpower.orbit._propagator import Orbit, R_EARTH
from satpower.orbit._eclipse import EclipseModel
from satpower.orbit._geometry import sun_position_eci


class TestCylindricalShadow:
    def test_sunlit_satellite(self):
        model = EclipseModel()
        # Satellite on Sun side of Earth
        sat_pos = np.array([R_EARTH + 400e3, 0, 0])
        sun_pos = np.array([1.496e11, 0, 0])  # Sun along +X
        assert model.shadow_fraction(sat_pos, sun_pos) == 0.0

    def test_eclipsed_satellite(self):
        model = EclipseModel()
        # Satellite behind Earth from Sun
        sat_pos = np.array([-(R_EARTH + 400e3), 0, 0])
        sun_pos = np.array([1.496e11, 0, 0])
        assert model.shadow_fraction(sat_pos, sun_pos) == 1.0

    def test_satellite_beside_shadow(self):
        model = EclipseModel()
        # Satellite perpendicular to Sun direction, above shadow cylinder
        sat_pos = np.array([0, R_EARTH + 400e3, 0])
        sun_pos = np.array([1.496e11, 0, 0])
        assert model.shadow_fraction(sat_pos, sun_pos) == 0.0

    def test_batch_shadow_fraction(self):
        model = EclipseModel()
        sun_pos = np.array([[1.496e11, 0, 0]] * 3)
        sat_pos = np.array([
            [R_EARTH + 400e3, 0, 0],     # sunlit
            [-(R_EARTH + 400e3), 0, 0],   # eclipsed
            [0, R_EARTH + 400e3, 0],      # beside
        ])
        fracs = model.shadow_fraction(sat_pos, sun_pos)
        assert fracs[0] == 0.0
        assert fracs[1] == 1.0
        assert fracs[2] == 0.0


class TestEclipseFraction:
    def test_orbit_has_eclipse(self):
        """A non-zero inclination orbit should have eclipse periods."""
        orbit = Orbit.circular(altitude_km=500, inclination_deg=45)
        model = EclipseModel()
        times = np.linspace(0, orbit.period, 500)
        state = orbit.propagate(times)
        sun_pos = sun_position_eci(times, epoch_day_of_year=80)

        fracs = model.shadow_fraction(state.position, sun_pos)
        eclipse_frac = np.mean(fracs)

        # LEO orbits typically have 30-40% eclipse
        assert 0.1 < eclipse_frac < 0.5

    def test_find_transitions(self):
        orbit = Orbit.circular(altitude_km=500, inclination_deg=45)
        model = EclipseModel()
        times = np.linspace(0, orbit.period * 2, 2000)
        state = orbit.propagate(times)
        sun_pos = sun_position_eci(times, epoch_day_of_year=80)

        events = model.find_transitions(state.position, sun_pos, times)
        # Should have at least 2 transitions per orbit
        assert len(events) >= 2
