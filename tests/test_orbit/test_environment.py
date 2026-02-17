"""Tests for orbital environment."""

import numpy as np
import pytest

from satpower.orbit._environment import OrbitalEnvironment, SOLAR_CONSTANT


class TestSolarFlux:
    def test_at_1au(self):
        env = OrbitalEnvironment()
        assert abs(env.solar_flux(1.0) - SOLAR_CONSTANT) < 0.1

    def test_inverse_square(self):
        env = OrbitalEnvironment()
        assert abs(env.solar_flux(2.0) - SOLAR_CONSTANT / 4.0) < 0.1


class TestAlbedoFlux:
    def test_decreases_with_altitude(self):
        env = OrbitalEnvironment()
        low = env.earth_albedo_flux(400e3)
        high = env.earth_albedo_flux(800e3)
        assert low > high

    def test_reasonable_leo_value(self):
        env = OrbitalEnvironment()
        flux = env.earth_albedo_flux(500e3)
        # Albedo flux at LEO is typically 100-400 W/m^2
        assert 50 < flux < 400


class TestEarthIR:
    def test_decreases_with_altitude(self):
        env = OrbitalEnvironment()
        low = env.earth_ir_flux(400e3)
        high = env.earth_ir_flux(800e3)
        assert low > high

    def test_reasonable_leo_value(self):
        env = OrbitalEnvironment()
        flux = env.earth_ir_flux(500e3)
        # Earth IR at LEO is typically 150-250 W/m^2
        assert 100 < flux < 300


class TestBetaAngle:
    def test_equatorial_orbit_vernal_equinox(self):
        env = OrbitalEnvironment()
        # Equatorial orbit at vernal equinox: beta ≈ 0
        beta = env.beta_angle(
            inclination_rad=0,
            raan_rad=0,
            sun_ecliptic_lon_rad=0,
        )
        assert abs(beta) < np.radians(5)

    def test_sso_has_nonzero_beta(self):
        env = OrbitalEnvironment()
        # SSO (97.6°) typically has large beta angles
        beta = env.beta_angle(
            inclination_rad=np.radians(97.6),
            raan_rad=np.radians(90),
            sun_ecliptic_lon_rad=0,
        )
        assert abs(beta) > np.radians(1)
