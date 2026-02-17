"""Geometry utilities — Sun vector, panel incidence angles."""

from __future__ import annotations

import numpy as np

# Mean Earth-Sun distance (meters)
AU_METERS = 1.496e11


def sun_position_eci(time_s: float | np.ndarray, epoch_day_of_year: float = 80.0) -> np.ndarray:
    """Approximate Sun position in ECI frame (meters).

    Simple model: Sun orbits Earth in ecliptic plane once per year.
    epoch_day_of_year sets the starting Sun longitude (default: vernal equinox ~March 21).

    Parameters
    ----------
    time_s : seconds from epoch
    epoch_day_of_year : day of year at epoch (1-365)

    Returns
    -------
    (3,) or (N, 3) Sun position in ECI meters
    """
    time_s = np.asarray(time_s, dtype=float)
    scalar = time_s.ndim == 0
    time_s = np.atleast_1d(time_s)

    # Sun ecliptic longitude: starts at epoch_day_of_year, advances ~0.9856 deg/day
    days = time_s / 86400.0
    total_days = epoch_day_of_year + days
    sun_lon = 2.0 * np.pi * (total_days - 80.0) / 365.25  # 0 at vernal equinox

    # Obliquity of ecliptic
    obliquity = np.radians(23.44)

    x = AU_METERS * np.cos(sun_lon)
    y = AU_METERS * np.sin(sun_lon) * np.cos(obliquity)
    z = AU_METERS * np.sin(sun_lon) * np.sin(obliquity)

    result = np.column_stack([x, y, z])
    if scalar:
        return result[0]
    return result


def sun_vector(sat_pos: np.ndarray, sun_pos: np.ndarray) -> np.ndarray:
    """Unit vector from satellite to Sun.

    Parameters
    ----------
    sat_pos : (3,) or (N, 3) satellite position in ECI
    sun_pos : (3,) or (N, 3) Sun position in ECI

    Returns
    -------
    (3,) or (N, 3) unit vector toward Sun
    """
    diff = np.asarray(sun_pos) - np.asarray(sat_pos)
    norm = np.linalg.norm(diff, axis=-1, keepdims=True)
    return diff / norm


def panel_incidence_angle(panel_normal: np.ndarray, sun_dir: np.ndarray) -> float | np.ndarray:
    """Cosine of incidence angle between panel normal and Sun direction.

    Returns max(0, cos(angle)) — negative values mean the panel faces away.

    Parameters
    ----------
    panel_normal : (3,) unit vector of panel outward normal (body frame)
    sun_dir : (3,) or (N, 3) unit vector toward Sun (body frame)
    """
    cos_angle = np.dot(sun_dir, panel_normal)
    return np.maximum(0.0, cos_angle)
