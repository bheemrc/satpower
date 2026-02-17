"""CLI entry point for satpower.

Usage:
    satpower run mission.yaml              # Run sim, print power budget report
    satpower run mission.yaml --plot       # Also show plots
    satpower run mission.yaml --save-plots results/  # Save plots to directory
    satpower list cells                    # List available solar cells
    satpower list batteries                # List available batteries
    satpower list eps                      # List available EPS boards
    satpower list missions                 # List bundled mission presets
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _cmd_run(args: argparse.Namespace) -> None:
    from satpower.mission._builder import load_mission, build_simulation
    from satpower.simulation._report import generate_power_budget
    from satpower.loads._profile import LoadProfile

    config = load_mission(args.mission)
    sim = build_simulation(config)

    print(f"Running simulation: {config.name} ({config.simulation.duration_orbits} orbits)...")

    results = sim.run(
        duration_orbits=config.simulation.duration_orbits,
        dt_max=config.simulation.dt_max,
    )

    # Build loads for report
    loads = LoadProfile()
    for load in config.loads:
        loads.add_mode(
            name=load.name,
            power_w=load.power_w,
            duty_cycle=load.duty_cycle,
            trigger=load.trigger,
        )

    # Battery for report
    from satpower.battery._pack import BatteryPack

    battery = BatteryPack.from_cell(
        config.satellite.battery.cell,
        config.satellite.battery.config,
    )

    report = generate_power_budget(results, loads, battery, config.name)
    print(report.to_text())

    if args.plot or args.save_plots:
        import matplotlib

        if args.save_plots:
            matplotlib.use("Agg")

        fig_soc = results.plot_soc()
        fig_power = results.plot_power_balance()
        fig_voltage = results.plot_battery_voltage()

        if args.save_plots:
            out_dir = Path(args.save_plots)
            out_dir.mkdir(parents=True, exist_ok=True)
            fig_soc.savefig(out_dir / "soc.png", dpi=150)
            fig_power.savefig(out_dir / "power_balance.png", dpi=150)
            fig_voltage.savefig(out_dir / "battery_voltage.png", dpi=150)
            print(f"\nPlots saved to {out_dir}/")
        else:
            import matplotlib.pyplot as plt

            plt.show()


def _cmd_list(args: argparse.Namespace) -> None:
    from satpower.data._registry import registry

    category = args.category

    if category == "cells":
        items = sorted(registry.list_solar_cells())
        print("Available solar cells:")
        for name in items:
            data = registry.get_solar_cell(name)
            print(f"  {name:<30s}  {data.name}  (eff={data.parameters.efficiency:.1%})")

    elif category == "batteries":
        items = sorted(registry.list_battery_cells())
        print("Available battery cells:")
        for name in items:
            data = registry.get_battery_cell(name)
            print(f"  {name:<30s}  {data.name}  ({data.capacity_ah:.1f}Ah, {data.nominal_voltage_v:.1f}V)")

    elif category == "eps":
        items = sorted(registry.list_eps())
        print("Available EPS boards:")
        for name in items:
            data = registry.get_eps(name)
            print(f"  {name:<30s}  {data.name}  (bus={data.bus_voltage_v:.1f}V)")

    elif category == "missions":
        items = sorted(registry.list_missions())
        if not items:
            print("No bundled missions found.")
        else:
            print("Bundled mission presets:")
            for name in items:
                print(f"  {name}")
    else:
        print(f"Unknown category: {category}")
        print("Available: cells, batteries, eps, missions")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="satpower",
        description="CubeSat EPS Simulation Tool",
    )
    subparsers = parser.add_subparsers(dest="command")

    # run
    run_parser = subparsers.add_parser("run", help="Run a mission simulation")
    run_parser.add_argument("mission", help="Path to mission YAML file")
    run_parser.add_argument("--plot", action="store_true", help="Show plots")
    run_parser.add_argument("--save-plots", metavar="DIR", help="Save plots to directory")

    # list
    list_parser = subparsers.add_parser("list", help="List available components")
    list_parser.add_argument(
        "category",
        choices=["cells", "batteries", "eps", "missions"],
        help="Component category to list",
    )

    args = parser.parse_args()

    if args.command == "run":
        _cmd_run(args)
    elif args.command == "list":
        _cmd_list(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
