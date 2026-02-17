#!/usr/bin/env python3
"""Minimal 3U CubeSat power simulation — 550 km SSO, 5 orbits."""

import satpower as sp


def main():
    # Define orbit: 550 km Sun-synchronous
    orbit = sp.Orbit.circular(altitude_km=550, inclination_deg=97.6)
    print(f"Orbit: {orbit.altitude_km:.0f} km, period = {orbit.period / 60:.1f} min")

    # Define solar panels: 3U CubeSat body-mounted with Azur 3G30C cells
    panels = sp.SolarPanel.cubesat_body("3U", cell_type="azur_3g30c")
    print(f"Panels: {len(panels)} faces")

    # Define battery: 2S2P NCR18650B pack
    battery = sp.BatteryPack.from_cell("panasonic_ncr18650b", config="2S2P")
    print(f"Battery: {battery.nominal_voltage:.1f}V, {battery.capacity_ah:.1f}Ah, {battery.energy_wh:.1f}Wh")

    # Define loads
    loads = sp.LoadProfile()
    loads.add_mode("idle", power_w=2.0)
    loads.add_mode("comms", power_w=8.0, duty_cycle=0.15)
    loads.add_mode("payload", power_w=5.0, duty_cycle=0.30)
    print(f"Load modes: {[m.name for m in loads.modes]}")

    # Run simulation for 5 orbits
    sim = sp.Simulation(orbit, panels, battery, loads)
    print("\nRunning simulation for 5 orbits...")
    results = sim.run(duration_orbits=5)

    # Print summary
    summary = results.summary()
    print("\n--- Simulation Results ---")
    print(f"Duration: {summary['duration_orbits']:.1f} orbits")
    print(f"Eclipse fraction: {summary['eclipse_fraction']:.1%}")
    print(f"Min SoC: {summary['min_soc']:.1%}")
    print(f"Max DoD: {summary['worst_case_dod']:.1%}")
    print(f"Avg power generated: {summary['avg_power_generated_w']:.2f} W")
    print(f"Avg power consumed: {summary['avg_power_consumed_w']:.2f} W")
    print(f"Power margin: {summary['power_margin_w']:.2f} W")
    print(f"Energy balance/orbit: {summary['energy_balance_per_orbit_wh']:.2f} Wh")
    print(f"Battery voltage range: {summary['min_battery_voltage_v']:.2f} - {summary['max_battery_voltage_v']:.2f} V")

    # Generate plots
    results.plot_soc()
    results.plot_power_balance()
    results.plot_battery_voltage()

    import matplotlib.pyplot as plt
    plt.show()


if __name__ == "__main__":
    main()
