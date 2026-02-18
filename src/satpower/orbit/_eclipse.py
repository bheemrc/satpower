"""Eclipse detection — cylindrical and conical shadow models."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from satpower.orbit._propagator import R_EARTH

# Sun radius in meters
R_SUN = 6.957e8


@dataclass
class EclipseEvent:
    """An eclipse entry or exit event."""

    time: float  # seconds from epoch
    event_type: str  # "entry" or "exit"


class EclipseModel:
    """Eclipse detection using shadow models.

    Currently implements the cylindrical shadow model, which treats Earth's
    shadow as a cylinder (no penumbra). Sufficient for power budget analysis.
    """

    def __init__(self, method: str = "cylindrical"):
        if method not in ("cylindrical", "conical"):
            raise ValueError(
                f"Unknown eclipse method: {method!r}. Use 'cylindrical' or 'conical'."
            )
        self._method = method

    def shadow_fraction(
        self, sat_pos: np.ndarray, sun_pos: np.ndarray
    ) -> float | np.ndarray:
        """Compute shadow fraction: 0 = full sun, 1 = full shadow.

        Parameters
        ----------
        sat_pos : (3,) or (N, 3) satellite position in ECI (meters)
        sun_pos : (3,) or (N, 3) Sun position in ECI (meters)
        """
        if self._method == "conical":
            return self._conical_shadow_fraction(sat_pos, sun_pos)
        return self._cylindrical_shadow_fraction(sat_pos, sun_pos)

    def _cylindrical_shadow_fraction(
        self, sat_pos: np.ndarray, sun_pos: np.ndarray
    ) -> float | np.ndarray:
        """Cylindrical shadow model — sharp boundary, no penumbra."""
        sat_pos = np.asarray(sat_pos, dtype=float)
        sun_pos = np.asarray(sun_pos, dtype=float)

        single = sat_pos.ndim == 1
        if single:
            sat_pos = sat_pos[np.newaxis, :]
            sun_pos = sun_pos[np.newaxis, :]

        # Unit vector from satellite to Sun
        to_sun = sun_pos - sat_pos
        to_sun_norm = np.linalg.norm(to_sun, axis=-1, keepdims=True)
        to_sun_hat = to_sun / to_sun_norm

        # Project satellite position onto Sun direction
        proj = np.sum(sat_pos * to_sun_hat, axis=-1)

        # Distance from satellite to the Earth-Sun line
        rejection = sat_pos - proj[:, np.newaxis] * to_sun_hat
        dist_from_axis = np.linalg.norm(rejection, axis=-1)

        # In shadow if: satellite is behind Earth (proj < 0) AND
        # distance from shadow axis < Earth radius
        in_shadow = (proj < 0) & (dist_from_axis < R_EARTH)

        result = np.where(in_shadow, 1.0, 0.0)
        if single:
            return float(result[0])
        return result

    def _conical_shadow_fraction(
        self, sat_pos: np.ndarray, sun_pos: np.ndarray
    ) -> float | np.ndarray:
        """Conical shadow model with penumbra transition.

        Uses angular overlap between Sun and Earth disks as seen from satellite.
        """
        sat_pos = np.asarray(sat_pos, dtype=float)
        sun_pos = np.asarray(sun_pos, dtype=float)

        single = sat_pos.ndim == 1
        if single:
            sat_pos = sat_pos[np.newaxis, :]
            sun_pos = sun_pos[np.newaxis, :]

        # Vectors from satellite to Earth center and Sun center
        to_earth = -sat_pos  # Earth is at origin
        to_sun = sun_pos - sat_pos

        d_earth = np.linalg.norm(to_earth, axis=-1)
        d_sun = np.linalg.norm(to_sun, axis=-1)

        # Angular radii of Earth and Sun as seen from satellite
        theta_earth = np.arcsin(np.clip(R_EARTH / d_earth, 0.0, 1.0))
        theta_sun = np.arcsin(np.clip(R_SUN / d_sun, 0.0, 1.0))

        # Angular separation between Earth center and Sun center
        to_earth_hat = to_earth / d_earth[:, np.newaxis]
        to_sun_hat = to_sun / d_sun[:, np.newaxis]
        cos_sep = np.sum(to_earth_hat * to_sun_hat, axis=-1)
        theta_sep = np.arccos(np.clip(cos_sep, -1.0, 1.0))

        # Shadow classification
        # Full sun: separation >= earth_angular_radius + sun_angular_radius
        # Full umbra: separation <= earth_angular_radius - sun_angular_radius
        # Penumbra: linear ramp between
        result = np.zeros(len(sat_pos))

        full_sun = theta_sep >= (theta_earth + theta_sun)
        full_shadow = theta_sep <= (theta_earth - theta_sun)
        penumbra = ~full_sun & ~full_shadow

        result[full_shadow] = 1.0
        # Linear interpolation through penumbra
        if np.any(penumbra):
            pen_range = 2.0 * theta_sun[penumbra]
            pen_pos = (theta_earth[penumbra] + theta_sun[penumbra]) - theta_sep[penumbra]
            result[penumbra] = np.clip(pen_pos / pen_range, 0.0, 1.0)

        if single:
            return float(result[0])
        return result

    def find_transitions(
        self,
        sat_positions: np.ndarray,
        sun_positions: np.ndarray,
        times: np.ndarray,
        threshold: float = 0.5,
    ) -> list[EclipseEvent]:
        """Find eclipse entry/exit events by threshold crossing."""
        fractions = self.shadow_fraction(sat_positions, sun_positions)
        events = []

        for i in range(1, len(fractions)):
            prev_in = fractions[i - 1] >= threshold
            curr_in = fractions[i] >= threshold
            if not prev_in and curr_in:
                t_event = 0.5 * (times[i - 1] + times[i])
                events.append(EclipseEvent(time=t_event, event_type="entry"))
            elif prev_in and not curr_in:
                t_event = 0.5 * (times[i - 1] + times[i])
                events.append(EclipseEvent(time=t_event, event_type="exit"))

        return events
