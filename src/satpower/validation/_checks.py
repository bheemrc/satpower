"""System-level compatibility checks between EPS, battery, panels, and loads."""

from __future__ import annotations

from dataclasses import dataclass, field

from satpower.regulation._eps_board import EPSBoard
from satpower.battery._pack import BatteryPack
from satpower.solar._panel import SolarPanel


@dataclass
class ValidationResult:
    """Result of a system validation check."""

    passed: bool
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def validate_system(
    eps: EPSBoard,
    battery: BatteryPack,
    panels: list[SolarPanel],
    loads_peak_power: float | None = None,
) -> ValidationResult:
    """Validate component compatibility.

    Checks:
    1. Battery voltage range vs EPS bus voltage range
    2. Solar cell Voc vs EPS max_solar_input_v
    3. Panel current (Isc) vs EPS max_solar_input_a
    4. Number of panels vs EPS num_solar_inputs
    5. Load power vs generation capacity (warning)
    """
    warnings: list[str] = []
    errors: list[str] = []

    # 1. Battery series count vs EPS battery config
    # The EPS is designed for a specific battery series count (e.g. 2S).
    # Battery voltage is regulated to bus voltage by the converter, so
    # battery voltage can be higher than bus voltage.
    eps_config = eps.battery_config
    import re
    m = re.match(r"(\d+)S", eps_config)
    if m:
        eps_series = int(m.group(1))
        if battery.n_series != eps_series:
            if battery.n_series > eps_series:
                errors.append(
                    f"Battery series count ({battery.n_series}S) exceeds "
                    f"EPS design ({eps_config}). Max voltage {battery.max_voltage:.1f}V "
                    f"may damage the EPS."
                )
            else:
                warnings.append(
                    f"Battery series count ({battery.n_series}S) differs from "
                    f"EPS design ({eps_config})"
                )

    # 2. Solar cell Voc vs EPS max solar input voltage
    for panel in panels:
        cell = panel.cell
        if cell.voc > eps.max_solar_input_v:
            errors.append(
                f"Panel '{panel.name}': cell Voc ({cell.voc:.2f}V) exceeds "
                f"EPS max solar input ({eps.max_solar_input_v:.1f}V)"
            )
            break  # All panels use same cell type typically

    # 3. Panel Isc vs EPS max solar input current
    if panels:
        cell = panels[0].cell
        panels_per_input = max(len(panels) / max(eps.num_solar_inputs, 1), 1.0)
        est_input_isc = cell.isc * panels_per_input
        if est_input_isc > eps.max_solar_input_a:
            warnings.append(
                f"Estimated per-input Isc ({est_input_isc:.3f}A) exceeds EPS input limit "
                f"({eps.max_solar_input_a:.1f}A) assuming evenly shared panel inputs."
            )

    # 4. Number of panels vs EPS solar inputs
    if len(panels) > eps.num_solar_inputs:
        warnings.append(
            f"Number of panels ({len(panels)}) exceeds "
            f"EPS solar inputs ({eps.num_solar_inputs}). "
            f"Some panels may need to share inputs."
        )

    # 5. Load power vs estimated generation capacity (warning only)
    if loads_peak_power is not None and panels:
        # Conservative coarse estimate: body-mounted geometry average + MPPT.
        total_area = sum(p.area_m2 for p in panels)
        avg_efficiency = panels[0].cell.efficiency if panels else 0.3
        estimated_gen = total_area * avg_efficiency * 1361.0 * 0.5 * eps.mppt_efficiency
        if loads_peak_power > estimated_gen:
            warnings.append(
                f"Peak load ({loads_peak_power:.1f}W) may exceed estimated "
                f"generation capacity (~{estimated_gen:.1f}W). Run full orbit simulation "
                f"for flight-like verification."
            )

    passed = len(errors) == 0
    return ValidationResult(passed=passed, warnings=warnings, errors=errors)
