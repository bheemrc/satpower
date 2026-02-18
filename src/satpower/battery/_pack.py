"""Battery pack — series/parallel cell configurations."""

from __future__ import annotations

import re

from satpower.battery._cell import BatteryCell


def _parse_config(config: str) -> tuple[int, int]:
    """Parse a battery configuration string like '2S2P' -> (n_series, n_parallel)."""
    match = re.match(r"^(\d+)S(\d+)P$", config.upper())
    if not match:
        raise ValueError(
            f"Invalid battery config: {config!r}. Expected format like '2S2P'."
        )
    n_series, n_parallel = int(match.group(1)), int(match.group(2))
    if n_series <= 0 or n_parallel <= 0:
        raise ValueError(
            f"Invalid battery config: {config!r}. Series/parallel counts must be > 0."
        )
    return n_series, n_parallel


class BatteryPack:
    """Battery pack with series/parallel cell configuration."""

    def __init__(self, cell: BatteryCell, n_series: int, n_parallel: int):
        self._cell = cell
        self._n_series = n_series
        self._n_parallel = n_parallel

    @classmethod
    def from_cell(cls, cell_name: str, config: str) -> BatteryPack:
        """Create a battery pack from a cell datasheet and configuration string.

        Parameters
        ----------
        cell_name : Name of battery cell (e.g. 'panasonic_ncr18650b')
        config : Configuration string (e.g. '2S2P')
        """
        cell = BatteryCell.from_datasheet(cell_name)
        n_s, n_p = _parse_config(config)
        return cls(cell, n_s, n_p)

    @property
    def cell(self) -> BatteryCell:
        return self._cell

    @property
    def n_series(self) -> int:
        return self._n_series

    @property
    def n_parallel(self) -> int:
        return self._n_parallel

    @property
    def capacity_ah(self) -> float:
        """Total pack capacity in Ah (parallel cells add capacity)."""
        return self._cell.capacity_ah * self._n_parallel

    @property
    def energy_wh(self) -> float:
        """Total pack energy in Wh."""
        return self.capacity_ah * self._cell.nominal_voltage * self._n_series

    @property
    def nominal_voltage(self) -> float:
        """Nominal pack voltage (series cells add voltage)."""
        return self._cell.nominal_voltage * self._n_series

    @property
    def max_voltage(self) -> float:
        return self._cell.max_voltage * self._n_series

    @property
    def min_voltage(self) -> float:
        return self._cell.min_voltage * self._n_series

    @property
    def max_charge_current_a(self) -> float:
        """Maximum pack charge current (A)."""
        return self._cell.max_charge_current_a * self._n_parallel

    @property
    def max_discharge_current_a(self) -> float:
        """Maximum pack discharge current (A)."""
        return self._cell.max_discharge_current_a * self._n_parallel

    def terminal_voltage(
        self,
        soc: float,
        current: float,
        temperature_k: float = 298.15,
        v_rc1: float = 0.0,
        v_rc2: float = 0.0,
    ) -> float:
        """Pack terminal voltage.

        Parameters
        ----------
        soc : State of charge [0, 1]
        current : Pack current (A), positive = discharge
        temperature_k : Cell temperature (K)
        v_rc1 : Per-cell RC1 voltage
        v_rc2 : Per-cell RC2 voltage
        """
        # Current per parallel string
        cell_current = current / self._n_parallel
        cell_v = self._cell.terminal_voltage(
            soc, cell_current, temperature_k, v_rc1, v_rc2
        )
        return cell_v * self._n_series

    def derivatives(
        self, current: float, v_rc1: float, v_rc2: float = 0.0
    ) -> tuple[float, float]:
        """Pack-level RC derivatives (same as cell since RC is per-cell)."""
        cell_current = current / self._n_parallel
        return self._cell.derivatives(cell_current, v_rc1, v_rc2)
