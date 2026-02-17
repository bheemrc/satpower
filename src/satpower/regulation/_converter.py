"""DC-DC converter efficiency model."""

from __future__ import annotations


class DcDcConverter:
    """DC-DC converter with efficiency model.

    Phase 1: constant efficiency. Phase 2 will add voltage/load-dependent
    efficiency curves from real converter datasheets.
    """

    def __init__(self, efficiency: float = 0.92, name: str = ""):
        if not 0.0 < efficiency <= 1.0:
            raise ValueError(f"Efficiency must be in (0, 1], got {efficiency}")
        self._efficiency = efficiency
        self._name = name

    @property
    def efficiency(self) -> float:
        return self._efficiency

    @property
    def name(self) -> str:
        return self._name

    def output_power(self, input_power: float) -> float:
        """Output power given input power."""
        return input_power * self._efficiency

    def input_power(self, output_power: float) -> float:
        """Required input power to deliver given output power."""
        return output_power / self._efficiency
