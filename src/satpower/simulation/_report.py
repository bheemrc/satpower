"""Power budget report generation from simulation results."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from satpower.simulation._results import SimulationResults
from satpower.loads._profile import LoadProfile
from satpower.battery._pack import BatteryPack


@dataclass
class PowerBudgetReport:
    """Power budget summary for a mission."""

    mission_name: str
    subsystems: list[dict]
    avg_generated_w: float
    avg_consumed_w: float
    avg_consumed_sunlight_w: float
    avg_consumed_eclipse_w: float
    power_margin_w: float
    eclipse_fraction: float
    worst_dod: float
    min_soc: float
    battery_energy_wh: float
    energy_balance_per_orbit_wh: float
    verdict: str

    def to_dict(self) -> dict:
        """Machine-readable dictionary."""
        return {
            "mission_name": self.mission_name,
            "subsystems": self.subsystems,
            "avg_generated_w": self.avg_generated_w,
            "avg_consumed_w": self.avg_consumed_w,
            "avg_consumed_sunlight_w": self.avg_consumed_sunlight_w,
            "avg_consumed_eclipse_w": self.avg_consumed_eclipse_w,
            "power_margin_w": self.power_margin_w,
            "eclipse_fraction": self.eclipse_fraction,
            "worst_dod": self.worst_dod,
            "min_soc": self.min_soc,
            "battery_energy_wh": self.battery_energy_wh,
            "energy_balance_per_orbit_wh": self.energy_balance_per_orbit_wh,
            "verdict": self.verdict,
        }

    def to_text(self) -> str:
        """Human-readable power budget table."""
        sep = "=" * 60
        lines = [
            sep,
            f"  POWER BUDGET REPORT: {self.mission_name}",
            sep,
            "",
            "  SUBSYSTEM BREAKDOWN",
            f"  {'Subsystem':<25s} {'Power (W)':>10s} {'Duty':>8s} {'Trigger':>10s}",
        ]
        for sub in self.subsystems:
            duty_str = f"{sub['duty_cycle'] * 100:.0f}%"
            lines.append(
                f"  {sub['name']:<25s} {sub['power_w']:>10.2f} {duty_str:>8s} {sub['trigger']:>10s}"
            )

        lines.append("")
        lines.append("  ORBIT AVERAGES")
        lines.append(f"    Eclipse fraction: {self.eclipse_fraction * 100:>5.1f}%")
        lines.append(f"    Generated:      {self.avg_generated_w:>6.2f} W")

        sun_frac = 1.0 - self.eclipse_fraction
        if sun_frac > 0:
            lines.append(f"    Consumed (sun):  {self.avg_consumed_sunlight_w:>6.2f} W")
        if self.eclipse_fraction > 0:
            lines.append(f"    Consumed (ecl):  {self.avg_consumed_eclipse_w:>6.2f} W")

        lines.append(f"    Consumed (avg):  {self.avg_consumed_w:>6.2f} W")
        sign = "+" if self.power_margin_w >= 0 else ""
        lines.append(f"    Margin:        {sign}{self.power_margin_w:>6.2f} W")

        lines.append("")
        lines.append("  BATTERY")
        lines.append(f"    Worst DoD:      {self.worst_dod * 100:>5.1f}%")
        lines.append(f"    Min SoC:        {self.min_soc * 100:>5.1f}%")
        lines.append(f"    Pack energy:    {self.battery_energy_wh:>6.1f} Wh")

        if self.worst_dod > 0:
            sizing_margin = 1.0 / self.worst_dod
            lines.append(f"    Sizing margin:  {sizing_margin:>5.1f}x")

        lines.append("")
        lines.append(f"  VERDICT: {self.verdict}")
        lines.append(sep)
        return "\n".join(lines)


def generate_power_budget(
    results: SimulationResults,
    loads: LoadProfile,
    battery: BatteryPack,
    mission_name: str = "Mission",
) -> PowerBudgetReport:
    """Generate a power budget report from simulation results."""
    # Build subsystem list
    subsystems = []
    for mode in loads.modes:
        subsystems.append({
            "name": mode.name,
            "power_w": mode.power_w,
            "duty_cycle": mode.duty_cycle,
            "trigger": mode.trigger,
        })

    eclipse_fraction = results.eclipse_fraction
    sunlight_fraction = 1.0 - eclipse_fraction

    # Compute consumed power in sunlight vs eclipse
    sun_mask = ~results.eclipse
    ecl_mask = results.eclipse

    avg_consumed_sunlight = float(np.mean(results.power_consumed[sun_mask])) if np.any(sun_mask) else 0.0
    avg_consumed_eclipse = float(np.mean(results.power_consumed[ecl_mask])) if np.any(ecl_mask) else 0.0

    avg_generated = float(np.mean(results.power_generated))
    avg_consumed = float(np.mean(results.power_consumed))
    margin = avg_generated - avg_consumed

    worst_dod = results.worst_case_dod
    min_soc = float(np.min(results.soc))

    if margin >= 0:
        verdict = "POSITIVE MARGIN"
    elif worst_dod < 0.5:
        verdict = "NEGATIVE MARGIN (battery can sustain)"
    else:
        verdict = "NEGATIVE MARGIN (battery may be undersized)"

    return PowerBudgetReport(
        mission_name=mission_name,
        subsystems=subsystems,
        avg_generated_w=avg_generated,
        avg_consumed_w=avg_consumed,
        avg_consumed_sunlight_w=avg_consumed_sunlight,
        avg_consumed_eclipse_w=avg_consumed_eclipse,
        power_margin_w=margin,
        eclipse_fraction=eclipse_fraction,
        worst_dod=worst_dod,
        min_soc=min_soc,
        battery_energy_wh=battery.energy_wh,
        energy_balance_per_orbit_wh=results.energy_balance_per_orbit,
        verdict=verdict,
    )
