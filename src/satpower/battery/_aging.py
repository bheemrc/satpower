"""Battery aging models — calendar and cycle degradation."""

from __future__ import annotations

import numpy as np


class AgingModel:
    """Calendar and cycle aging model for battery capacity fade.

    Phase 1: simple linear models. Phase 2 will add Arrhenius temperature
    dependence and nonlinear cycle aging.
    """

    def __init__(
        self,
        calendar_fade_per_year: float = 0.02,
        cycle_fade_per_cycle_50dod: float = 0.0001,
        cycle_fade_per_cycle_100dod: float = 0.0005,
    ):
        self._cal_fade = calendar_fade_per_year
        self._cyc_fade_50 = cycle_fade_per_cycle_50dod
        self._cyc_fade_100 = cycle_fade_per_cycle_100dod

    def capacity_remaining(
        self,
        years: float,
        n_cycles: int,
        avg_dod: float,
    ) -> float:
        """Fraction of original capacity remaining.

        Parameters
        ----------
        years : Calendar time
        n_cycles : Number of charge/discharge cycles
        avg_dod : Average depth of discharge per cycle [0, 1]
        """
        calendar_loss = self._cal_fade * years

        # Interpolate cycle fade between 50% and 100% DoD
        if avg_dod <= 0.5:
            fade_per_cycle = self._cyc_fade_50 * (avg_dod / 0.5)
        else:
            t = (avg_dod - 0.5) / 0.5
            fade_per_cycle = self._cyc_fade_50 + t * (self._cyc_fade_100 - self._cyc_fade_50)

        cycle_loss = fade_per_cycle * n_cycles
        remaining = 1.0 - calendar_loss - cycle_loss
        return float(np.clip(remaining, 0.0, 1.0))
