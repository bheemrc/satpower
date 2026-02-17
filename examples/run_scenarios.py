#!/usr/bin/env python3
"""Run multiple CubeSat scenarios and save plots for review."""

import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import satpower as sp

OUT_DIR = os.path.join(os.path.dirname(__file__), "plots")
os.makedirs(OUT_DIR, exist_ok=True)


def scenario_1_3u_sso():
    """Scenario 1: Standard 3U CubeSat at 550 km Sun-synchronous orbit."""
    print("=== Scenario 1: 3U CubeSat, 550 km SSO, 5 orbits ===")
    orbit = sp.Orbit.circular(altitude_km=550, inclination_deg=97.6)
    panels = sp.SolarPanel.cubesat_body("3U", cell_type="azur_3g30c")
    battery = sp.BatteryPack.from_cell("panasonic_ncr18650b", config="2S2P")

    loads = sp.LoadProfile()
    loads.add_mode("idle", power_w=2.0)
    loads.add_mode("comms", power_w=8.0, duty_cycle=0.15)
    loads.add_mode("payload", power_w=5.0, duty_cycle=0.30)

    sim = sp.Simulation(orbit, panels, battery, loads)
    results = sim.run(duration_orbits=5, dt_max=30)

    summary = results.summary()
    print(f"  Period: {orbit.period/60:.1f} min")
    print(f"  Eclipse fraction: {summary['eclipse_fraction']:.1%}")
    print(f"  Min SoC: {summary['min_soc']:.1%}")
    print(f"  Max DoD: {summary['worst_case_dod']:.1%}")
    print(f"  Power margin: {summary['power_margin_w']:.2f} W")
    print(f"  Energy balance/orbit: {summary['energy_balance_per_orbit_wh']:.2f} Wh")
    print(f"  Battery voltage: {summary['min_battery_voltage_v']:.2f} - {summary['max_battery_voltage_v']:.2f} V")

    fig = results.plot_soc()
    fig.suptitle("Scenario 1: 3U SSO 550 km — State of Charge", fontsize=12, y=1.02)
    fig.savefig(os.path.join(OUT_DIR, "s1_soc.png"), dpi=150, bbox_inches="tight")
    plt.close(fig)

    fig = results.plot_power_balance()
    fig.suptitle("Scenario 1: 3U SSO 550 km — Power Balance", fontsize=12, y=1.02)
    fig.savefig(os.path.join(OUT_DIR, "s1_power.png"), dpi=150, bbox_inches="tight")
    plt.close(fig)

    fig = results.plot_battery_voltage()
    fig.suptitle("Scenario 1: 3U SSO 550 km — Battery Voltage", fontsize=12, y=1.02)
    fig.savefig(os.path.join(OUT_DIR, "s1_voltage.png"), dpi=150, bbox_inches="tight")
    plt.close(fig)

    return results


def scenario_2_iss_orbit():
    """Scenario 2: 3U CubeSat at ISS altitude with lighter loads."""
    print("\n=== Scenario 2: 3U CubeSat, 408 km ISS orbit, 10 orbits ===")
    orbit = sp.Orbit.circular(altitude_km=408, inclination_deg=51.6)
    panels = sp.SolarPanel.cubesat_body("3U", cell_type="spectrolab_xtj_prime")
    battery = sp.BatteryPack.from_cell("panasonic_ncr18650b", config="2S1P")

    loads = sp.LoadProfile()
    loads.add_mode("idle", power_w=1.5)
    loads.add_mode("adcs", power_w=1.0, duty_cycle=0.8)
    loads.add_mode("comms", power_w=6.0, duty_cycle=0.10, trigger="sunlight")

    sim = sp.Simulation(orbit, panels, battery, loads)
    results = sim.run(duration_orbits=10, dt_max=30)

    summary = results.summary()
    print(f"  Period: {orbit.period/60:.1f} min")
    print(f"  Eclipse fraction: {summary['eclipse_fraction']:.1%}")
    print(f"  Min SoC: {summary['min_soc']:.1%}")
    print(f"  Max DoD: {summary['worst_case_dod']:.1%}")
    print(f"  Power margin: {summary['power_margin_w']:.2f} W")
    print(f"  Energy balance/orbit: {summary['energy_balance_per_orbit_wh']:.2f} Wh")

    fig = results.plot_soc()
    fig.suptitle("Scenario 2: ISS Orbit 408 km — State of Charge", fontsize=12, y=1.02)
    fig.savefig(os.path.join(OUT_DIR, "s2_soc.png"), dpi=150, bbox_inches="tight")
    plt.close(fig)

    fig = results.plot_power_balance()
    fig.suptitle("Scenario 2: ISS Orbit 408 km — Power Balance", fontsize=12, y=1.02)
    fig.savefig(os.path.join(OUT_DIR, "s2_power.png"), dpi=150, bbox_inches="tight")
    plt.close(fig)

    fig = results.plot_battery_voltage()
    fig.suptitle("Scenario 2: ISS Orbit 408 km — Battery Voltage", fontsize=12, y=1.02)
    fig.savefig(os.path.join(OUT_DIR, "s2_voltage.png"), dpi=150, bbox_inches="tight")
    plt.close(fig)

    return results


def scenario_3_heavy_payload():
    """Scenario 3: 3U CubeSat with heavy payload — stress test."""
    print("\n=== Scenario 3: 3U CubeSat, 500 km 45° inc, heavy payload, 5 orbits ===")
    orbit = sp.Orbit.circular(altitude_km=500, inclination_deg=45.0)
    panels = sp.SolarPanel.cubesat_body("3U", cell_type="azur_3g30c")
    battery = sp.BatteryPack.from_cell("sony_vtc6", config="2S2P")

    loads = sp.LoadProfile()
    loads.add_mode("idle", power_w=3.0)
    loads.add_mode("comms", power_w=10.0, duty_cycle=0.20)
    loads.add_mode("payload", power_w=8.0, duty_cycle=0.50)
    loads.add_mode("heater", power_w=2.0, trigger="eclipse")

    sim = sp.Simulation(orbit, panels, battery, loads, initial_soc=0.9)
    results = sim.run(duration_orbits=5, dt_max=30)

    summary = results.summary()
    print(f"  Period: {orbit.period/60:.1f} min")
    print(f"  Eclipse fraction: {summary['eclipse_fraction']:.1%}")
    print(f"  Min SoC: {summary['min_soc']:.1%}")
    print(f"  Max DoD: {summary['worst_case_dod']:.1%}")
    print(f"  Power margin: {summary['power_margin_w']:.2f} W")
    print(f"  Energy balance/orbit: {summary['energy_balance_per_orbit_wh']:.2f} Wh")

    fig = results.plot_soc()
    fig.suptitle("Scenario 3: Heavy Payload Stress Test — State of Charge", fontsize=12, y=1.02)
    fig.savefig(os.path.join(OUT_DIR, "s3_soc.png"), dpi=150, bbox_inches="tight")
    plt.close(fig)

    fig = results.plot_power_balance()
    fig.suptitle("Scenario 3: Heavy Payload Stress Test — Power Balance", fontsize=12, y=1.02)
    fig.savefig(os.path.join(OUT_DIR, "s3_power.png"), dpi=150, bbox_inches="tight")
    plt.close(fig)

    fig = results.plot_battery_voltage()
    fig.suptitle("Scenario 3: Heavy Payload Stress Test — Battery Voltage", fontsize=12, y=1.02)
    fig.savefig(os.path.join(OUT_DIR, "s3_voltage.png"), dpi=150, bbox_inches="tight")
    plt.close(fig)

    return results


if __name__ == "__main__":
    scenario_1_3u_sso()
    scenario_2_iss_orbit()
    scenario_3_heavy_payload()
    print(f"\nAll plots saved to: {OUT_DIR}/")
