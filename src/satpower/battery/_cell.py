"""Thevenin equivalent circuit model for battery cells."""

from __future__ import annotations

import numpy as np
from scipy.interpolate import interp1d

from satpower.data._loader import load_battery_cell, BatteryCellData

# Gas constant (J/(mol·K))
R_GAS = 8.314


class BatteryCell:
    """Thevenin R-RC equivalent circuit battery model.

    Models terminal voltage as:
        V_terminal = OCV(SoC) - I * R0 - V_rc1

    Where V_rc1 follows: dV_rc1/dt = I/C1 - V_rc1/(R1*C1)
    """

    def __init__(self, data: BatteryCellData):
        self._data = data
        tm = data.thevenin_model

        self._capacity_ah = data.capacity_ah
        self._nominal_v = data.nominal_voltage_v
        self._max_v = data.max_charge_voltage_v
        self._min_v = data.min_discharge_voltage_v

        self._r0 = tm.ro_ohm
        self._r1 = tm.r1_ohm
        self._c1 = tm.c1_f
        self._r2 = tm.r2_ohm
        self._c2 = tm.c2_f

        # Build OCV interpolator from SoC table
        soc_points = [row[0] for row in data.ocv_soc_table]
        ocv_points = [row[1] for row in data.ocv_soc_table]
        self._ocv_interp = interp1d(
            soc_points, ocv_points, kind="linear", fill_value="extrapolate"
        )

        # Temperature model
        self._ea = data.temperature.ro_activation_energy_j
        self._t_ref = data.temperature.reference_temp_c + 273.15

    @classmethod
    def from_datasheet(cls, name: str) -> BatteryCell:
        """Load battery cell from YAML datasheet."""
        return cls(load_battery_cell(name))

    @property
    def name(self) -> str:
        return self._data.name

    @property
    def capacity_ah(self) -> float:
        return self._capacity_ah

    @property
    def capacity_wh(self) -> float:
        return self._capacity_ah * self._nominal_v

    @property
    def nominal_voltage(self) -> float:
        return self._nominal_v

    @property
    def max_voltage(self) -> float:
        return self._max_v

    @property
    def min_voltage(self) -> float:
        return self._min_v

    def ocv(self, soc: float) -> float:
        """Open-circuit voltage at given state of charge."""
        soc = np.clip(soc, 0.0, 1.0)
        return float(self._ocv_interp(soc))

    def internal_resistance(self, soc: float, temperature_k: float = 298.15) -> float:
        """Total internal resistance (R0) with temperature correction.

        Uses Arrhenius relation for temperature dependence.
        """
        temp_factor = np.exp(
            self._ea / R_GAS * (1.0 / temperature_k - 1.0 / self._t_ref)
        )
        return self._r0 * temp_factor

    def terminal_voltage(
        self,
        soc: float,
        current: float,
        temperature_k: float = 298.15,
        v_rc1: float = 0.0,
        v_rc2: float = 0.0,
    ) -> float:
        """Terminal voltage under load.

        Parameters
        ----------
        soc : State of charge [0, 1]
        current : Current (A), positive = discharge, negative = charge
        temperature_k : Cell temperature (K)
        v_rc1 : RC circuit 1 voltage (V)
        v_rc2 : RC circuit 2 voltage (V)
        """
        r0 = self.internal_resistance(soc, temperature_k)
        v = self.ocv(soc) - current * r0 - v_rc1 - v_rc2
        return v

    def derivatives(self, current: float, v_rc1: float, v_rc2: float = 0.0) -> tuple[float, float]:
        """Compute dV_rc1/dt and dV_rc2/dt for ODE integration.

        Parameters
        ----------
        current : Current (A), positive = discharge
        v_rc1 : Current RC1 voltage
        v_rc2 : Current RC2 voltage

        Returns
        -------
        (dV_rc1_dt, dV_rc2_dt)
        """
        dv_rc1_dt = current / self._c1 - v_rc1 / (self._r1 * self._c1)

        if self._c2 > 0 and self._r2 > 0:
            dv_rc2_dt = current / self._c2 - v_rc2 / (self._r2 * self._c2)
        else:
            dv_rc2_dt = 0.0

        return dv_rc1_dt, dv_rc2_dt
