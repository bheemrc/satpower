"""Simulation results container with plotting and summary statistics."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class SimulationResults:
    """Container for simulation output data."""

    time: np.ndarray  # seconds from epoch
    soc: np.ndarray  # state of charge [0, 1]
    power_generated: np.ndarray  # W
    power_consumed: np.ndarray  # W
    battery_voltage: np.ndarray  # V
    eclipse: np.ndarray  # boolean
    modes: list[str]  # active modes at each timestep
    orbit_period: float  # seconds

    @property
    def time_minutes(self) -> np.ndarray:
        return self.time / 60.0

    @property
    def time_hours(self) -> np.ndarray:
        return self.time / 3600.0

    @property
    def time_orbits(self) -> np.ndarray:
        return self.time / self.orbit_period

    @property
    def worst_case_dod(self) -> float:
        """Maximum depth of discharge encountered."""
        return 1.0 - float(np.min(self.soc))

    @property
    def power_margin(self) -> float:
        """Average power margin (generated - consumed) in W."""
        return float(np.mean(self.power_generated - self.power_consumed))

    @property
    def energy_balance_per_orbit(self) -> float:
        """Net energy per orbit in Wh."""
        total_time = self.time[-1] - self.time[0]
        n_orbits = total_time / self.orbit_period
        if n_orbits <= 0:
            return 0.0
        net_power = self.power_generated - self.power_consumed
        total_energy_ws = float(np.trapezoid(net_power, self.time))
        return total_energy_ws / 3600.0 / n_orbits

    @property
    def eclipse_fraction(self) -> float:
        """Fraction of simulation time in eclipse."""
        return float(np.mean(self.eclipse.astype(float)))

    def summary(self) -> dict:
        """Summary statistics."""
        return {
            "min_soc": float(np.min(self.soc)),
            "max_soc": float(np.max(self.soc)),
            "worst_case_dod": self.worst_case_dod,
            "avg_power_generated_w": float(np.mean(self.power_generated)),
            "avg_power_consumed_w": float(np.mean(self.power_consumed)),
            "power_margin_w": self.power_margin,
            "energy_balance_per_orbit_wh": self.energy_balance_per_orbit,
            "eclipse_fraction": self.eclipse_fraction,
            "min_battery_voltage_v": float(np.min(self.battery_voltage)),
            "max_battery_voltage_v": float(np.max(self.battery_voltage)),
            "duration_orbits": (self.time[-1] - self.time[0]) / self.orbit_period,
        }

    def plot_soc(self, ax=None):
        """Plot state of charge over time.

        Returns matplotlib Figure if no axes provided.
        """
        import matplotlib.pyplot as plt

        if ax is None:
            fig, ax = plt.subplots(figsize=(10, 4))
        else:
            fig = ax.get_figure()

        t = self.time_orbits
        ax.plot(t, self.soc * 100, "b-", linewidth=1.5)

        # Shade eclipse regions
        self._shade_eclipses(ax, t)

        ax.set_xlabel("Time (orbits)")
        ax.set_ylabel("State of Charge (%)")
        ax.set_title("Battery State of Charge")
        ax.set_ylim(0, 105)
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        return fig

    def plot_power_balance(self, ax=None):
        """Plot power generation and consumption over time."""
        import matplotlib.pyplot as plt

        if ax is None:
            fig, ax = plt.subplots(figsize=(10, 4))
        else:
            fig = ax.get_figure()

        t = self.time_orbits
        ax.plot(t, self.power_generated, "g-", linewidth=1.5, label="Generated")
        ax.plot(t, self.power_consumed, "r-", linewidth=1.5, label="Consumed")

        self._shade_eclipses(ax, t)

        ax.set_xlabel("Time (orbits)")
        ax.set_ylabel("Power (W)")
        ax.set_title("Power Balance")
        ax.legend()
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        return fig

    def plot_battery_voltage(self, ax=None):
        """Plot battery voltage over time."""
        import matplotlib.pyplot as plt

        if ax is None:
            fig, ax = plt.subplots(figsize=(10, 4))
        else:
            fig = ax.get_figure()

        t = self.time_orbits
        ax.plot(t, self.battery_voltage, "m-", linewidth=1.5)

        self._shade_eclipses(ax, t)

        ax.set_xlabel("Time (orbits)")
        ax.set_ylabel("Voltage (V)")
        ax.set_title("Battery Voltage")
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        return fig

    def _shade_eclipses(self, ax, t: np.ndarray) -> None:
        """Add gray shading for eclipse periods."""
        in_ecl = False
        start = 0.0
        for i in range(len(self.eclipse)):
            if self.eclipse[i] and not in_ecl:
                start = t[i]
                in_ecl = True
            elif not self.eclipse[i] and in_ecl:
                ax.axvspan(start, t[i], alpha=0.15, color="gray")
                in_ecl = False
        if in_ecl:
            ax.axvspan(start, t[-1], alpha=0.15, color="gray")
