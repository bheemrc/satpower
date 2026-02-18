"""Mission mode definitions and duty cycling."""

from __future__ import annotations

from dataclasses import dataclass

_ALLOWED_TRIGGERS = {"always", "sunlight", "eclipse", "scheduled"}
_DEFAULT_SCHEDULE_PERIOD_S = 5400.0


@dataclass
class LoadMode:
    """A single operational mode with power consumption."""

    name: str
    power_w: float
    duty_cycle: float = 1.0
    trigger: str = "always"  # "always", "sunlight", "eclipse", "scheduled"
    priority: int = 0
    period_s: float = _DEFAULT_SCHEDULE_PERIOD_S
    phase_s: float = 0.0


class LoadProfile:
    """Collection of operational modes defining spacecraft power consumption."""

    def __init__(self) -> None:
        self._modes: list[LoadMode] = []

    def add_mode(
        self,
        name: str,
        power_w: float,
        duty_cycle: float = 1.0,
        trigger: str = "always",
        priority: int = 0,
        period_s: float = _DEFAULT_SCHEDULE_PERIOD_S,
        phase_s: float = 0.0,
    ) -> None:
        """Add an operational mode.

        Parameters
        ----------
        name : Mode name (e.g. 'idle', 'comms', 'payload')
        power_w : Average power consumption in this mode (W)
        duty_cycle : Fraction of time this mode is active [0, 1]
        trigger : When this mode activates: 'always', 'sunlight', 'eclipse', 'scheduled'
        priority : Higher priority modes override lower ones
        """
        if not 0.0 <= duty_cycle <= 1.0:
            raise ValueError(f"duty_cycle must be in [0, 1], got {duty_cycle}")
        if trigger not in _ALLOWED_TRIGGERS:
            raise ValueError(
                f"trigger must be one of {_ALLOWED_TRIGGERS}, got {trigger!r}"
            )
        if period_s <= 0.0:
            raise ValueError(f"period_s must be > 0, got {period_s}")
        self._modes.append(
            LoadMode(
                name=name,
                power_w=power_w,
                duty_cycle=duty_cycle,
                trigger=trigger,
                priority=priority,
                period_s=period_s,
                phase_s=phase_s,
            )
        )

    @staticmethod
    def _scheduled_active(mode: LoadMode, time: float) -> bool:
        if mode.duty_cycle <= 0.0:
            return False
        phase = ((time + mode.phase_s) % mode.period_s) / mode.period_s
        return phase < mode.duty_cycle

    @property
    def modes(self) -> list[LoadMode]:
        return list(self._modes)

    def power_at(self, time: float, in_eclipse: bool = False) -> float:
        """Total power consumption at a given time.

        For Phase 1, duty_cycle is applied as a simple average multiplier.
        Trigger-based modes are filtered by eclipse state.

        Parameters
        ----------
        time : Time (seconds from epoch)
        in_eclipse : Whether satellite is in eclipse
        """
        total = 0.0
        for mode in self._modes:
            if mode.trigger == "sunlight" and in_eclipse:
                continue
            if mode.trigger == "eclipse" and not in_eclipse:
                continue
            if mode.trigger == "scheduled":
                if self._scheduled_active(mode, time):
                    total += mode.power_w
                continue
            total += mode.power_w * mode.duty_cycle
        return total

    def active_modes(self, time: float, in_eclipse: bool = False) -> list[str]:
        """List of active mode names at given time."""
        active = []
        for mode in self._modes:
            if mode.trigger == "sunlight" and in_eclipse:
                continue
            if mode.trigger == "eclipse" and not in_eclipse:
                continue
            if mode.trigger == "scheduled" and not self._scheduled_active(mode, time):
                continue
            if mode.duty_cycle > 0:
                active.append(mode.name)
        return active

    def orbit_average_power(self, eclipse_fraction: float) -> float:
        """Compute orbit-averaged power consumption.

        Parameters
        ----------
        eclipse_fraction : Fraction of orbit in eclipse [0, 1]
        """
        sunlight_fraction = 1.0 - eclipse_fraction

        total = 0.0
        for mode in self._modes:
            if mode.trigger == "always":
                total += mode.power_w * mode.duty_cycle
            elif mode.trigger == "sunlight":
                total += mode.power_w * mode.duty_cycle * sunlight_fraction
            elif mode.trigger == "eclipse":
                total += mode.power_w * mode.duty_cycle * eclipse_fraction
            elif mode.trigger == "scheduled":
                total += mode.power_w * mode.duty_cycle
        return total
