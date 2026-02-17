"""Core simulation engine — ODE system, time-stepping, solve_ivp."""

from __future__ import annotations

import numpy as np
from scipy.integrate import solve_ivp

from satpower.orbit._propagator import Orbit
from satpower.orbit._eclipse import EclipseModel
from satpower.orbit._environment import OrbitalEnvironment
from satpower.orbit._geometry import sun_position_eci, sun_vector, panel_incidence_angle
from satpower.solar._panel import SolarPanel
from satpower.battery._pack import BatteryPack
from satpower.battery._soc import CoulombCounter
from satpower.loads._profile import LoadProfile
from satpower.regulation._bus import PowerBus
from satpower.simulation._results import SimulationResults

# Default panel temperature (K) — simplified for Phase 1
_DEFAULT_PANEL_TEMP_K = 301.15  # ~28°C (standard test conditions)
_DEFAULT_BATTERY_TEMP_K = 298.15  # ~25°C


class Simulation:
    """CubeSat power system simulation.

    Integrates the power balance over time using scipy's solve_ivp.

    State vector: [SoC, V_rc1, V_rc2]
    """

    def __init__(
        self,
        orbit: Orbit,
        panels: list[SolarPanel],
        battery: BatteryPack,
        loads: LoadProfile,
        environment: OrbitalEnvironment | None = None,
        bus: PowerBus | None = None,
        mppt_efficiency: float = 0.97,
        initial_soc: float = 1.0,
        epoch_day_of_year: float = 80.0,
    ):
        self._orbit = orbit
        self._panels = panels
        self._battery = battery
        self._loads = loads
        self._environment = environment or OrbitalEnvironment()
        self._bus = bus or PowerBus()
        self._mppt_efficiency = mppt_efficiency
        self._initial_soc = initial_soc
        self._epoch_doy = epoch_day_of_year
        self._eclipse_model = EclipseModel()

    def _compute_solar_power(
        self, sat_pos: np.ndarray, sun_pos: np.ndarray, shadow_frac: float
    ) -> float:
        """Compute total solar array power at a single timestep."""
        if shadow_frac >= 1.0:
            return 0.0

        sun_dir = sun_vector(sat_pos, sun_pos)
        irradiance = self._environment.solar_flux() * (1.0 - shadow_frac)

        total_power = 0.0
        for panel in self._panels:
            total_power += panel.power(
                sun_dir,
                irradiance,
                _DEFAULT_PANEL_TEMP_K,
                self._mppt_efficiency,
            )

        return total_power

    def _rhs(self, t: float, state: np.ndarray) -> np.ndarray:
        """Right-hand side of the ODE system.

        state = [SoC, V_rc1, V_rc2]
        """
        soc, v_rc1, v_rc2 = state

        # Clamp SoC
        soc = np.clip(soc, 0.0, 1.0)

        # Orbit state at time t
        orbit_state = self._orbit.propagate(np.array([t]))
        sat_pos = orbit_state.position[0]

        # Sun position
        sun_pos = sun_position_eci(t, self._epoch_doy)

        # Eclipse
        shadow = self._eclipse_model.shadow_fraction(sat_pos, sun_pos)
        in_eclipse = shadow >= 0.5

        # Solar power
        solar_power = self._compute_solar_power(sat_pos, sun_pos, shadow)

        # Load power
        load_power = self._loads.power_at(t, in_eclipse)

        # Battery voltage and current
        battery_voltage = self._battery.terminal_voltage(
            soc, 0.0, _DEFAULT_BATTERY_TEMP_K, v_rc1, v_rc2
        )
        battery_current = self._bus.net_battery_current(
            solar_power, load_power, battery_voltage
        )

        # State derivatives
        dsoc_dt = CoulombCounter.dsoc_dt(battery_current, self._battery.capacity_ah)
        dv_rc1_dt, dv_rc2_dt = self._battery.derivatives(battery_current, v_rc1, v_rc2)

        return np.array([dsoc_dt, dv_rc1_dt, dv_rc2_dt])

    def run(
        self,
        duration_orbits: float | None = None,
        duration_s: float | None = None,
        dt_max: float = 30.0,
        method: str = "RK45",
    ) -> SimulationResults:
        """Run the simulation.

        Parameters
        ----------
        duration_orbits : Simulation duration in orbital periods
        duration_s : Simulation duration in seconds (overrides duration_orbits)
        dt_max : Maximum timestep (seconds)
        method : ODE solver method ('RK45', 'BDF', etc.)
        """
        if duration_s is not None:
            t_end = duration_s
        elif duration_orbits is not None:
            t_end = duration_orbits * self._orbit.period
        else:
            raise ValueError("Specify either duration_orbits or duration_s")

        # Initial state
        y0 = np.array([self._initial_soc, 0.0, 0.0])

        # Time evaluation points (for dense output)
        n_points = max(int(t_end / dt_max) + 1, 100)
        t_eval = np.linspace(0, t_end, n_points)

        # Solve ODE
        sol = solve_ivp(
            self._rhs,
            (0, t_end),
            y0,
            method=method,
            t_eval=t_eval,
            max_step=dt_max,
            rtol=1e-6,
            atol=1e-8,
        )

        if not sol.success:
            raise RuntimeError(f"ODE solver failed: {sol.message}")

        # Extract results and compute auxiliary quantities
        times = sol.t
        soc = np.clip(sol.y[0], 0.0, 1.0)
        v_rc1 = sol.y[1]
        v_rc2 = sol.y[2]

        # Recompute auxiliary arrays
        n = len(times)
        power_generated = np.zeros(n)
        power_consumed = np.zeros(n)
        battery_voltage = np.zeros(n)
        eclipse = np.zeros(n, dtype=bool)
        modes = []

        for i, t in enumerate(times):
            orbit_state = self._orbit.propagate(np.array([t]))
            sat_pos = orbit_state.position[0]
            sun_pos = sun_position_eci(t, self._epoch_doy)

            shadow = self._eclipse_model.shadow_fraction(sat_pos, sun_pos)
            in_ecl = shadow >= 0.5
            eclipse[i] = in_ecl

            power_generated[i] = self._compute_solar_power(sat_pos, sun_pos, shadow)
            power_consumed[i] = self._loads.power_at(t, in_ecl)

            battery_voltage[i] = self._battery.terminal_voltage(
                soc[i], 0.0, _DEFAULT_BATTERY_TEMP_K, v_rc1[i], v_rc2[i]
            )

            modes.append(
                ",".join(self._loads.active_modes(t, in_ecl))
            )

        return SimulationResults(
            time=times,
            soc=soc,
            power_generated=power_generated,
            power_consumed=power_consumed,
            battery_voltage=battery_voltage,
            eclipse=eclipse,
            modes=modes,
            orbit_period=self._orbit.period,
        )
