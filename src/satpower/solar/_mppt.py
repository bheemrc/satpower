"""MPPT efficiency model."""

from __future__ import annotations


class MpptModel:
    """Maximum Power Point Tracker efficiency model.

    For Phase 1 MVP, uses a constant efficiency. Phase 2 will add
    voltage-dependent efficiency curves.
    """

    def __init__(self, efficiency: float = 0.97):
        if not 0.0 < efficiency <= 1.0:
            raise ValueError(f"MPPT efficiency must be in (0, 1], got {efficiency}")
        self._efficiency = efficiency

    @property
    def efficiency(self) -> float:
        return self._efficiency

    def tracking_efficiency(self, v_mpp: float = 0.0, v_bus: float = 0.0) -> float:
        """Return MPPT tracking efficiency.

        In Phase 1, returns a constant. Phase 2 will model efficiency as a
        function of input/output voltage ratio.
        """
        return self._efficiency
