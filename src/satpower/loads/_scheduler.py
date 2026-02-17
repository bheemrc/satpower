"""Mode transition logic — triggers and priorities (Phase 2 full implementation)."""

from __future__ import annotations

from satpower.loads._profile import LoadProfile


class ModeScheduler:
    """Manages mode transitions based on triggers and priorities.

    Phase 1: pass-through to LoadProfile. Phase 2 will add state-based
    transitions (SoC thresholds, ground pass windows, scheduled events).
    """

    def __init__(self, profile: LoadProfile):
        self._profile = profile

    def power_at(self, time: float, in_eclipse: bool = False) -> float:
        """Get total power consumption considering mode transitions."""
        return self._profile.power_at(time, in_eclipse)

    def active_modes(self, time: float, in_eclipse: bool = False) -> list[str]:
        """Get active modes considering transitions."""
        return self._profile.active_modes(time, in_eclipse)
