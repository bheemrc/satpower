"""DC-DC converter efficiency model."""

from __future__ import annotations

import numpy as np


class DcDcConverter:
    """DC-DC converter with efficiency model.

    Supports constant efficiency (default) and load-dependent mode where
    efficiency varies with output load level.
    """

    def __init__(
        self,
        efficiency: float = 0.92,
        name: str = "",
        load_dependent: bool = False,
        rated_power_w: float = 20.0,
        peak_efficiency: float = 0.94,
        light_load_efficiency: float = 0.80,
    ):
        if not 0.0 < efficiency <= 1.0:
            raise ValueError(f"Efficiency must be in (0, 1], got {efficiency}")
        self._efficiency = efficiency
        self._name = name
        self._load_dependent = load_dependent
        self._rated_power_w = rated_power_w
        self._peak_efficiency = peak_efficiency
        self._light_load_efficiency = light_load_efficiency

    @property
    def efficiency(self) -> float:
        return self._efficiency

    @property
    def name(self) -> str:
        return self._name

    def efficiency_at_load(self, load_power_w: float) -> float:
        """Return converter efficiency at a given load power.

        When load_dependent is False, returns the constant efficiency.
        When load_dependent is True, models:
        - Low efficiency at light loads (switching losses dominate)
        - Peak efficiency at ~50% rated load
        - Mild droop above ~80% rated load (conduction losses)
        """
        if not self._load_dependent:
            return self._efficiency

        if self._rated_power_w <= 0 or load_power_w <= 0:
            return self._light_load_efficiency

        x = load_power_w / self._rated_power_w

        # Model: peak at x ≈ 0.5, with droop at high and low loads
        # Uses a quadratic-in-log model: eff = peak - a*(ln(x) - ln(0.5))^2
        # Simplified approach: rise with 1-exp, then droop above 0.5
        eta_range = self._peak_efficiency - self._light_load_efficiency
        # Rise: saturates quickly, reaching ~98% of range at x=0.5
        rise = 1.0 - np.exp(-6.0 * x)
        # Droop above 50% load: quadratic droop
        droop = 0.15 * eta_range * max(0.0, x - 0.5) ** 2
        eff = self._light_load_efficiency + eta_range * rise - droop
        return float(np.clip(eff, self._light_load_efficiency, self._peak_efficiency))

    def efficiency_for_discharge(self, load_power_w: float) -> float:
        """Efficiency for battery -> bus path."""
        return self.efficiency_at_load(load_power_w)

    def efficiency_for_charge(self, source_power_w: float) -> float:
        """Efficiency for solar -> battery path."""
        return self.efficiency_at_load(source_power_w)

    def output_power(self, input_power: float) -> float:
        """Output power given input power."""
        return input_power * self._efficiency

    def input_power(self, output_power: float) -> float:
        """Required input power to deliver given output power."""
        return output_power / self._efficiency
