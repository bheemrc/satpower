"""State of charge estimation — Coulomb counting."""

from __future__ import annotations

import numpy as np


class CoulombCounter:
    """Coulomb counting state-of-charge estimator.

    Integrates current over time to track charge in/out of battery.
    """

    def __init__(self, capacity_ah: float, initial_soc: float = 1.0):
        self._capacity_as = capacity_ah * 3600.0  # Ah -> As (coulombs)
        self._soc = np.clip(initial_soc, 0.0, 1.0)

    @property
    def soc(self) -> float:
        return self._soc

    def update(self, current: float, dt: float) -> float:
        """Update SoC given current and timestep.

        Parameters
        ----------
        current : Current (A), positive = discharge, negative = charge
        dt : Time step (seconds)

        Returns
        -------
        Updated SoC
        """
        # dSoC = -I * dt / Q  (discharge decreases SoC)
        dsoc = -current * dt / self._capacity_as
        self._soc = float(np.clip(self._soc + dsoc, 0.0, 1.0))
        return self._soc

    @staticmethod
    def dsoc_dt(current: float, capacity_ah: float) -> float:
        """Compute dSoC/dt for ODE integration.

        Parameters
        ----------
        current : Current (A), positive = discharge
        capacity_ah : Battery capacity (Ah)
        """
        return -current / (capacity_ah * 3600.0)
