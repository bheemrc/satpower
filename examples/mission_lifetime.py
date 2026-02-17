#!/usr/bin/env python3
"""Multi-year degradation analysis — estimates battery capacity over mission life."""

from satpower.battery._aging import AgingModel
from satpower.solar._degradation import apply_radiation_degradation


def main():
    # Battery aging over 3-year mission
    aging = AgingModel(
        calendar_fade_per_year=0.02,
        cycle_fade_per_cycle_50dod=0.0001,
        cycle_fade_per_cycle_100dod=0.0005,
    )

    orbits_per_day = 15.5  # typical LEO
    avg_dod = 0.25  # 25% average DoD

    print("Battery Capacity Degradation Over Mission Life")
    print("=" * 50)
    print(f"{'Year':>6} {'Cycles':>8} {'Capacity':>10}")
    print("-" * 50)

    for year in range(6):
        n_cycles = int(orbits_per_day * 365.25 * year)
        remaining = aging.capacity_remaining(year, n_cycles, avg_dod)
        print(f"{year:>6} {n_cycles:>8} {remaining:>9.1%}")

    # Solar panel degradation over mission life
    bol_power = 10.0  # W at BOL
    print("\n\nSolar Panel Degradation (Azur 3G30C)")
    print("=" * 50)
    print(f"{'Fluence':>14} {'Power':>8} {'Remaining':>10}")
    print("-" * 50)

    for log_f in [0, 13, 13.5, 14, 14.5, 15]:
        fluence = 10**log_f if log_f > 0 else 0
        power = apply_radiation_degradation(bol_power, fluence, 0.93, 0.88)
        print(f"{'BOL' if log_f == 0 else f'1e{log_f}':<14} {power:>7.2f} W {power/bol_power:>9.1%}")


if __name__ == "__main__":
    main()
