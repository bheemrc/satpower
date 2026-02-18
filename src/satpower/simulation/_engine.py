"""Core simulation engine — ODE system, time-stepping, solve_ivp."""

from __future__ import annotations

import numpy as np
from scipy.integrate import solve_ivp

from satpower.orbit._propagator import Orbit, R_EARTH
from satpower.orbit._eclipse import EclipseModel
from satpower.orbit._environment import OrbitalEnvironment
from satpower.orbit._geometry import sun_position_eci, sun_vector
from satpower.solar._panel import SolarPanel
from satpower.solar._mppt import MpptModel
from satpower.battery._pack import BatteryPack
from satpower.battery._soc import CoulombCounter
from satpower.loads._profile import LoadProfile
from satpower.regulation._bus import PowerBus
from satpower.regulation._eps_board import EPSBoard
from satpower.simulation._results import SimulationResults

# Default panel temperature (K) — used when thermal model is disabled
_DEFAULT_PANEL_TEMP_K = 301.15  # ~28°C (standard test conditions)
_DEFAULT_BATTERY_TEMP_K = 298.15  # ~25°C


def _nadir_rotation_matrix(sat_pos: np.ndarray, sat_vel: np.ndarray) -> np.ndarray:
    """Compute rotation matrix from ECI to nadir-pointing body frame.

    Body frame convention:
    - Z_body points toward Earth (nadir)
    - X_body along velocity direction (ram)
    - Y_body completes right-hand frame (orbit normal cross-track)

    Parameters
    ----------
    sat_pos : (3,) satellite position in ECI
    sat_vel : (3,) satellite velocity in ECI

    Returns
    -------
    (3, 3) rotation matrix R such that v_body = R @ v_eci
    """
    # Z_body = -r_hat (toward Earth)
    z_body = -sat_pos / np.linalg.norm(sat_pos)

    # Y_body = orbit normal = -(r x v) / |r x v|  (negative so X ends up in ram direction)
    h = np.cross(sat_pos, sat_vel)
    y_body = -h / np.linalg.norm(h)

    # X_body = Y x Z (completes right-hand frame, roughly along velocity)
    x_body = np.cross(y_body, z_body)
    x_body = x_body / np.linalg.norm(x_body)

    # Rotation matrix: rows are body axes expressed in ECI
    return np.array([x_body, y_body, z_body])


class Simulation:
    """CubeSat power system simulation.

    Integrates the power balance over time using scipy's solve_ivp.

    State vector: [SoC, V_rc1, V_rc2] (no thermal)
                  [SoC, V_rc1, V_rc2, T_panel, T_battery] (with thermal)
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
        eps_board: EPSBoard | None = None,
        eclipse_model: str = "cylindrical",
        mppt_model: MpptModel | None = None,
        thermal_model: "ThermalModel | None" = None,
    ):
        self._orbit = orbit
        self._panels = panels
        self._battery = battery
        self._loads = loads
        self._environment = environment or OrbitalEnvironment()
        self._eps_board = eps_board

        # EPS board overrides bus and mppt_efficiency when provided
        if eps_board is not None:
            self._bus = eps_board.bus
            self._mppt_efficiency = eps_board.mppt_efficiency
        else:
            self._bus = bus or PowerBus()
            self._mppt_efficiency = mppt_efficiency

        self._mppt_model = mppt_model
        self._initial_soc = initial_soc
        self._epoch_doy = epoch_day_of_year
        self._eclipse_model = EclipseModel(method=eclipse_model)
        self._thermal_model = thermal_model
        self._thermal_enabled = thermal_model is not None

        # Precompute total panel area for thermal model
        self._total_panel_area = sum(p.area_m2 for p in panels) if panels else 0.0

    def _compute_solar_power(
        self,
        sat_pos: np.ndarray,
        sat_vel: np.ndarray,
        sun_pos: np.ndarray,
        shadow_frac: float,
        t: float = 0.0,
        panel_temp_k: float = _DEFAULT_PANEL_TEMP_K,
    ) -> float:
        """Compute total solar array power at a single timestep."""
        if shadow_frac >= 1.0:
            return 0.0

        # Sun direction in ECI
        sun_dir_eci = sun_vector(sat_pos, sun_pos)

        # Rotate Sun direction to body frame (nadir-pointing attitude)
        r_eci_to_body = _nadir_rotation_matrix(sat_pos, sat_vel)
        sun_dir_body = r_eci_to_body @ sun_dir_eci

        current_doy = self._epoch_doy + t / 86400.0
        irradiance = self._environment.solar_flux_at_epoch(current_doy) * (1.0 - shadow_frac)

        if self._mppt_model is not None and self._mppt_model._power_dependent:
            # Two-pass: first compute raw power, then apply power-dependent MPPT
            raw_power = 0.0
            for panel in self._panels:
                raw_power += panel.power(
                    sun_dir_body, irradiance, panel_temp_k, 1.0
                )
            mppt_eff = self._mppt_model.tracking_efficiency(panel_power=raw_power)
            return raw_power * mppt_eff

        mppt_eff = (
            self._mppt_model.efficiency if self._mppt_model is not None
            else self._mppt_efficiency
        )
        total_power = 0.0
        for panel in self._panels:
            total_power += panel.power(
                sun_dir_body, irradiance, panel_temp_k, mppt_eff
            )

        return total_power

    def _compute_solar_absorbed_heat(
        self,
        sat_pos: np.ndarray,
        sat_vel: np.ndarray,
        sun_pos: np.ndarray,
        shadow_frac: float,
        t: float,
        solar_power_w: float,
    ) -> float:
        """Compute solar heat absorbed by panels (not converted to electricity).

        Returns absorbed solar thermal power in watts.
        """
        if shadow_frac >= 1.0:
            return 0.0

        current_doy = self._epoch_doy + t / 86400.0
        irradiance = self._environment.solar_flux_at_epoch(current_doy) * (1.0 - shadow_frac)

        # Total solar power incident on panels (approximation: use total area * avg cos)
        # The electrical power is already computed; absorbed heat = incident - electrical
        # Simplified: absorbed = alpha * irradiance * area * avg_cos_angle - P_electrical
        # More conservative: use absorptance directly
        alpha = self._thermal_model.config.panel_absorptance if self._thermal_model else 0.91
        # Approximate total incident solar on panels
        total_incident = irradiance * self._total_panel_area * 0.5  # avg cos factor ~0.5
        solar_absorbed = alpha * total_incident - solar_power_w
        return max(0.0, solar_absorbed)

    def _rhs(self, t: float, state: np.ndarray) -> np.ndarray:
        """Right-hand side of the ODE system.

        state = [SoC, V_rc1, V_rc2] or [SoC, V_rc1, V_rc2, T_panel, T_battery]
        """
        if self._thermal_enabled:
            soc, v_rc1, v_rc2, t_panel, t_battery = state
        else:
            soc, v_rc1, v_rc2 = state
            t_panel = _DEFAULT_PANEL_TEMP_K
            t_battery = _DEFAULT_BATTERY_TEMP_K

        # Clamp SoC for intermediate calculations
        soc_clamped = np.clip(soc, 0.0, 1.0)

        # Orbit state at time t
        orbit_state = self._orbit.propagate(np.array([t]))
        sat_pos = orbit_state.position[0]
        sat_vel = orbit_state.velocity[0]

        # Sun position
        sun_pos = sun_position_eci(t, self._epoch_doy)

        # Eclipse
        shadow = self._eclipse_model.shadow_fraction(sat_pos, sun_pos)
        in_eclipse = shadow >= 0.5

        # Solar power (using dynamic panel temperature if thermal enabled)
        solar_power = self._compute_solar_power(
            sat_pos, sat_vel, sun_pos, shadow, t, t_panel
        )

        # Load power
        load_power = self._loads.power_at(t, in_eclipse)

        # Battery voltage (use OCV estimate for current computation)
        battery_voltage = self._battery.terminal_voltage(
            soc_clamped, 0.0, t_battery, v_rc1, v_rc2
        )

        # Battery current from power balance
        battery_current = self._bus.net_battery_current(
            solar_power, load_power, battery_voltage
        )

        # Iterative correction: recompute voltage with estimated current
        battery_voltage_loaded = self._battery.terminal_voltage(
            soc_clamped, battery_current, t_battery, v_rc1, v_rc2
        )
        if battery_voltage_loaded > 0:
            battery_current = self._bus.net_battery_current(
                solar_power, load_power, battery_voltage_loaded
            )

        # State derivatives
        dsoc_dt = CoulombCounter.dsoc_dt(battery_current, self._battery.capacity_ah)

        # Enforce SoC bounds: stop charging at 100%, stop discharging at 0%
        if soc >= 1.0 and dsoc_dt > 0:
            dsoc_dt = 0.0
        elif soc <= 0.0 and dsoc_dt < 0:
            dsoc_dt = 0.0

        dv_rc1_dt, dv_rc2_dt = self._battery.derivatives(battery_current, v_rc1, v_rc2)

        if not self._thermal_enabled:
            return np.array([dsoc_dt, dv_rc1_dt, dv_rc2_dt])

        # Thermal derivatives
        altitude_m = self._orbit.altitude_m
        solar_absorbed = self._compute_solar_absorbed_heat(
            sat_pos, sat_vel, sun_pos, shadow, t, solar_power
        )
        albedo_flux = self._environment.earth_albedo_flux(altitude_m)
        earth_ir_flux = self._environment.earth_ir_flux(altitude_m)

        dt_panel = self._thermal_model.panel_derivatives(
            t_panel, solar_absorbed, albedo_flux, earth_ir_flux, self._total_panel_area
        )

        # Battery Joule heating: I²R
        r_internal = self._battery.cell.internal_resistance(soc_clamped, t_battery)
        joule_heat = battery_current**2 * r_internal

        dt_battery = self._thermal_model.battery_derivatives(t_battery, joule_heat)

        return np.array([dsoc_dt, dv_rc1_dt, dv_rc2_dt, dt_panel, dt_battery])

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
        if self._thermal_enabled:
            cfg = self._thermal_model.config
            y0 = np.array([
                self._initial_soc, 0.0, 0.0,
                cfg.initial_panel_temp_k, cfg.initial_battery_temp_k,
            ])
        else:
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

        if self._thermal_enabled:
            panel_temperature = sol.y[3]
            battery_temperature = sol.y[4]
        else:
            panel_temperature = None
            battery_temperature = None

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
            sat_vel = orbit_state.velocity[0]
            sun_pos = sun_position_eci(t, self._epoch_doy)

            shadow = self._eclipse_model.shadow_fraction(sat_pos, sun_pos)
            in_ecl = shadow >= 0.5
            eclipse[i] = in_ecl

            t_panel = panel_temperature[i] if panel_temperature is not None else _DEFAULT_PANEL_TEMP_K
            t_bat = battery_temperature[i] if battery_temperature is not None else _DEFAULT_BATTERY_TEMP_K

            power_generated[i] = self._compute_solar_power(
                sat_pos, sat_vel, sun_pos, shadow, t, t_panel
            )
            power_consumed[i] = self._loads.power_at(t, in_ecl)

            # Compute battery current for voltage under load
            v_ocv = self._battery.terminal_voltage(
                soc[i], 0.0, t_bat, v_rc1[i], v_rc2[i]
            )
            i_bat = self._bus.net_battery_current(
                power_generated[i], power_consumed[i], v_ocv
            )
            battery_voltage[i] = self._battery.terminal_voltage(
                soc[i], i_bat, t_bat, v_rc1[i], v_rc2[i]
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
            panel_temperature=panel_temperature,
            battery_temperature=battery_temperature,
        )
