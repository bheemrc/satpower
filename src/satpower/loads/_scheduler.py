"""Mode transition logic — triggers and priorities."""

from __future__ import annotations

from satpower.loads._profile import LoadMode, LoadProfile


class ModeScheduler:
    """Manages mode transitions based on triggers and priorities.

    Priority model (baseline + override):
    - Priority 0 modes are "baseline" and always run when their trigger is
      satisfied (e.g., OBC, ADCS).
    - Higher-priority modes represent operational overrides. When multiple
      priority levels are active, the *highest* priority level is selected
      as the active override. Intermediate priorities are NOT included —
      this models exclusive operational modes (e.g., comms vs payload).
    - The final active set is: baseline (p=0) + highest-priority override.
    """

    def __init__(self, profile: LoadProfile):
        self._profile = profile

    def _mode_active(self, mode: LoadMode, time: float, in_eclipse: bool) -> bool:
        if mode.trigger == "sunlight" and in_eclipse:
            return False
        if mode.trigger == "eclipse" and not in_eclipse:
            return False
        if mode.trigger == "scheduled":
            return self._profile._scheduled_active(mode, time)
        return True

    def _active_priority_set(self, time: float, in_eclipse: bool) -> list[LoadMode]:
        """Return the set of modes that should be active at this time.

        Returns all baseline (priority=0) modes whose triggers are satisfied,
        plus all modes at the single highest active priority level (override).
        """
        active = [
            m for m in self._profile.modes
            if m.duty_cycle > 0.0 and self._mode_active(m, time, in_eclipse)
        ]
        if not active:
            return []
        highest_priority = max(m.priority for m in active)
        if highest_priority == 0:
            # All modes are baseline — return them all
            return active
        baseline = [m for m in active if m.priority == 0]
        override = [m for m in active if m.priority == highest_priority]
        return baseline + override

    def power_at(self, time: float, in_eclipse: bool = False) -> float:
        """Get total power consumption considering mode transitions."""
        total = 0.0
        for mode in self._active_priority_set(time, in_eclipse):
            if mode.trigger == "scheduled":
                total += mode.power_w
            else:
                total += mode.power_w * mode.duty_cycle
        return total

    def active_modes(self, time: float, in_eclipse: bool = False) -> list[str]:
        """Get active modes considering transitions."""
        return [m.name for m in self._active_priority_set(time, in_eclipse)]
