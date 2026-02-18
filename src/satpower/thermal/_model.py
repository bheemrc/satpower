"""Thermal model for solar panels and battery."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# Stefan-Boltzmann constant (W/m^2/K^4)
STEFAN_BOLTZMANN = 5.670374419e-8


@dataclass
class ThermalConfig:
    """Configuration for the thermal model."""

    panel_thermal_mass_j_per_k: float = 450.0  # 0.5 kg * 900 J/(kg·K) for Si
    panel_absorptance: float = 0.91
    panel_emittance: float = 0.85
    panel_area_m2: float = 0.06  # total illuminated area, set from panels
    battery_thermal_mass_j_per_k: float = 95.0  # n_cells * mass * Cp
    battery_emittance: float = 0.8
    battery_surface_area_m2: float = 0.01
    spacecraft_interior_temp_k: float = 293.15  # 20°C
    initial_panel_temp_k: float = 301.15  # ~28°C
    initial_battery_temp_k: float = 298.15  # ~25°C


class ThermalModel:
    """Lumped-parameter thermal model for panel and battery temperatures.

    Computes temperature derivatives for ODE integration:
    - Panel: absorbs solar, albedo, Earth IR; radiates to space from both sides.
    - Battery: heated by Joule losses (I²R); radiates to spacecraft interior.
    """

    def __init__(self, config: ThermalConfig | None = None):
        self._config = config or ThermalConfig()

    @property
    def config(self) -> ThermalConfig:
        return self._config

    def panel_derivatives(
        self,
        t_panel: float,
        solar_absorbed_w: float,
        albedo_flux_w_m2: float,
        earth_ir_flux_w_m2: float,
        panel_area_m2: float,
    ) -> float:
        """Compute dT_panel/dt (K/s).

        Parameters
        ----------
        t_panel : Current panel temperature (K)
        solar_absorbed_w : Solar power absorbed by panel (not converted to electricity)
        albedo_flux_w_m2 : Earth albedo flux at satellite (W/m²)
        earth_ir_flux_w_m2 : Earth IR flux at satellite (W/m²)
        panel_area_m2 : Panel area for radiation (m²)
        """
        cfg = self._config
        alpha = cfg.panel_absorptance
        eps = cfg.panel_emittance

        # Absorbed heat inputs
        q_albedo = alpha * albedo_flux_w_m2 * panel_area_m2
        q_earth_ir = eps * earth_ir_flux_w_m2 * panel_area_m2

        # Radiated heat — panel radiates from both sides (factor of 2)
        q_radiated = eps * STEFAN_BOLTZMANN * panel_area_m2 * 2.0 * t_panel**4

        # Net heat flow
        q_net = solar_absorbed_w + q_albedo + q_earth_ir - q_radiated

        return q_net / cfg.panel_thermal_mass_j_per_k

    def battery_derivatives(
        self,
        t_battery: float,
        joule_heat_w: float,
        heater_power_w: float = 0.0,
    ) -> float:
        """Compute dT_battery/dt (K/s).

        Parameters
        ----------
        t_battery : Current battery temperature (K)
        joule_heat_w : Internal resistive heating I²R (W)
        heater_power_w : Survival heater power (W)
        """
        cfg = self._config
        eps = cfg.battery_emittance
        a_bat = cfg.battery_surface_area_m2
        t_sc = cfg.spacecraft_interior_temp_k

        # Battery radiates to spacecraft interior (net radiation)
        q_radiated = eps * STEFAN_BOLTZMANN * a_bat * (t_battery**4 - t_sc**4)

        q_net = joule_heat_w + heater_power_w - q_radiated

        return q_net / cfg.battery_thermal_mass_j_per_k
