"""Radiation degradation — JPL remaining factor model (Phase 2 full implementation)."""

from __future__ import annotations


def apply_radiation_degradation(
    power_bol: float,
    fluence_1mev: float,
    remaining_factor_1e14: float,
    remaining_factor_1e15: float,
) -> float:
    """Apply radiation degradation to beginning-of-life power.

    Uses log-linear interpolation of remaining factors from datasheet.

    Parameters
    ----------
    power_bol : Beginning-of-life power (W)
    fluence_1mev : Equivalent 1 MeV electron fluence (e-/cm^2)
    remaining_factor_1e14 : Pmax remaining at 1e14 fluence
    remaining_factor_1e15 : Pmax remaining at 1e15 fluence

    Returns
    -------
    Degraded power (W)
    """
    import numpy as np

    if fluence_1mev <= 0:
        return power_bol

    log_f = np.log10(fluence_1mev)
    log_f14 = 14.0
    log_f15 = 15.0

    if log_f <= log_f14:
        # Linear interpolation from 1.0 at 0 fluence to rf_1e14
        rf = 1.0 - (1.0 - remaining_factor_1e14) * (log_f / log_f14)
    elif log_f <= log_f15:
        # Interpolate between the two known points
        t = (log_f - log_f14) / (log_f15 - log_f14)
        rf = remaining_factor_1e14 + t * (remaining_factor_1e15 - remaining_factor_1e14)
    else:
        # Extrapolate beyond 1e15
        slope = (remaining_factor_1e15 - remaining_factor_1e14) / (log_f15 - log_f14)
        rf = remaining_factor_1e15 + slope * (log_f - log_f15)

    rf = max(0.0, min(1.0, rf))
    return power_bol * rf
