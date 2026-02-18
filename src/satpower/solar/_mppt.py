"""MPPT efficiency model."""

from __future__ import annotations

import numpy as np


class MpptModel:
    """Maximum Power Point Tracker efficiency model.

    Supports constant efficiency (default) and power-dependent mode where
    efficiency drops at low power levels.
    """

    def __init__(
        self,
        efficiency: float = 0.97,
        power_dependent: bool = False,
        rated_power_w: float = 10.0,
        min_efficiency: float = 0.85,
    ):
        if not 0.0 < efficiency <= 1.0:
            raise ValueError(f"MPPT efficiency must be in (0, 1], got {efficiency}")
        if not 0.0 < min_efficiency <= efficiency:
            raise ValueError(
                f"min_efficiency must be in (0, efficiency], got {min_efficiency}"
            )
        self._efficiency = efficiency
        self._power_dependent = power_dependent
        self._rated_power_w = rated_power_w
        self._min_efficiency = min_efficiency

    @property
    def efficiency(self) -> float:
        return self._efficiency

    def tracking_efficiency(
        self, panel_power: float = 0.0, v_mpp: float = 0.0, v_bus: float = 0.0
    ) -> float:
        """Return MPPT tracking efficiency.

        Parameters
        ----------
        panel_power : Raw panel power before MPPT (W). Used in power-dependent mode.
        v_mpp : Maximum power point voltage (unused, for future extension).
        v_bus : Bus voltage (unused, for future extension).
        """
        if not self._power_dependent:
            return self._efficiency

        if self._rated_power_w <= 0:
            return self._efficiency

        p_frac = panel_power / self._rated_power_w
        # Exponential ramp: low power → low efficiency, rated power → peak efficiency
        eta = self._efficiency - (self._efficiency - self._min_efficiency) * np.exp(
            -5.0 * p_frac
        )
        return float(eta)
