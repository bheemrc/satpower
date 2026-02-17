"""Eclipse detection — cylindrical shadow model."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from satpower.orbit._propagator import R_EARTH


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
        if method not in ("cylindrical",):
            raise ValueError(f"Unknown eclipse method: {method!r}. Use 'cylindrical'.")
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

        # Satellite is on Sun side of Earth — check if in shadow cylinder
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

    def find_transitions(
        self,
        sat_positions: np.ndarray,
        sun_positions: np.ndarray,
        times: np.ndarray,
    ) -> list[EclipseEvent]:
        """Find eclipse entry/exit events by scanning shadow fraction transitions."""
        fractions = self.shadow_fraction(sat_positions, sun_positions)
        events = []

        for i in range(1, len(fractions)):
            if fractions[i - 1] == 0.0 and fractions[i] == 1.0:
                # Linear interpolation for transition time
                t_event = 0.5 * (times[i - 1] + times[i])
                events.append(EclipseEvent(time=t_event, event_type="entry"))
            elif fractions[i - 1] == 1.0 and fractions[i] == 0.0:
                t_event = 0.5 * (times[i - 1] + times[i])
                events.append(EclipseEvent(time=t_event, event_type="exit"))

        return events
