"""Orbit propagation — analytical Kepler for circular orbits."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# Earth constants
MU_EARTH = 3.986004418e14  # m^3/s^2
R_EARTH = 6371.0e3  # m
J2 = 1.08263e-3  # Earth J2 oblateness coefficient


@dataclass
class OrbitState:
    """Satellite state at one or more times."""

    time: np.ndarray  # seconds from epoch
    position: np.ndarray  # (N, 3) ECI positions in meters
    velocity: np.ndarray  # (N, 3) ECI velocities in m/s

    @property
    def altitude(self) -> np.ndarray:
        """Altitude above Earth surface in meters."""
        r = np.linalg.norm(self.position, axis=-1)
        return r - R_EARTH


class Orbit:
    """Circular orbit defined by altitude and inclination.

    Uses analytical Kepler propagation (constant altitude, no perturbations).
    Suitable for Phase 1 MVP power analysis.
    """

    def __init__(
        self,
        altitude_m: float,
        inclination_rad: float,
        raan_rad: float = 0.0,
        j2: bool = False,
    ):
        self._altitude_m = altitude_m
        self._inclination_rad = inclination_rad
        self._raan_rad = raan_rad
        self._semi_major_axis = R_EARTH + altitude_m
        self._mean_motion = np.sqrt(MU_EARTH / self._semi_major_axis**3)  # rad/s
        self._j2 = j2

        # J2 RAAN drift rate: dΩ/dt = -1.5 * n * J2 * (R_E/a)² * cos(i)
        if j2:
            self._raan_rate = (
                -1.5
                * self._mean_motion
                * J2
                * (R_EARTH / self._semi_major_axis) ** 2
                * np.cos(inclination_rad)
            )
        else:
            self._raan_rate = 0.0

    @classmethod
    def circular(
        cls,
        altitude_km: float,
        inclination_deg: float,
        raan_deg: float = 0.0,
        j2: bool = False,
    ) -> Orbit:
        """Create a circular orbit from altitude (km) and inclination (deg)."""
        return cls(
            altitude_m=altitude_km * 1000.0,
            inclination_rad=np.radians(inclination_deg),
            raan_rad=np.radians(raan_deg),
            j2=j2,
        )

    @property
    def period(self) -> float:
        """Orbital period in seconds."""
        return 2.0 * np.pi / self._mean_motion

    @property
    def altitude_m(self) -> float:
        return self._altitude_m

    @property
    def altitude_km(self) -> float:
        return self._altitude_m / 1000.0

    @property
    def inclination_deg(self) -> float:
        return np.degrees(self._inclination_rad)

    @property
    def semi_major_axis(self) -> float:
        """Semi-major axis in meters."""
        return self._semi_major_axis

    def propagate(self, times: np.ndarray) -> OrbitState:
        """Propagate orbit to given times (seconds from epoch).

        Returns positions and velocities in ECI frame assuming:
        - Circular orbit (constant radius)
        - RAAN and inclination define the orbital plane
        - Satellite starts at ascending node at t=0
        """
        times = np.asarray(times, dtype=float)
        a = self._semi_major_axis
        n = self._mean_motion
        inc = self._inclination_rad

        # RAAN: static or drifting with J2
        raan = self._raan_rad + self._raan_rate * times

        # True anomaly (= mean anomaly for circular orbit)
        theta = n * times

        # Position in orbital plane
        x_orb = a * np.cos(theta)
        y_orb = a * np.sin(theta)

        # Rotation to ECI: R_z(-RAAN) @ R_x(-inc) @ [x_orb, y_orb, 0]
        cos_raan = np.cos(raan)
        sin_raan = np.sin(raan)
        cos_inc = np.cos(inc)
        sin_inc = np.sin(inc)

        x_eci = cos_raan * x_orb - sin_raan * cos_inc * y_orb
        y_eci = sin_raan * x_orb + cos_raan * cos_inc * y_orb
        z_eci = sin_inc * y_orb

        position = np.column_stack([x_eci, y_eci, z_eci])

        # Velocity in orbital plane
        v = a * n
        vx_orb = -v * np.sin(theta)
        vy_orb = v * np.cos(theta)

        vx_eci = cos_raan * vx_orb - sin_raan * cos_inc * vy_orb
        vy_eci = sin_raan * vx_orb + cos_raan * cos_inc * vy_orb
        vz_eci = sin_inc * vy_orb

        velocity = np.column_stack([vx_eci, vy_eci, vz_eci])

        return OrbitState(time=times, position=position, velocity=velocity)
