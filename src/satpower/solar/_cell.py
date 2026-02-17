"""Single-diode I-V model for solar cells."""

from __future__ import annotations

import numpy as np
from scipy.optimize import brentq

from satpower.data._loader import load_solar_cell, SolarCellData

# Boltzmann constant (J/K)
K_B = 1.380649e-23
# Electron charge (C)
Q_E = 1.602176634e-19


class SolarCell:
    """Single-diode solar cell model.

    Models a multi-junction solar cell using the single-diode equivalent
    circuit with temperature and irradiance dependence.
    """

    def __init__(self, data: SolarCellData):
        self._data = data
        p = data.parameters
        d = data.diode_model
        tc = data.test_conditions

        self._voc = p.voc_v
        self._isc = p.isc_a
        self._vmp = p.vmp_v
        self._imp = p.imp_a
        self._area_cm2 = p.area_cm2
        self._efficiency = p.efficiency

        self._n = d.ideality_factor
        self._rs = d.series_resistance_ohm
        self._rsh = d.shunt_resistance_ohm

        self._irrad_ref = tc.irradiance_w_m2
        self._temp_ref_k = tc.temperature_c + 273.15

        # Temperature coefficients
        tcoeff = data.temperature_coefficients
        self._dvoc_dt = tcoeff.dvoc_dt_mv_per_c * 1e-3  # V/K
        self._disc_dt = tcoeff.disc_dt_ua_cm2_per_c * 1e-6 * self._area_cm2  # A/K
        self._dpmp_dt = tcoeff.dpmp_dt_percent_per_c / 100.0  # fraction/K

        # Compute single-diode parameters from datasheet values
        self._vt_ref = self._n * K_B * self._temp_ref_k / Q_E
        self._i_ph_ref = self._isc  # photocurrent ≈ Isc
        self._i0_ref = self._isc / (np.exp(self._voc / self._vt_ref) - 1.0)

        # Optical
        self._packing_factor = data.optical.packing_factor

    @classmethod
    def from_datasheet(cls, name: str) -> SolarCell:
        """Load solar cell from YAML datasheet by name."""
        return cls(load_solar_cell(name))

    @property
    def name(self) -> str:
        return self._data.name

    @property
    def area_cm2(self) -> float:
        return self._area_cm2

    @property
    def area_m2(self) -> float:
        return self._area_cm2 * 1e-4

    @property
    def efficiency(self) -> float:
        return self._efficiency

    @property
    def packing_factor(self) -> float:
        return self._packing_factor

    @property
    def voc(self) -> float:
        """Open-circuit voltage at test conditions (V)."""
        return self._voc

    @property
    def isc(self) -> float:
        """Short-circuit current at test conditions (A)."""
        return self._isc

    def _adjust_for_conditions(
        self, irradiance: float, temperature_k: float
    ) -> tuple[float, float, float]:
        """Adjust Iph, I0, Vt for irradiance and temperature."""
        g_ratio = irradiance / self._irrad_ref
        dt = temperature_k - self._temp_ref_k

        # Photocurrent scales linearly with irradiance
        i_ph = (self._i_ph_ref + self._disc_dt * dt) * g_ratio

        # Thermal voltage
        vt = self._n * K_B * temperature_k / Q_E

        # Saturation current increases with temperature
        i0 = self._i0_ref * (temperature_k / self._temp_ref_k) ** 3 * np.exp(
            Q_E * self._voc / (self._n * K_B) * (1.0 / self._temp_ref_k - 1.0 / temperature_k)
        )

        return i_ph, i0, vt

    def iv_curve(
        self,
        irradiance: float,
        temperature_k: float,
        voltage: np.ndarray,
    ) -> np.ndarray:
        """Compute current at given voltages for the single-diode model.

        I = I_ph - I_0 * (exp((V + I*Rs) / Vt) - 1) - (V + I*Rs) / Rsh

        Solved iteratively for each voltage point.
        """
        i_ph, i0, vt = self._adjust_for_conditions(irradiance, temperature_k)
        voltage = np.asarray(voltage, dtype=float)

        def _current_at_v(v: float) -> float:
            if i_ph <= 0:
                return 0.0

            def residual(i: float) -> float:
                return (
                    i_ph
                    - i0 * (np.exp((v + i * self._rs) / vt) - 1.0)
                    - (v + i * self._rs) / self._rsh
                    - i
                )

            try:
                return brentq(residual, 0.0, i_ph * 1.1)
            except ValueError:
                return 0.0

        return np.array([_current_at_v(v) for v in voltage])

    def mpp(
        self, irradiance: float, temperature_k: float
    ) -> tuple[float, float]:
        """Find maximum power point (V_mp, I_mp).

        Uses the full I-V curve with brentq root-finding for accuracy.
        For fast repeated evaluation, use power_at_mpp() which uses an
        analytical approximation.
        """
        if irradiance <= 0:
            return 0.0, 0.0

        # Search over voltage range
        voc_approx = self._voc + self._dvoc_dt * (temperature_k - self._temp_ref_k)
        v_range = np.linspace(0, max(voc_approx, 0.1), 200)
        i_range = self.iv_curve(irradiance, temperature_k, v_range)
        p_range = v_range * i_range
        idx = np.argmax(p_range)
        return float(v_range[idx]), float(i_range[idx])

    def power_at_mpp(self, irradiance: float, temperature_k: float) -> float:
        """Power output at maximum power point (W).

        Uses analytical fill-factor approximation for performance.
        For the full I-V curve solution, use mpp() instead.
        """
        if irradiance <= 0:
            return 0.0

        g_ratio = irradiance / self._irrad_ref
        dt = temperature_k - self._temp_ref_k

        # Adjust Voc and Isc for conditions
        isc = (self._isc + self._disc_dt * dt) * g_ratio
        voc = self._voc + self._dvoc_dt * dt
        # Voc also shifts with irradiance (logarithmic)
        if g_ratio > 0:
            vt = self._n * K_B * temperature_k / Q_E
            voc += vt * np.log(max(g_ratio, 1e-10))

        if isc <= 0 or voc <= 0:
            return 0.0

        # Fill factor approximation: FF ≈ (voc_norm - ln(voc_norm + 0.72)) / (voc_norm + 1)
        # where voc_norm = Voc / Vt (normalized Voc)
        vt = self._n * K_B * temperature_k / Q_E
        voc_norm = voc / vt
        if voc_norm > 1:
            ff = (voc_norm - np.log(voc_norm + 0.72)) / (voc_norm + 1)
            # Series resistance correction
            rs_loss = self._rs * isc / voc
            ff *= (1.0 - rs_loss)
        else:
            ff = 0.7  # fallback

        ff = np.clip(ff, 0.5, 0.95)
        return float(isc * voc * ff)
