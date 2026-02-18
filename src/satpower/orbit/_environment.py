"""Orbital environment — solar flux, Earth albedo, Earth IR."""

from __future__ import annotations

import numpy as np

from satpower.orbit._propagator import R_EARTH

# Solar constant at 1 AU (W/m^2)
SOLAR_CONSTANT = 1361.0

# Mean Earth albedo coefficient
EARTH_ALBEDO = 0.30

# Earth average IR emission (W/m^2 at surface)
EARTH_IR_EMISSION = 237.0


class OrbitalEnvironment:
    """Orbital environmental fluxes: solar, albedo, Earth IR."""

    def __init__(self, solar_constant: float = SOLAR_CONSTANT):
        self._solar_constant = solar_constant

    def solar_flux(self, distance_au: float = 1.0) -> float:
        """Solar flux at given distance from Sun (W/m^2).

        Follows inverse-square law from the solar constant at 1 AU.
        """
        return self._solar_constant / (distance_au**2)

    def solar_flux_at_epoch(self, day_of_year: float) -> float:
        """Solar flux accounting for Earth's orbital eccentricity (W/m^2).

        Varies ±3.4% over the year: peaks near perihelion (day ~3),
        minimum near aphelion (day ~186).

        Parameters
        ----------
        day_of_year : Day of the year (1–365.25), can be fractional.
        """
        return self._solar_constant * (
            1.0 + 0.0334 * np.cos(2.0 * np.pi * (day_of_year - 3.0) / 365.25)
        )

    def earth_albedo_flux(self, altitude_m: float) -> float:
        """Albedo flux reflected from Earth onto satellite (W/m^2).

        Uses simple view factor model for a spherical Earth.
        """
        r = R_EARTH + altitude_m
        view_factor = (R_EARTH / r) ** 2
        return EARTH_ALBEDO * self._solar_constant * view_factor

    def earth_ir_flux(self, altitude_m: float) -> float:
        """Earth infrared flux onto satellite (W/m^2).

        Assumes Earth radiates uniformly as a blackbody.
        """
        r = R_EARTH + altitude_m
        view_factor = (R_EARTH / r) ** 2
        return EARTH_IR_EMISSION * view_factor

    def beta_angle(
        self,
        inclination_rad: float,
        raan_rad: float,
        sun_ecliptic_lon_rad: float,
    ) -> float:
        """Beta angle — angle between orbital plane and Sun vector (radians).

        The beta angle determines eclipse duration and thermal environment.
        Higher |beta| = shorter eclipses (or none if |beta| > ~70° for LEO).

        Parameters
        ----------
        inclination_rad : Orbit inclination
        raan_rad : Right Ascension of Ascending Node
        sun_ecliptic_lon_rad : Sun ecliptic longitude (varies over the year)
        """
        # Sun direction in ECI (simplified: Sun in ecliptic plane)
        obliquity = np.radians(23.44)
        sun_x = np.cos(sun_ecliptic_lon_rad)
        sun_y = np.sin(sun_ecliptic_lon_rad) * np.cos(obliquity)
        sun_z = np.sin(sun_ecliptic_lon_rad) * np.sin(obliquity)
        sun_hat = np.array([sun_x, sun_y, sun_z])

        # Orbital plane normal (from RAAN and inclination)
        h_x = np.sin(raan_rad) * np.sin(inclination_rad)
        h_y = -np.cos(raan_rad) * np.sin(inclination_rad)
        h_z = np.cos(inclination_rad)
        h_hat = np.array([h_x, h_y, h_z])

        # Beta angle = arcsin(dot(sun_hat, h_hat))
        sin_beta = np.dot(sun_hat, h_hat)
        return np.arcsin(np.clip(sin_beta, -1.0, 1.0))
