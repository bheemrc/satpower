"""Battery aging models — calendar and cycle degradation."""

from __future__ import annotations

import numpy as np

# Universal gas constant (J/(mol·K))
_R_GAS = 8.314


class AgingModel:
    """Calendar and cycle aging model for battery capacity fade.

    Supports Arrhenius temperature dependence for accelerated aging at
    elevated temperatures.
    """

    def __init__(
        self,
        calendar_fade_per_year: float = 0.02,
        cycle_fade_per_cycle_50dod: float = 0.0001,
        cycle_fade_per_cycle_100dod: float = 0.0005,
        reference_temp_k: float = 298.15,
        activation_energy_j: float = 50000.0,
    ):
        self._cal_fade = calendar_fade_per_year
        self._cyc_fade_50 = cycle_fade_per_cycle_50dod
        self._cyc_fade_100 = cycle_fade_per_cycle_100dod
        self._reference_temp_k = reference_temp_k
        self._activation_energy = activation_energy_j

    def _arrhenius_factor(self, temperature_k: float) -> float:
        """Arrhenius acceleration factor relative to reference temperature.

        factor = exp(Ea/R * (1/T_ref - 1/T))

        Returns 1.0 at reference temperature, >1 at higher temps, <1 at lower.
        """
        if temperature_k <= 0:
            return 1.0
        exponent = (
            self._activation_energy
            / _R_GAS
            * (1.0 / self._reference_temp_k - 1.0 / temperature_k)
        )
        return float(np.exp(exponent))

    def capacity_remaining(
        self,
        years: float,
        n_cycles: int,
        avg_dod: float,
        temperature_k: float = 298.15,
    ) -> float:
        """Fraction of original capacity remaining.

        Parameters
        ----------
        years : Calendar time
        n_cycles : Number of charge/discharge cycles
        avg_dod : Average depth of discharge per cycle [0, 1]
        temperature_k : Average battery temperature (K). Default 298.15K
            gives factor=1.0 (no acceleration).
        """
        arrhenius = self._arrhenius_factor(temperature_k)

        calendar_loss = self._cal_fade * years * arrhenius

        # Interpolate cycle fade between 50% and 100% DoD
        if avg_dod <= 0.5:
            fade_per_cycle = self._cyc_fade_50 * (avg_dod / 0.5)
        else:
            t = (avg_dod - 0.5) / 0.5
            fade_per_cycle = self._cyc_fade_50 + t * (self._cyc_fade_100 - self._cyc_fade_50)

        cycle_loss = fade_per_cycle * n_cycles * arrhenius
        remaining = 1.0 - calendar_loss - cycle_loss
        return float(np.clip(remaining, 0.0, 1.0))
